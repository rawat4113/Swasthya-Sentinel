from app.database.models import EnvironmentObservation, HealthObservation, WorkforceObservation
from app.processing.quality import parse_dt

def insert_record(db, category, row, source):
    common={'zone_id':row['zone_id'],'observed_at':parse_dt(row['observed_at']),'source':source,'source_detail':str(row.get('source_detail') or row.get('provider') or row.get('source_name') or ''),'quality_status':'valid'}
    mapping={
      'environment':(EnvironmentObservation,['temperature_c','humidity_pct','apparent_temperature_c','aqi','pm25','pm10','no2']),
      'health':(HealthObservation,['clinic_visits','heat_complaints','respiratory_complaints','fatigue_reports','first_aid_cases']),
      'workforce':(WorkforceObservation,['shift','exposed_workers','heat_complaints','respiratory_complaints','first_aid_cases','absence_count'])}
    model, fields=mapping[category]
    values={k:(row.get(k) if row.get(k) not in ('',None) else (0 if k not in ('shift',) else 'Day')) for k in fields}
    obj=model(**common,**values)
    db.add(obj)
    return obj
