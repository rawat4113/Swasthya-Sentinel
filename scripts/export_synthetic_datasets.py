from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.database.connection import SessionLocal
from app.database.models import EnvironmentObservation,HealthObservation,WorkforceObservation

ROOT=Path(__file__).resolve().parents[1]

def export():
    db=SessionLocal(); out=ROOT/'data'/'synthetic'; out.mkdir(parents=True,exist_ok=True)
    try:
        specs=[('environment',EnvironmentObservation,['zone_id','observed_at','ingested_at','temperature_c','humidity_pct','apparent_temperature_c','aqi','pm25','pm10','no2','source','source_detail']),
               ('health',HealthObservation,['zone_id','observed_at','ingested_at','clinic_visits','heat_complaints','respiratory_complaints','fatigue_reports','first_aid_cases','source','source_detail']),
               ('workforce',WorkforceObservation,['zone_id','observed_at','ingested_at','shift','exposed_workers','heat_complaints','respiratory_complaints','first_aid_cases','absence_count','source','source_detail'])]
        results={}
        for name,model,fields in specs:
            rows=db.query(model).filter_by(source='SYNTHETIC').order_by(model.observed_at).all()
            frame=pd.DataFrame([{f:(getattr(x,f).isoformat() if f in ('observed_at','ingested_at') else getattr(x,f)) for f in fields} for x in rows])
            path=out/f'{name}_180day_synthetic.csv'; frame.to_csv(path,index=False); results[name]={'path':str(path.relative_to(ROOT)),'rows':len(frame)}
        return results
    finally: db.close()

if __name__=='__main__': print(export())
