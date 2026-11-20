import math
from datetime import date, datetime
from app.ingestion.column_mapper import normalize_columns

def normalize_record(record):
    row=normalize_columns(record)
    if 'observed_at' not in row and 'date' in row: row['observed_at']=row['date']
    cleaned={}
    for key,value in row.items():
        if value is None:
            cleaned[key]=None; continue
        if hasattr(value,'to_pydatetime'):
            value=value.to_pydatetime()
        if isinstance(value,(datetime,date)):
            cleaned[key]=value.isoformat(); continue
        if hasattr(value,'item'):
            try: value=value.item()
            except Exception: pass
        if isinstance(value,float) and math.isnan(value): value=None
        cleaned[key]=value
    return cleaned
