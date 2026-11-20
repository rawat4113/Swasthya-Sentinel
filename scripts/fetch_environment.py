from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app
if __name__=='__main__':
    with TestClient(app) as client:
        r=client.post('/api/v1/data/refresh')
        print(r.status_code, r.json())
