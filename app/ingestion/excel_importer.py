import io
import pandas as pd

def parse_excel_bytes(content: bytes, max_rows: int = 10000):
    frame=pd.read_excel(io.BytesIO(content))
    if len(frame)>max_rows: raise ValueError(f'Maximum {max_rows:,} rows per import')
    return frame.where(pd.notnull(frame),None).to_dict(orient='records')
