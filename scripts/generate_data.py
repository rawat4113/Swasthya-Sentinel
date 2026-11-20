from datetime import datetime, timedelta
import random, sys, yaml
from datetime import timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import init_db
from app.database.connection import SessionLocal
from app.database.models import (Zone, EnvironmentObservation, HealthObservation, WorkforceObservation, RiskAssessment, Alert, IngestionJob, InterventionAction, AuditLog, SimulationRun, DataSourceStatus)

DEFAULT_ZONES=[('ZONE_01','Illustrative North Zone',22.48,70.05),('ZONE_02','Illustrative Central Zone',22.46,70.07),('ZONE_03','Illustrative Industrial Zone',22.44,70.09)]

def load_zones():
    cfg=Path(__file__).resolve().parents[1]/'config'/'district.yaml'
    try:
        data=yaml.safe_load(cfg.read_text(encoding='utf-8')) or {}
        zones=data.get('zones',[])
        return [(str(z['id']),str(z['name']),float(z['latitude']),float(z['longitude'])) for z in zones], data.get('district',{}).get('name','Illustrative Demo District')
    except Exception:
        return DEFAULT_ZONES,'Illustrative Demo District'

def seed(force=False):
    init_db(); db=SessionLocal(); zones,district_name=load_zones()
    try:
        if db.query(Zone).count() and not force: return {'status':'already_seeded','zones':db.query(Zone).count()}
        if force:
            for model in [InterventionAction,Alert,RiskAssessment,SimulationRun,IngestionJob,AuditLog,DataSourceStatus,
                          EnvironmentObservation,HealthObservation,WorkforceObservation,Zone]:
                db.query(model).delete(synchronize_session=False)
        for zid,name,lat,lon in zones:
            if not db.get(Zone,zid): db.add(Zone(id=zid,name=name,district=district_name,latitude=lat,longitude=lon,population_reference=0))
        db.commit()
        rng=random.Random(4113); today=datetime.now(timezone.utc).replace(tzinfo=None,hour=12,minute=0,second=0,microsecond=0)
        for i in range(180):
            day=today-timedelta(days=179-i)
            for j,(zid,_,_,_) in enumerate(zones):
                seasonal=4*__import__('math').sin((i/180)*6.28)
                temp=29+seasonal+rng.gauss(0,2)+j*.5
                humidity=max(35,min(90,65+rng.gauss(0,8)))
                apparent=temp+max(0,(humidity-50)*.07)
                pm25=max(8,25+rng.gauss(0,8)+j*3); pm10=pm25*1.65+rng.gauss(0,4)
                heat=max(0,int(rng.gauss(4+j,2))); resp=max(0,int(rng.gauss(5+j,2)))
                # Seed two contained illustrative events for a meaningful first demo.
                if i>=176 and zid=='ZONE_03':
                    temp+=7; apparent+=8; heat+=14; resp+=2
                if i>=176 and zid=='ZONE_02':
                    pm25+=55; pm10+=75; resp+=13
                db.add(EnvironmentObservation(zone_id=zid,observed_at=day,temperature_c=round(temp,1),humidity_pct=round(humidity,1),apparent_temperature_c=round(apparent,1),pm25=round(pm25,1),pm10=round(pm10,1),source='SYNTHETIC',quality_status='valid'))
                db.add(HealthObservation(zone_id=zid,observed_at=day,clinic_visits=100+resp+heat,heat_complaints=heat,respiratory_complaints=resp,fatigue_reports=max(0,int(rng.gauss(5,2))),first_aid_cases=max(0,int(rng.gauss(2,1))),source='SYNTHETIC',quality_status='valid'))
                workers=100+j*40
                db.add(WorkforceObservation(zone_id=zid,observed_at=day,shift='All shifts',exposed_workers=workers,heat_complaints=max(0,int(heat*.6+rng.gauss(1,1))),respiratory_complaints=max(0,int(resp*.5+rng.gauss(1,1))),first_aid_cases=max(0,int(rng.gauss(2,1))),absence_count=max(0,int(rng.gauss(4,2))),source='SYNTHETIC',quality_status='valid'))
        db.commit()
        return {'status':'seeded','zones':len(zones),'days':180,'records_per_category':180*len(zones)}
    finally: db.close()

if __name__=='__main__': print(seed(force='--force' in sys.argv))
