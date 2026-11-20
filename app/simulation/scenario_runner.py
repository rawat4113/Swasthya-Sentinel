from app.simulation.scenario_generator import defaults_for_scenario

def resolve_scenario_inputs(scenario, supplied):
    """Apply scenario defaults, then let explicitly supplied values override them."""
    values=defaults_for_scenario(scenario)
    values.update({k:v for k,v in supplied.items() if v is not None})
    return values
