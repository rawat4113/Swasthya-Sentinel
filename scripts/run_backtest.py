from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.validation.backtest import run_synthetic_backtest
if __name__=='__main__': print(json.dumps(run_synthetic_backtest(),indent=2))
