from statistics import median
import math
from pathlib import Path
import yaml

_CFG_PATH=Path(__file__).resolve().parents[2]/'config'/'risk_thresholds.yaml'
try:
    with open(_CFG_PATH,encoding='utf-8') as _f: RISK_CONFIG=yaml.safe_load(_f) or {}
except Exception:
    RISK_CONFIG={}

def robust_anomaly_score(values, current=None):
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not vals:
        return 0.0, {'baseline': None, 'robust_z': None, 'sample_count': 0}
    current = float(current if current is not None else vals[-1])
    base = vals[:-1] if len(vals) > 1 and current == vals[-1] else vals
    if not base: base = vals
    med = median(base)
    mad = median([abs(x-med) for x in base])
    rz = 0.6745 * (current-med) / (mad if mad > 1e-6 else max(abs(med)*0.05, 1.0))
    score = max(0.0, min(100.0, (rz-0.5)*20))
    return score, {'baseline': round(med, 2), 'robust_z': round(rz, 2), 'sample_count': len(base)}

def ewma(values, alpha=0.3):
    vals=[float(v) for v in values if v is not None]
    if not vals: return None
    result=vals[0]
    for v in vals[1:]: result=alpha*v+(1-alpha)*result
    return result

def severity(score):
    cfg=RISK_CONFIG
    if score <= float(cfg.get('normal',29)): return 'Normal'
    if score <= float(cfg.get('watch',49)): return 'Watch'
    if score <= float(cfg.get('elevated',69)): return 'Elevated'
    return 'High'

def _clamp(v): return max(0.0, min(100.0, float(v)))

def calculate_risk(risk_type, environment, health, workforce, history=None, simulated=False):
    history = history or {}
    if risk_type == 'heat':
        apparent = environment.get('apparent_temperature_c')
        if apparent is None: apparent = environment.get('temperature_c')
        # Demonstration normalization only; not a medical heat-stress threshold.
        env = _clamp((float(apparent or 20)-24)*5.0)
        clinical_values = history.get('heat_complaints', [])
        clinical, clinical_meta = robust_anomaly_score(clinical_values, health.get('heat_complaints', 0))
        work_values = history.get('work_heat_complaints', [])
        work, work_meta = robust_anomaly_score(work_values, workforce.get('heat_complaints', 0))
        weights=RISK_CONFIG.get('heat_weights',{'environment':.40,'clinical':.35,'workforce':.25})
        score = _clamp(float(weights['environment'])*env + float(weights['clinical'])*clinical + float(weights['workforce'])*work)
        evidence = {
            'environmental_score': round(env,1), 'clinical_score': round(clinical,1), 'workforce_score': round(work,1),
            'apparent_temperature_c': apparent, 'heat_complaints': health.get('heat_complaints',0),
            'workforce_heat_complaints': workforce.get('heat_complaints',0),
            'clinical_baseline': clinical_meta['baseline'], 'clinical_robust_z': clinical_meta['robust_z'],
            'workforce_baseline': work_meta['baseline'], 'workforce_robust_z': work_meta['robust_z']}
        explanation = (f"Heat-risk score is {score:.1f}/100. Environmental contribution is {env:.1f}, "
                       f"clinical-service anomaly is {clinical:.1f}, and workforce anomaly is {work:.1f}. "
                       f"Apparent temperature is {apparent if apparent is not None else 'unavailable'} °C.")
        sample_ok = min(clinical_meta['sample_count'], work_meta['sample_count']) >= 7
    else:
        pm25=environment.get('pm25'); pm10=environment.get('pm10'); aqi=environment.get('aqi')
        # PM values are pollutant concentrations, not AQI. This is a prototype normalized indicator.
        pollutant = max([float(x) for x in [pm25, pm10] if x is not None], default=None)
        env = _clamp((float(aqi)/3 if aqi is not None else (float(pollutant)*1.4 if pollutant is not None else 0)))
        clinical_values=history.get('respiratory_complaints', [])
        clinical, clinical_meta=robust_anomaly_score(clinical_values, health.get('respiratory_complaints',0))
        work_values=history.get('work_respiratory_complaints', [])
        work, work_meta=robust_anomaly_score(work_values, workforce.get('respiratory_complaints',0))
        weights=RISK_CONFIG.get('respiratory_weights',{'environment':.40,'clinical':.35,'workforce':.25})
        score=_clamp(float(weights['environment'])*env+float(weights['clinical'])*clinical+float(weights['workforce'])*work)
        evidence={'environmental_score':round(env,1),'clinical_score':round(clinical,1),'workforce_score':round(work,1),
                  'aqi':aqi,'pm25':pm25,'pm10':pm10,'respiratory_complaints':health.get('respiratory_complaints',0),
                  'workforce_respiratory_complaints':workforce.get('respiratory_complaints',0),
                  'clinical_baseline':clinical_meta['baseline'],'clinical_robust_z':clinical_meta['robust_z'],
                  'workforce_baseline':work_meta['baseline'],'workforce_robust_z':work_meta['robust_z']}
        explanation=(f"Respiratory-risk score is {score:.1f}/100. Environmental contribution is {env:.1f}, "
                     f"clinical-service anomaly is {clinical:.1f}, and workforce anomaly is {work:.1f}. "
                     f"Pollutant measurements are kept distinct from official AQI values.")
        sample_ok=min(clinical_meta['sample_count'],work_meta['sample_count'])>=7
    # Confidence measures availability + baseline sufficiency; never reduce risk because inputs are missing.
    families = int(bool(environment.get('available', any(environment.get(k) is not None for k in ['temperature_c','apparent_temperature_c','pm25','pm10','aqi']))))
    families += int(bool(health.get('available', True)))
    families += int(bool(workforce.get('available', True)))
    confidence = _clamp((families/3)*70 + (30 if sample_ok else (10 if families else 0)))
    evidence['independent_signal_families'] = families
    evidence['simulated'] = simulated
    evidence['confidence_note'] = 'Confidence reflects input availability and baseline sufficiency; risk is not reduced for missing inputs.'
    return {'risk_type':risk_type,'score':round(score,1),'confidence':round(confidence,1),'severity':severity(score),
            'evidence':evidence,'explanation':explanation,'is_simulated':simulated}
