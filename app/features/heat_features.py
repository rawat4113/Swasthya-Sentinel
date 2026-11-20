def build_heat_features(environment, health, workforce):
    apparent=environment.get('apparent_temperature_c')
    if apparent is None: apparent=environment.get('temperature_c')
    return {'apparent_temperature_c':apparent,'humidity_pct':environment.get('humidity_pct'),
            'heat_complaints':health.get('heat_complaints'),'workforce_heat_complaints':workforce.get('heat_complaints')}
