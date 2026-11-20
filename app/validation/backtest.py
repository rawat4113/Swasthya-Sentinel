from datetime import datetime, timedelta
import random
from app.risk_engine.scoring import robust_anomaly_score

def _metrics(rows, prediction_key):
    tp=sum(1 for r in rows if r['actual'] and r[prediction_key])
    fp=sum(1 for r in rows if not r['actual'] and r[prediction_key])
    fn=sum(1 for r in rows if r['actual'] and not r[prediction_key])
    tn=sum(1 for r in rows if not r['actual'] and not r[prediction_key])
    sensitivity=tp/(tp+fn) if tp+fn else 0
    ppv=tp/(tp+fp) if tp+fp else 0
    precision=ppv
    return {'true_positive':tp,'false_positive':fp,'false_negative':fn,'true_negative':tn,
            'sensitivity':round(sensitivity,3),'positive_predictive_value':round(ppv,3),
            'false_alerts_per_zone_week':round(fp/(max(1,len(rows))/7),3)}

def run_synthetic_backtest(seed=4113):
    """Evaluate synthetic known-event windows; outputs are not clinical validation."""
    rng=random.Random(seed); rows=[]; event_starts={('ZONE_01','heat'):70,('ZONE_02','respiratory'):82}
    for zone in ['ZONE_01','ZONE_02','ZONE_03']:
        for risk in ['heat','respiratory']:
            history=[]
            for day in range(110):
                actual_start=event_starts.get((zone,risk),999)
                is_early=(day>=actual_start-5 and day<actual_start)
                actual=day>=actual_start and day<actual_start+8
                if risk=='heat':
                    env=30+rng.gauss(0,1.5)+(5 if is_early else (9 if actual else 0))
                    clinical=max(0,round(rng.gauss(4,1)+(5 if is_early else (15 if actual else 0))))
                    workforce=max(0,round(rng.gauss(3,1)+(4 if is_early else (12 if actual else 0))))
                    fixed=env>=39
                    hist_score=robust_anomaly_score([x[0] for x in history[-28:]],clinical)[0] if len(history)>=7 else 0
                    multi_env=min(100,max(0,(env-30)*8)); multi=min(100,.4*multi_env+.35*hist_score+.25*min(100,workforce*5))
                    history.append((clinical,))
                else:
                    env=25+rng.gauss(0,5)+(45 if is_early else (90 if actual else 0))
                    clinical=max(0,round(rng.gauss(5,1)+(5 if is_early else (17 if actual else 0))))
                    workforce=max(0,round(rng.gauss(3,1)+(4 if is_early else (13 if actual else 0))))
                    fixed=env>=75
                    hist_score=robust_anomaly_score([x[0] for x in history[-28:]],clinical)[0] if len(history)>=7 else 0
                    multi_env=min(100,max(0,env*1.1)); multi=min(100,.4*multi_env+.35*hist_score+.25*min(100,workforce*5))
                    history.append((clinical,))
                statistical=hist_score>=35 or fixed
                multisignal=multi>=48
                rows.append({'zone_id':zone,'risk_type':risk,'day':day,'actual':actual,'fixed':fixed,'statistical':statistical,'multisignal':multisignal})
    reports={k:_metrics(rows,k) for k in ['fixed','statistical','multisignal']}
    lead={}
    for key in ['fixed','statistical','multisignal']:
        leads=[]
        for (zone,risk),start in event_starts.items():
            candidates=[r['day'] for r in rows if r['zone_id']==zone and r['risk_type']==risk and r[key] and max(0,start-14)<=r['day']<=start]
            if candidates: leads.append(max(0,start-min(candidates)))
        lead[key]=round(sum(leads)/len(leads),2) if leads else None
        reports[key]['mean_lead_time_days']=lead[key]
    return {'validation_type':'synthetic_known_event_backtest','event_windows':len(event_starts),'records_evaluated':len(rows),'models':reports,
            'limitations':'Synthetic injected events with known onset. Metrics demonstrate pipeline evaluation only; not clinical accuracy or real-world health impact.'}
