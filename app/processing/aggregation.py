import pandas as pd

def aggregate_by_zone_day(frame, count_columns):
    """Aggregate records by zone and calendar day without inferring individual outcomes."""
    if frame.empty: return frame
    data=frame.copy(); data['observed_at']=pd.to_datetime(data['observed_at'],utc=True).dt.date
    return data.groupby(['zone_id','observed_at'],as_index=False)[count_columns].sum(min_count=1)
