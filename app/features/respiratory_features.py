def build_respiratory_features(environment, health, workforce):
    return {'aqi':environment.get('aqi'),'pm25':environment.get('pm25'),'pm10':environment.get('pm10'),
            'respiratory_complaints':health.get('respiratory_complaints'),
            'workforce_respiratory_complaints':workforce.get('respiratory_complaints')}
