from pathlib import Path
import yaml

CFG=Path(__file__).resolve().parents[2]/'config'/'action_rules.yaml'
try:
    ACTIONS=yaml.safe_load(CFG.read_text(encoding='utf-8')) or {}
except Exception:
    ACTIONS={}

def recommendation_for(risk_type, severity):
    config=ACTIONS.get(risk_type,{})
    actions=config.get('actions',[])
    fallback=(['Review water access, shade/cooling, recovery breaks and high-exposure work schedules; verify aggregated health-service reports.'] if risk_type=='heat'
              else ['Verify air-quality station readings, assess exposure controls and coordinate appropriate public-health and healthcare readiness.'])
    return (' '.join(actions or fallback),config.get('responsible_role','District Health Officer'))
