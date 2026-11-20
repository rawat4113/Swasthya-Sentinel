from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import init_db
from scripts.generate_data import seed
from app.core.config import settings

if __name__ == '__main__':
    init_db()
    print(seed(force=False))
    if settings.demo_users_enabled:
        from app.core.bootstrap import ensure_demo_users
        ensure_demo_users()
        print('Demo role accounts are ready. See README.md for local demo credentials.')
