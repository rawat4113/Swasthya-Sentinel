from pathlib import Path
import os
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / '.env')

class Settings:
    app_name = os.getenv('APP_NAME', 'Swasthya Sentinel')
    app_env = os.getenv('APP_ENV', 'development')
    database_file = os.getenv('DATABASE_FILE', str(ROOT_DIR / 'swasthya_sentinel.json'))
    openaq_api_key = os.getenv('OPENAQ_API_KEY', '')
    data_mode = os.getenv('DATA_MODE', 'demo')
    auto_refresh_enabled = os.getenv('AUTO_REFRESH_ENABLED', 'false').lower() == 'true'
    refresh_interval_minutes = int(os.getenv('REFRESH_INTERVAL_MINUTES', '30'))
    min_group_size = int(os.getenv('MIN_GROUP_SIZE', '10'))
    district_config = os.getenv('DISTRICT_CONFIG', str(ROOT_DIR / 'config' / 'district.yaml'))
    auth_secret_key = os.getenv('AUTH_SECRET_KEY', 'CHANGE-ME-Swasthya-Sentinel-local-demo-secret')
    demo_users_enabled = os.getenv('DEMO_USERS_ENABLED', 'true').lower() == 'true'
    access_token_hours = int(os.getenv('ACCESS_TOKEN_HOURS', '8'))

settings = Settings()
