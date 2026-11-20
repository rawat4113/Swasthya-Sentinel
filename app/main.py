from datetime import datetime, timedelta, timezone
import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4
from pathlib import Path
import csv, io, json
import httpx
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.connection import get_db, SessionLocal
from app.database import init_db
from app.database.models import (Zone, EnvironmentObservation, HealthObservation, WorkforceObservation,
 RiskAssessment, Alert, IngestionJob, InterventionAction, AuditLog, SimulationRun, DataSourceStatus, User)
from app.core.config import settings
from app.processing.quality import validate_record, parse_dt
from app.ingestion.data_cleaner import normalize_record
from app.ingestion.data_validator import validate_observation
from app.ingestion.manual_input import prepare_manual_input
from app.ingestion.csv_importer import parse_csv_bytes
from app.ingestion.excel_importer import parse_excel_bytes
from app.ingestion.geojson_importer import parse_geojson
from app.ingestion.ingestion_history import job_summary
from app.ingestion.ingestion_pipeline import import_status
from app.core.security import reject_personal_identifiers, hash_password, verify_password, issue_access_token, decode_access_token
from app.ingestion.data_processor import insert_record
from app.risk_engine.scoring import calculate_risk, severity, RISK_CONFIG
from app.explainability.explanations import explain_contributions
from app.prevention.recommendation_rules import recommendation_for
from app.validation.backtest import run_synthetic_backtest
from app.ingestion.aqi_connector import fetch_nearby_particulates
from app.simulation.scenario_runner import resolve_scenario_inputs

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

@asynccontextmanager
async def lifespan(application):
    init_db()
    from scripts.generate_data import seed
    seed(force=False)
    if settings.demo_users_enabled:
        from app.core.bootstrap import ensure_demo_users
        ensure_demo_users()
    task=None
    if settings.auto_refresh_enabled:
        task=asyncio.create_task(_periodic_refresh_loop())
    try:
        yield
    finally:
        if task:
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass

app=FastAPI(title='Swasthya Sentinel API',version='1.0.0',description='District-level multisignal population and workforce health early-warning MVP.',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['*'] if settings.app_env=='development' else [],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

class ManualInput(BaseModel):
    category: str
    record: dict
    actor: str='demo-user'
class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)
class UserCreateInput(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r'^[a-zA-Z0-9_.-]+$')
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=200)
    role: str

class AcknowledgeInput(BaseModel): actor: str='demo-user'
class ActionInput(BaseModel): responsible_role: str; notes: str=''; actor: str='demo-user'
class SimulationInput(BaseModel):
    zone_id: str
    scenario: str=Field(default='custom',max_length=80)
    temperature_c: float|None=None
    humidity_pct: float|None=None
    apparent_temperature_c: float|None=None
    aqi: float|None=None
    pm25: float|None=None
    pm10: float|None=None
    heat_complaints: int|None=None
    respiratory_complaints: int|None=None
    workforce_heat_complaints: int|None=None
    workforce_respiratory_complaints: int|None=None


ROLE_LABELS = {
    'district_admin': 'District Administrator',
    'health_officer': 'Health Department Officer',
    'environmental_officer': 'Environmental Department Officer',
    'workplace_safety_officer': 'Workplace Safety Officer',
}
ROLE_CATEGORIES = {
    'district_admin': {'environment', 'health', 'workforce'},
    'health_officer': {'health'},
    'environmental_officer': {'environment'},
    'workplace_safety_officer': {'workforce'},
}


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(401, 'Sign in to access this feature.')
    token = authorization.split(' ', 1)[1].strip()
    payload = decode_access_token(token, settings.auth_secret_key)
    if not payload:
        raise HTTPException(401, 'Your session has expired. Please sign in again.')
    user = db.query(User).filter_by(username=payload.get('sub'), is_active=True).first()
    if not user or user.role != payload.get('role'):
        raise HTTPException(401, 'User session is no longer valid.')
    return user


def require_roles(*roles):
    def dependency(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, 'Your account does not have permission for this action.')
        return user
    return dependency


def ensure_category_permission(user: User, category: str):
    if category not in ROLE_CATEGORIES.get(user.role, set()):
        raise HTTPException(403, f"Your {ROLE_LABELS.get(user.role, user.role)} account cannot submit {category} observations.")


def ensure_job_access(job: IngestionJob | None, user: User):
    if not job:
        raise HTTPException(404, 'Ingestion job not found')
    if user.role != 'district_admin' and job.created_by != user.username:
        raise HTTPException(403, 'You can only review imports submitted by your account.')


def _known_zones(db): return {z.id for z in db.query(Zone).all()}
def _asdict(obj, fields): return {f:getattr(obj,f) for f in fields} if obj else {}
def _record_dict(category,row):
    if category not in ['environment','health','workforce']:
        raise HTTPException(400,'category must be environment, health or workforce')
    try: reject_personal_identifiers(row.keys())
    except ValueError as exc: raise HTTPException(422,str(exc))
    return normalize_record(row)

def _source_audit(db,action,entity_type,entity_id,details=None,actor='system'):
    db.add(AuditLog(actor=actor,action=action,entity_type=entity_type,entity_id=str(entity_id),details=details or {}))

def _get_signal_set(db,zone_id):
    env=db.query(EnvironmentObservation).filter_by(zone_id=zone_id).order_by(desc(EnvironmentObservation.observed_at)).first()
    health=db.query(HealthObservation).filter_by(zone_id=zone_id).order_by(desc(HealthObservation.observed_at)).first()
    workforce=db.query(WorkforceObservation).filter_by(zone_id=zone_id).order_by(desc(WorkforceObservation.observed_at)).first()
    e=_asdict(env,['temperature_c','humidity_pct','apparent_temperature_c','aqi','pm25','pm10','no2'])
    h=_asdict(health,['clinic_visits','heat_complaints','respiratory_complaints','fatigue_reports','first_aid_cases'])
    w=_asdict(workforce,['exposed_workers','heat_complaints','respiratory_complaints','first_aid_cases','absence_count'])
    now=_utcnow()
    e_fresh=bool(env and (now-env.observed_at)<=timedelta(hours=48))
    h_fresh=bool(health and (now-health.observed_at)<=timedelta(hours=72))
    w_fresh=bool(workforce and (now-workforce.observed_at)<=timedelta(hours=72))
    e['available']=e_fresh; h['available']=h_fresh; w['available']=w_fresh
    if not e_fresh:
        for key in ['temperature_c','humidity_pct','apparent_temperature_c','aqi','pm25','pm10','no2']: e[key]=None
    if not h_fresh:
        for key in ['clinic_visits','heat_complaints','respiratory_complaints','fatigue_reports','first_aid_cases']: h[key]=None
    if not w_fresh:
        for key in ['exposed_workers','heat_complaints','respiratory_complaints','first_aid_cases','absence_count']: w[key]=None
    histories={}
    for field,model in [('heat_complaints',HealthObservation),('respiratory_complaints',HealthObservation)]:
        rows=db.query(model).filter_by(zone_id=zone_id).order_by(desc(model.observed_at)).limit(31).all()
        histories[field]=[getattr(x,field) for x in reversed(rows)]
    for field,model,key in [('work_heat_complaints',WorkforceObservation,'heat_complaints'),('work_respiratory_complaints',WorkforceObservation,'respiratory_complaints')]:
        rows=db.query(model).filter_by(zone_id=zone_id).order_by(desc(model.observed_at)).limit(31).all()
        histories[field]=[getattr(x,key) for x in reversed(rows)]
    return e,h,w,histories,env,health,workforce

def _save_risk(db,zone_id,result):
    obj=RiskAssessment(zone_id=zone_id,risk_type=result['risk_type'],score=result['score'],confidence=result['confidence'],severity=result['severity'],evidence=result['evidence'],explanation=result['explanation'],is_simulated=result.get('is_simulated',False))
    db.add(obj); db.flush()
    # Alert only when score is meaningful and at least two independent signal families exist.
    if result['score']>=float(RISK_CONFIG.get('alert_score',50)) and result['evidence'].get('independent_signal_families',0)>=int(RISK_CONFIG.get('alert_min_independent_signal_families',2)):
        recent=db.query(Alert).filter_by(zone_id=zone_id,risk_type=result['risk_type'],status='open',is_simulated=result.get('is_simulated',False)).order_by(desc(Alert.created_at)).first()
        if not recent or recent.created_at < _utcnow()-timedelta(hours=float(RISK_CONFIG.get('alert_cooldown_hours',12))):
            rec,role=recommendation_for(result['risk_type'],result['severity'])
            db.add(Alert(zone_id=zone_id,risk_type=result['risk_type'],severity=result['severity'],score=result['score'],confidence=result['confidence'],title=f"{result['risk_type'].title()} risk warning — {zone_id}",explanation=result['explanation'],recommendation=rec,responsible_role=role,is_simulated=result.get('is_simulated',False)))
    return obj

def compute_zone_risks(db,zone_id,save=True,overrides=None,simulated=False):
    env,health,workforce,histories,*_= _get_signal_set(db,zone_id)
    if overrides:
        env.update({k:v for k,v in overrides.items() if k in ['temperature_c','humidity_pct','apparent_temperature_c','aqi','pm25','pm10'] and v is not None})
        health.update({k:v for k,v in overrides.items() if k in ['heat_complaints','respiratory_complaints'] and v is not None})
        workforce.update({k:v for k,v in overrides.items() if k in ['workforce_heat_complaints','workforce_respiratory_complaints'] and v is not None})
        if any(k in overrides for k in ['temperature_c','humidity_pct','apparent_temperature_c','aqi','pm25','pm10']): env['available']=True
        if any(k in overrides for k in ['heat_complaints','respiratory_complaints']): health['available']=True
        if any(k in overrides for k in ['workforce_heat_complaints','workforce_respiratory_complaints']): workforce['available']=True
        if 'workforce_heat_complaints' in overrides: workforce['heat_complaints']=overrides['workforce_heat_complaints']
        if 'workforce_respiratory_complaints' in overrides: workforce['respiratory_complaints']=overrides['workforce_respiratory_complaints']
    results=[]
    for risk_type in ['heat','respiratory']:
        result=calculate_risk(risk_type,env,health,workforce,histories,simulated)
        result['contributions']=explain_contributions(risk_type,result['evidence'])
        if save: _save_risk(db,zone_id,result)
        results.append(result)
    if save: db.commit()
    return results

def _job_response(job):
    return job_summary(job) | {'created_by': getattr(job, 'created_by', 'legacy-demo-user')}

def _stage_job(db,category,source,filename,rows,actor="system"):
    if category not in ['environment','health','workforce']: raise HTTPException(400,'category must be environment, health or workforce')
    known=_known_zones(db); normalized=[_record_dict(category,r) for r in rows]
    forbidden={'patient_id','patient_name','employee_id','employee_name','phone','phone_number','email','national_id','aadhaar','medical_record_number'}
    if any(forbidden.intersection(row) for row in normalized):
        raise HTTPException(422,'Personal identifiers are not accepted. Upload aggregated observations only.')
    errors=[]; seen=set(); valid=0; duplicate=0
    for i,row in enumerate(normalized):
        row_errors=validate_observation(category,row,known)
        key=(row.get('zone_id'),row.get('observed_at'))
        if key in seen: row_errors.append('Duplicate record in uploaded file'); duplicate+=1
        seen.add(key)
        if row_errors: errors.append({'row':i+1,'errors':row_errors})
        else: valid+=1
    job=IngestionJob(id=str(uuid4()),source_type=source,category=category,filename=filename,total_rows=len(normalized),valid_rows=valid,invalid_rows=len(errors),duplicate_rows=duplicate,staged_data=normalized,errors=errors,status='validated' if not errors else 'needs_review',created_by=actor)
    db.add(job); db.commit(); db.refresh(job)
    return _job_response(job)

async def _periodic_refresh_loop():
    while True:
        await asyncio.sleep(max(5,settings.refresh_interval_minutes)*60)
        db=SessionLocal()
        try:
            refresh_environment(db)
            if settings.openaq_api_key: refresh_air_quality(db)
        except Exception:
            db.rollback()
        finally:
            db.close()

@app.get('/')
def root(): return {'name':'Swasthya Sentinel API','docs':'/docs','status':'running'}
@app.get('/health')
def health_check(): return {'status':'healthy','service':'swasthya-sentinel-api','timestamp':_utcnow().isoformat()}

@app.post('/api/v1/auth/login')
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=payload.username).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, 'Incorrect username or password.')
    user.last_login_at = _utcnow()
    _source_audit(db, 'USER_LOGIN', 'user', user.username, {'role': user.role}, actor=user.username)
    db.commit()
    token = issue_access_token(user.username, user.role, settings.auth_secret_key,
                               max(1, settings.access_token_hours) * 60 * 60)
    return {'access_token': token, 'token_type': 'bearer',
            'expires_in': max(1, settings.access_token_hours) * 60 * 60,
            'user': {'username': user.username, 'display_name': user.display_name, 'role': user.role,
                     'role_label': ROLE_LABELS.get(user.role, user.role)}}

@app.get('/api/v1/auth/me')
def auth_me(user: User = Depends(get_current_user)):
    return {'username': user.username, 'display_name': user.display_name, 'role': user.role,
            'role_label': ROLE_LABELS.get(user.role, user.role)}

@app.get('/api/v1/auth/users')
def list_users(db: Session = Depends(get_db), user: User = Depends(require_roles('district_admin'))):
    return [{'username': item.username, 'display_name': item.display_name, 'role': item.role,
             'role_label': ROLE_LABELS.get(item.role, item.role), 'is_active': item.is_active,
             'created_at': item.created_at.isoformat(),
             'last_login_at': item.last_login_at.isoformat() if item.last_login_at else None}
            for item in db.query(User).order_by(User.username).all()]

@app.post('/api/v1/auth/users')
def create_user(payload: UserCreateInput, db: Session = Depends(get_db), user: User = Depends(require_roles('district_admin'))):
    if payload.role not in ROLE_LABELS:
        raise HTTPException(422, 'Unsupported role.')
    if db.query(User).filter_by(username=payload.username).first():
        raise HTTPException(409, 'Username already exists.')
    item = User(username=payload.username, display_name=payload.display_name, role=payload.role,
                password_hash=hash_password(payload.password), is_active=True)
    db.add(item)
    _source_audit(db, 'USER_CREATED', 'user', payload.username, {'role': payload.role, 'created_by': user.username}, actor=user.username)
    db.commit()
    return {'status': 'created', 'username': item.username, 'role': item.role}

@app.post('/api/v1/auth/users/{username}/deactivate')
def deactivate_user(username: str, db: Session = Depends(get_db), user: User = Depends(require_roles('district_admin'))):
    item = db.query(User).filter_by(username=username).first()
    if not item:
        raise HTTPException(404, 'User not found.')
    if item.username == user.username:
        raise HTTPException(409, 'You cannot deactivate your own account.')
    item.is_active = False
    _source_audit(db, 'USER_DEACTIVATED', 'user', username, {'by': user.username}, actor=user.username)
    db.commit()
    return {'status': 'deactivated', 'username': username}

@app.get('/api/v1/zones')
def zones(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    return [{'id':z.id,'name':z.name,'district':z.district,'latitude':z.latitude,'longitude':z.longitude,'population_reference':z.population_reference} for z in db.query(Zone).all()]

@app.get('/api/v1/overview')
def overview(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    out=[]
    for z in db.query(Zone).all():
        risks=compute_zone_risks(db,z.id,save=False)
        out.append({'zone_id':z.id,'zone_name':z.name,'heat':risks[0],'respiratory':risks[1]})
    active=db.query(Alert).filter(Alert.status=='open').count()
    latest=db.query(EnvironmentObservation).order_by(desc(EnvironmentObservation.observed_at)).first()
    return {'district':'Illustrative Demo District','zones':out,'active_alerts':active,'last_environment_observation':latest.observed_at.isoformat() if latest else None,'data_mode':settings.data_mode}

@app.get('/api/v1/risks')
def risks(zone_id:str|None=None,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    selected=[zone_id] if zone_id else [z.id for z in db.query(Zone).all()]
    if zone_id and zone_id not in _known_zones(db): raise HTTPException(404,'Unknown zone')
    return [dict(zone_id=z,assessments=compute_zone_risks(db,z,save=True)) for z in selected]
@app.get('/api/v1/risks/heat')
def heat_risks(db:Session=Depends(get_db),user:User=Depends(get_current_user)): return [{'zone_id':z.id,'risk':compute_zone_risks(db,z.id,save=False)[0]} for z in db.query(Zone).all()]
@app.get('/api/v1/risks/respiratory')
def respiratory_risks(db:Session=Depends(get_db),user:User=Depends(get_current_user)): return [{'zone_id':z.id,'risk':compute_zone_risks(db,z.id,save=False)[1]} for z in db.query(Zone).all()]

@app.get('/api/v1/zones/geojson')
def zone_geojson(user:User=Depends(get_current_user)):
    base=Path(__file__).resolve().parents[1]
    imported=base/'data'/'boundaries'/'imported_zones.geojson'
    sample=base/'data'/'boundaries'/'illustrative_demo_zones.geojson'
    target=imported if imported.exists() else sample
    try: return json.loads(target.read_text(encoding='utf-8'))
    except Exception: return {'type':'FeatureCollection','features':[]}

@app.get('/api/v1/environment')
def environment(zone_id:str|None=None,limit:int=100,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    q=db.query(EnvironmentObservation).order_by(desc(EnvironmentObservation.observed_at))
    if zone_id: q=q.filter_by(zone_id=zone_id)
    return [{'zone_id':x.zone_id,'observed_at':x.observed_at.isoformat(),'ingested_at':x.ingested_at.isoformat(),'temperature_c':x.temperature_c,'humidity_pct':x.humidity_pct,'apparent_temperature_c':x.apparent_temperature_c,'aqi':x.aqi,'pm25':x.pm25,'pm10':x.pm10,'source':x.source,'source_detail':x.source_detail,'quality_status':x.quality_status} for x in q.limit(min(limit,1000)).all()]
@app.get('/api/v1/health-signals')
def health_signals(zone_id:str|None=None,limit:int=100,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    q=db.query(HealthObservation).order_by(desc(HealthObservation.observed_at))
    if zone_id:q=q.filter_by(zone_id=zone_id)
    output=[]
    for x in q.limit(min(limit,1000)).all():
        threshold=settings.min_group_size
        output.append({'zone_id':x.zone_id,'observed_at':x.observed_at.isoformat(),'ingested_at':x.ingested_at.isoformat(),
          'clinic_visits':None if x.clinic_visits<threshold else x.clinic_visits,
          'heat_complaints':None if x.heat_complaints<threshold else x.heat_complaints,
          'respiratory_complaints':None if x.respiratory_complaints<threshold else x.respiratory_complaints,
          'fatigue_reports':None if x.fatigue_reports<threshold else x.fatigue_reports,
          'first_aid_cases':None if x.first_aid_cases<threshold else x.first_aid_cases,'source':x.source,'source_detail':x.source_detail,
          'suppressed_fields':[name for name,value in [('clinic_visits',x.clinic_visits),('heat_complaints',x.heat_complaints),('respiratory_complaints',x.respiratory_complaints),('fatigue_reports',x.fatigue_reports),('first_aid_cases',x.first_aid_cases)] if value<threshold],
          'source':x.source})
    return output
@app.get('/api/v1/workforce')
def workforce(zone_id:str|None=None,limit:int=100,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    q=db.query(WorkforceObservation).order_by(desc(WorkforceObservation.observed_at))
    if zone_id:q=q.filter_by(zone_id=zone_id)
    output=[]
    for x in q.limit(min(limit,1000)).all():
        threshold=settings.min_group_size; small=x.exposed_workers < threshold
        output.append({'zone_id':x.zone_id,'observed_at':x.observed_at.isoformat(),'ingested_at':x.ingested_at.isoformat(),'shift':x.shift,
          'exposed_workers':None if small else x.exposed_workers,
          'heat_complaints':None if small or x.heat_complaints<threshold else x.heat_complaints,
          'respiratory_complaints':None if small or x.respiratory_complaints<threshold else x.respiratory_complaints,
          'first_aid_cases':None if small or x.first_aid_cases<threshold else x.first_aid_cases,
          'absence_count':None if small or x.absence_count<threshold else x.absence_count,'source':x.source,'source_detail':x.source_detail,
          'suppressed':small or any(v<threshold for v in [x.heat_complaints,x.respiratory_complaints,x.first_aid_cases,x.absence_count]),'source':x.source})
    return output

@app.post('/api/v1/ingestion/manual')
def manual_input(payload:ManualInput,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    ensure_category_permission(user, payload.category)
    row,errors=prepare_manual_input(payload.category,payload.record,_known_zones(db))
    if errors: raise HTTPException(422,{'validation_errors':errors})
    job=_stage_job(db,payload.category,'MANUAL','manual-entry',[row],actor=user.username); job_obj=db.get(IngestionJob,job['job_id'])
    return commit_job(job_obj,db,user.username)

def commit_job(job,db,actor='demo-user'):
    if not job: raise HTTPException(404,'Ingestion job not found')
    if job.status in ('committed','partially_committed'): return _job_response(job)
    if job.status=='rejected': raise HTTPException(409,'This import was rejected and cannot be committed.')
    known=_known_zones(db); errors=[]; valid=[]; seen=set()
    for i,row in enumerate(job.staged_data):
        errs=validate_observation(job.category,row,known)
        key=(row.get('zone_id'),row.get('observed_at'))
        if key in seen: errs.append('Duplicate row in this import')
        seen.add(key)
        try:
            dt=parse_dt(row['observed_at'])
            model={'environment':EnvironmentObservation,'health':HealthObservation,'workforce':WorkforceObservation}[job.category]
            if db.query(model).filter_by(zone_id=row['zone_id'],observed_at=dt).first(): errs.append('Record already exists in database')
        except Exception: pass
        if errs: errors.append({'row':i+1,'errors':errs})
        else: valid.append(row)
    for row in valid: insert_record(db,job.category,row,job.source_type)
    job.errors=errors; job.valid_rows=len(valid); job.invalid_rows=len(errors); job.imported_rows=len(valid); job.status=import_status(len(valid),len(errors)); job.committed_at=_utcnow()
    _source_audit(db,'IMPORT_COMMIT','ingestion_job',job.id,{'imported':len(valid),'rejected':len(errors),'source':job.source_type,'actor':actor},actor=actor)
    db.commit(); db.refresh(job)
    if valid:
        for zid in {r['zone_id'] for r in valid}: compute_zone_risks(db,zid,save=True)
    return _job_response(job)

@app.post('/api/v1/ingestion/preview')
async def preview_upload(file:UploadFile=File(...),category:str=Query(...),db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    ensure_category_permission(user, category)
    return await _upload_stage(file,category,db,user.username)
@app.post('/api/v1/ingestion/upload/csv')
async def upload_csv(file:UploadFile=File(...),category:str=Query(...),db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    ensure_category_permission(user, category)
    if not file.filename.lower().endswith('.csv'): raise HTTPException(400,'Upload a .csv file')
    return await _upload_stage(file,category,db,user.username)
@app.post('/api/v1/ingestion/upload/excel')
async def upload_excel(file:UploadFile=File(...),category:str=Query(...),db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    ensure_category_permission(user, category)
    if not file.filename.lower().endswith(('.xlsx','.xls')): raise HTTPException(400,'Upload an Excel .xlsx or .xls file')
    return await _upload_stage(file,category,db,user.username)
async def _upload_stage(file,category,db,actor="system"):
    if category not in ['environment','health','workforce']: raise HTTPException(400,'Invalid category')
    content=await file.read()
    if len(content)>10*1024*1024: raise HTTPException(413,'Maximum upload size is 10 MB')
    try:
        rows=parse_csv_bytes(content) if file.filename.lower().endswith('.csv') else parse_excel_bytes(content)
    except HTTPException: raise
    except Exception as exc: raise HTTPException(400,f'Could not parse uploaded file: {exc}')
    return _stage_job(db,category,'CSV_IMPORT' if file.filename.lower().endswith('.csv') else 'EXCEL_IMPORT',file.filename,rows,actor=actor)

@app.post('/api/v1/ingestion/upload/geojson')
async def upload_geojson(file:UploadFile=File(...),db:Session=Depends(get_db),user:User=Depends(require_roles('district_admin','environmental_officer'))):
    if not file.filename.lower().endswith('.geojson') and not file.filename.lower().endswith('.json'): raise HTTPException(400,'Upload GeoJSON')
    content=await file.read()
    if len(content)>10*1024*1024: raise HTTPException(413,'Maximum GeoJSON size is 10 MB')
    try: obj,parsed=parse_geojson(content)
    except Exception as exc: raise HTTPException(422,f'Invalid GeoJSON: {exc}')
    created=[]
    for item in parsed:
        zid=item['zone_id']; lat=item['latitude']; lon=item['longitude']
        zone=db.get(Zone,zid)
        if not zone: zone=Zone(id=zid,name=item['name'],district='Imported GeoJSON',latitude=lat,longitude=lon); db.add(zone)
        else: zone.latitude=lat; zone.longitude=lon
        created.append(zid)
    base=Path(__file__).resolve().parents[1]; target=base/'data'/'boundaries'/'imported_zones.geojson'
    target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(obj,indent=2),encoding='utf-8')
    _source_audit(db,'GEOJSON_IMPORT','zones',','.join(created),{'count':len(created),'filename':file.filename},actor=user.username); db.commit()
    return {'status':'imported','zones':created,'note':'GeoJSON zones imported; verify boundaries and official status before operational use.'}

@app.post('/api/v1/ingestion/validate')
def validate_job(job_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    job=db.get(IngestionJob,job_id)
    ensure_job_access(job, user)
    known=_known_zones(db); errors=[]; valid=0; seen=set(); duplicates=0
    for i,row in enumerate(job.staged_data):
        errs=validate_observation(job.category,row,known); key=(row.get('zone_id'),row.get('observed_at'))
        if key in seen: errs.append('Duplicate row in uploaded file'); duplicates+=1
        seen.add(key)
        if errs: errors.append({'row':i+1,'errors':errs})
        else: valid+=1
    job.errors=errors; job.valid_rows=valid; job.invalid_rows=len(errors); job.duplicate_rows=duplicates; job.status='validated' if not errors else 'needs_review'; db.commit(); db.refresh(job)
    return _job_response(job)
@app.post('/api/v1/ingestion/commit')
def commit_import(job_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    job=db.get(IngestionJob,job_id); ensure_job_access(job, user)
    return commit_job(job,db,user.username)
@app.post('/api/v1/ingestion/reject')
def reject_import(job_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    job=db.get(IngestionJob,job_id)
    ensure_job_access(job, user)
    if job.status in ('committed','partially_committed'): raise HTTPException(409,'Committed imports cannot be rejected; use a governed correction process.')
    job.status='rejected'; job.committed_at=_utcnow()
    _source_audit(db,'IMPORT_REJECT','ingestion_job',job.id,{'actor':user.username},actor=user.username)
    db.commit(); db.refresh(job)
    return _job_response(job)

@app.get('/api/v1/ingestion/jobs')
def ingestion_jobs(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    query=db.query(IngestionJob)
    if user.role != 'district_admin': query=query.filter_by(created_by=user.username)
    return [_job_response(j) for j in query.order_by(desc(IngestionJob.created_at)).limit(100).all()]
@app.get('/api/v1/ingestion/jobs/{job_id}')
def ingestion_job(job_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    j=db.get(IngestionJob,job_id); ensure_job_access(j, user)
    return _job_response(j)
@app.get('/api/v1/ingestion/jobs/{job_id}/errors')
def ingestion_errors(job_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    j=db.get(IngestionJob,job_id); ensure_job_access(j, user)
    return {'job_id':job_id,'errors':j.errors}
@app.get('/api/v1/ingestion/my-submissions')
def my_submissions(db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    query=db.query(IngestionJob)
    if user.role != 'district_admin': query=query.filter_by(created_by=user.username)
    rows=query.order_by(desc(IngestionJob.created_at)).limit(100).all()
    return [_job_response(job) | {'created_by': job.created_by} for job in rows]

@app.get('/api/v1/ingestion/templates')
def ingestion_templates(user:User=Depends(get_current_user)):
    return {'environment':['zone_id','observed_at','source_detail','temperature_c','humidity_pct','apparent_temperature_c','aqi','pm25','pm10','no2'],'health':['zone_id','observed_at','source_detail','clinic_visits','heat_complaints','respiratory_complaints','fatigue_reports','first_aid_cases'],'workforce':['zone_id','observed_at','source_detail','shift','exposed_workers','heat_complaints','respiratory_complaints','first_aid_cases','absence_count']}
@app.get('/api/v1/ingestion/data-quality')
def ingestion_quality(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    jobs_query=db.query(IngestionJob)
    if user.role != 'district_admin': jobs_query=jobs_query.filter_by(created_by=user.username)
    recent=[_job_response(j) for j in jobs_query.order_by(desc(IngestionJob.created_at)).limit(10).all()]
    return {'environment_records':db.query(EnvironmentObservation).count(),'health_records':db.query(HealthObservation).count(),'workforce_records':db.query(WorkforceObservation).count(),'jobs':jobs_query.count(),'recent_jobs':recent}

@app.get('/api/v1/alerts')
def get_alerts(status:str|None=None,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    q=db.query(Alert).order_by(desc(Alert.created_at))
    if status:q=q.filter_by(status=status)
    return [{'id':a.id,'zone_id':a.zone_id,'risk_type':a.risk_type,'severity':a.severity,'score':a.score,'confidence':a.confidence,'title':a.title,'explanation':a.explanation,'recommendation':a.recommendation,'responsible_role':a.responsible_role,'status':a.status,'is_simulated':a.is_simulated,'created_at':a.created_at.isoformat()} for a in q.limit(200).all()]
@app.get('/api/v1/alerts/{alert_id}')
def get_alert(alert_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    a=db.get(Alert,alert_id)
    if not a: raise HTTPException(404,'Alert not found')
    return {'id':a.id,'zone_id':a.zone_id,'risk_type':a.risk_type,'severity':a.severity,'score':a.score,'confidence':a.confidence,'title':a.title,'explanation':a.explanation,'recommendation':a.recommendation,'responsible_role':a.responsible_role,'status':a.status,'is_simulated':a.is_simulated,'created_at':a.created_at.isoformat()}
@app.post('/api/v1/alerts/{alert_id}/acknowledge')
def acknowledge(alert_id:int,payload:AcknowledgeInput,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    a=db.get(Alert,alert_id)
    if not a: raise HTTPException(404,'Alert not found')
    a.status='acknowledged'; a.acknowledged_at=_utcnow(); _source_audit(db,'ALERT_ACKNOWLEDGED','alert',alert_id,{'actor':user.username},actor=user.username); db.commit(); return {'status':'acknowledged','alert_id':alert_id}
@app.post('/api/v1/alerts/{alert_id}/actions')
def create_action(alert_id:int,payload:ActionInput,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if not db.get(Alert,alert_id): raise HTTPException(404,'Alert not found')
    obj=InterventionAction(alert_id=alert_id,responsible_role=payload.responsible_role,notes=payload.notes); db.add(obj); _source_audit(db,'ACTION_ASSIGNED','alert',alert_id,{'role':payload.responsible_role,'actor':user.username},actor=user.username); db.commit(); db.refresh(obj)
    return {'action_id':obj.id,'status':obj.status,'responsible_role':obj.responsible_role}
@app.get('/api/v1/actions')
def get_actions(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    return [{'id':x.id,'alert_id':x.alert_id,'responsible_role':x.responsible_role,'notes':x.notes,'status':x.status,
             'created_at':x.created_at.isoformat(),'completed_at':x.completed_at.isoformat() if x.completed_at else None}
            for x in db.query(InterventionAction).order_by(desc(InterventionAction.created_at)).limit(200).all()]

@app.post('/api/v1/actions/{action_id}/complete')
def complete_action(action_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    obj=db.get(InterventionAction,action_id)
    if not obj: raise HTTPException(404,'Action not found')
    obj.status='completed'; obj.completed_at=_utcnow(); _source_audit(db,'ACTION_COMPLETED','intervention_action',action_id,{'actor':user.username},actor=user.username); db.commit(); return {'action_id':action_id,'status':'completed'}

@app.post('/api/v1/simulation/run')
def run_simulation(payload:SimulationInput,db:Session=Depends(get_db),user:User=Depends(require_roles('district_admin'))):
    if payload.zone_id not in _known_zones(db): raise HTTPException(404,'Unknown zone')
    overrides=resolve_scenario_inputs(payload.scenario,payload.model_dump(exclude={'zone_id','scenario'},exclude_none=True))
    results=compute_zone_risks(db,payload.zone_id,save=True,overrides=overrides,simulated=True)
    obj=SimulationRun(zone_id=payload.zone_id,scenario=payload.scenario,inputs=overrides,results={'risks':results}); db.add(obj); _source_audit(db,'SIMULATION_RUN','simulation',payload.zone_id,{'scenario':payload.scenario},actor=user.username); db.commit(); db.refresh(obj)
    return {'simulation_id':obj.id,'zone_id':payload.zone_id,'scenario':payload.scenario,'risks':results,'simulation_only':True}
@app.post('/api/v1/simulation/reset')
def reset_simulation(db:Session=Depends(get_db),user:User=Depends(require_roles('district_admin'))):
    # Remove simulated outputs from active dashboards while preserving run inputs/results for an audit trail.
    alert_count=db.query(Alert).filter_by(is_simulated=True).delete(synchronize_session=False)
    assessment_count=db.query(RiskAssessment).filter_by(is_simulated=True).delete(synchronize_session=False)
    _source_audit(db,'SIMULATION_RESET','simulation','all',{'alerts_removed':alert_count,'assessments_removed':assessment_count,'simulation_runs_retained':True},actor=user.username)
    db.commit()
    return {'status':'reset','simulated_alerts_removed':alert_count,'simulated_assessments_removed':assessment_count,'simulation_runs_retained_for_audit':True,'verified_observations_unchanged':True}

@app.get('/api/v1/validation/summary')
def validation_summary(db:Session=Depends(get_db),user:User=Depends(require_roles('district_admin'))):
    report=run_synthetic_backtest()
    env=db.query(EnvironmentObservation).count()
    report['stored_environment_observations']=env
    report['saved_assessments']=db.query(RiskAssessment).filter_by(is_simulated=False).count()
    all_observations=[]
    for model in [EnvironmentObservation,HealthObservation,WorkforceObservation]:
        all_observations.extend(db.query(model).filter(model.source!='SYNTHETIC').all())
    latency=[max(0.0,(x.ingested_at-x.observed_at).total_seconds()/60) for x in all_observations if x.ingested_at and x.observed_at]
    report['data_latency']={'measured_non_synthetic_records':len(latency),'mean_minutes':round(sum(latency)/len(latency),2) if latency else None,
                            'note':'Calculated from stored ingestion and observation timestamps; synthetic backfill rows are excluded.'}
    return report

@app.post('/api/v1/data/refresh')
def refresh_environment(db:Session=Depends(get_db),user:User=Depends(require_roles('district_admin','environmental_officer'))):
    results=[]
    for z in db.query(Zone).all():
        try:
            params={'latitude':z.latitude,'longitude':z.longitude,'current':'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m','timezone':'auto'}
            r=httpx.get('https://api.open-meteo.com/v1/forecast',params=params,timeout=12); r.raise_for_status(); cur=r.json()['current']
            db.add(EnvironmentObservation(zone_id=z.id,observed_at=parse_dt(cur.get('time')) if cur.get('time') else _utcnow(),temperature_c=cur.get('temperature_2m'),humidity_pct=cur.get('relative_humidity_2m'),apparent_temperature_c=cur.get('apparent_temperature'),source='REAL_API',source_detail='Open-Meteo API',quality_status='valid'))
            results.append({'zone_id':z.id,'status':'success','temperature_c':cur.get('temperature_2m')})
        except Exception as exc: results.append({'zone_id':z.id,'status':'failed','message':str(exc)[:180]})
    status=db.query(DataSourceStatus).filter_by(source='OPEN_METEO').first() or DataSourceStatus(source='OPEN_METEO')
    successes=sum(x['status']=='success' for x in results); status.status='connected' if successes else 'failed'; status.last_success_at=_utcnow() if successes else status.last_success_at; status.message=f'{successes}/{len(results)} zones refreshed'; db.add(status); db.commit()
    for z in db.query(Zone).all(): compute_zone_risks(db,z.id,save=True)
    return {'results':results,'success_count':successes,'total_zones':len(results)}

@app.post('/api/v1/data/refresh/air-quality')
def refresh_air_quality(db:Session=Depends(get_db),user:User=Depends(require_roles('district_admin','environmental_officer'))):
    if not settings.openaq_api_key:
        status=db.query(DataSourceStatus).filter_by(source='OPENAQ').first() or DataSourceStatus(source='OPENAQ')
        status.status='not_configured'; status.message='Set OPENAQ_API_KEY to enable OpenAQ. CPCB AQI may also be imported from official CSV/API exports.'; db.add(status); db.commit()
        return {'status':'not_configured','message':status.message}
    results=[]
    for z in db.query(Zone).all():
        try:
            result=fetch_nearby_particulates(z.latitude,z.longitude,settings.openaq_api_key)
            if result.get('status')=='success':
                when=result.get('observed_at')
                try: observed=parse_dt(when) if when else _utcnow()
                except Exception: observed=_utcnow()
                db.add(EnvironmentObservation(zone_id=z.id,observed_at=observed,pm25=result.get('pm25'),pm10=result.get('pm10'),source='OPENAQ',source_detail=str(result.get('station_name') or 'OpenAQ API'),quality_status='valid'))
                results.append({'zone_id':z.id,'status':'success','station_name':result.get('station_name'),'pm25':result.get('pm25'),'pm10':result.get('pm10')})
            else: results.append({'zone_id':z.id,'status':result.get('status'),'message':result.get('message')})
        except Exception as exc: results.append({'zone_id':z.id,'status':'failed','message':str(exc)[:180]})
    status=db.query(DataSourceStatus).filter_by(source='OPENAQ').first() or DataSourceStatus(source='OPENAQ')
    ok=sum(x['status']=='success' for x in results); status.status='connected' if ok else 'failed'; status.last_success_at=_utcnow() if ok else status.last_success_at; status.message=f'{ok}/{len(results)} zones returned PM observations'; db.add(status); db.commit()
    for z in db.query(Zone).all(): compute_zone_risks(db,z.id,save=True)
    return {'status':status.status,'results':results,'note':'PM2.5 and PM10 are concentrations, not AQI.'}

@app.get('/api/v1/data-quality')
def data_quality(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    return {'counts':{'environment':db.query(EnvironmentObservation).count(),'health':db.query(HealthObservation).count(),'workforce':db.query(WorkforceObservation).count()},'sources':[{'source':x.source,'status':x.status,'last_success_at':x.last_success_at.isoformat() if x.last_success_at else None,'message':x.message} for x in db.query(DataSourceStatus).all()]}
@app.get('/api/v1/audit')
def audit_logs(db:Session=Depends(get_db),user:User=Depends(require_roles('district_admin'))):
    return [{'id':x.id,'actor':x.actor,'action':x.action,'entity_type':x.entity_type,'entity_id':x.entity_id,'details':x.details,'created_at':x.created_at.isoformat()} for x in db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(200).all()]
