SCENARIO_DEFAULTS={
 'heatwave':{'temperature_c':43,'humidity_pct':78,'apparent_temperature_c':50,'heat_complaints':24,'workforce_heat_complaints':15},
 'pollution_spike':{'pm25':105,'pm10':170,'aqi':180,'respiratory_complaints':25,'workforce_respiratory_complaints':15},
 'combined_emergency':{'temperature_c':43,'humidity_pct':80,'apparent_temperature_c':51,'pm25':100,'pm10':165,'aqi':190,'heat_complaints':24,'respiratory_complaints':25,'workforce_heat_complaints':15,'workforce_respiratory_complaints':15},
}

def defaults_for_scenario(name):
    return dict(SCENARIO_DEFAULTS.get(name,{}))
