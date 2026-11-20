from app.processing.quality import validate_record, parse_dt

def validate_observation(category, record, known_zones):
    return validate_record(category,record,known_zones)
