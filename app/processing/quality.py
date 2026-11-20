from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import math

def validate_record(category, row, known_zones):
    errors=[]
    if row.get('zone_id') not in known_zones: errors.append('Unknown zone_id')
    if not row.get('observed_at'): errors.append('Missing observed_at')
    else:
        try: datetime.fromisoformat(str(row['observed_at']).replace('Z','+00:00'))
        except ValueError: errors.append('Invalid observed_at; use ISO 8601')
    numeric_fields={
      'environment':['temperature_c','humidity_pct','apparent_temperature_c','aqi','pm25','pm10','no2'],
      'health':['clinic_visits','heat_complaints','respiratory_complaints','fatigue_reports','first_aid_cases'],
      'workforce':['exposed_workers','heat_complaints','respiratory_complaints','first_aid_cases','absence_count']}
    for f in numeric_fields.get(category,[]):
        v=row.get(f)
        if v in (None,''): continue
        try:
            n=float(v)
            if not math.isfinite(n): errors.append(f'{f} must be a finite number'); continue
            if category in ('health','workforce') and n < 0: errors.append(f'{f} cannot be negative')
            if category=='environment' and f=='humidity_pct' and not 0<=n<=100: errors.append('humidity_pct must be 0–100')
            if category=='environment' and f in ('pm25','pm10','aqi') and n<0: errors.append(f'{f} cannot be negative')
        except (ValueError,TypeError): errors.append(f'{f} must be numeric')
    return errors

def parse_dt(value):
    dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=ZoneInfo('Asia/Kolkata'))
    return dt.astimezone(timezone.utc).replace(tzinfo=None)
