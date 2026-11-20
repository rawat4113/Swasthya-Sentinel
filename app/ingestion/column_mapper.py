ALIASES={
 'source_detail':['provider','source_name','data_provider','origin'], 'zone_id':['zone','zoneid','area_id','monitoring_zone'], 'observed_at':['date','datetime','timestamp','observation_time'],
 'temperature_c':['temperature','temp_c','temp'], 'humidity_pct':['humidity','relative_humidity'],
 'apparent_temperature_c':['feels_like','apparent_temp'], 'aqi':['air_quality_index'], 'pm25':['pm2_5','pm2.5'], 'pm10':['pm_10'],
 'clinic_visits':['visits','total_visits'], 'heat_complaints':['heat_cases','heat_reports'],
 'respiratory_complaints':['respiratory_cases','breathing_complaints'], 'fatigue_reports':['fatigue'],
 'first_aid_cases':['first_aid'], 'exposed_workers':['workers_exposed'], 'absence_count':['absences'], 'shift':['work_shift']}

def normalize_columns(row):
    out={}
    for key,value in row.items():
        normalized=str(key).strip().lower().replace(' ','_').replace('-','_')
        out[normalized]=value
    for canonical, aliases in ALIASES.items():
        if canonical not in out:
            for alias in aliases:
                if alias in out: out[canonical]=out[alias]; break
    return out
