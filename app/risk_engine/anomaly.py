from sklearn.ensemble import IsolationForest
import numpy as np

def isolation_anomaly_score(rows):
    """Return anomaly labels for numeric feature rows; needs at least 10 rows."""
    if len(rows) < 10: return [0] * len(rows)
    arr=np.asarray(rows,dtype=float)
    model=IsolationForest(contamination='auto', random_state=42)
    return [1 if p == -1 else 0 for p in model.fit_predict(arr)]
