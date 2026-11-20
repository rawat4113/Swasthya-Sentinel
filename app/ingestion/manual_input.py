from app.ingestion.data_cleaner import normalize_record
from app.ingestion.data_validator import validate_observation

def prepare_manual_input(category, record, known_zones):
    row=normalize_record(record)
    errors=validate_observation(category,row,known_zones)
    if errors: return None,errors
    return row,[]
