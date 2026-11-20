from app.core.security import hash_password
from app.database.connection import SessionLocal
from app.database.models import User

DEMO_USERS = [
    ('admin', 'District Administrator', 'district_admin', 'Admin@Sentinel2026'),
    ('health', 'Health Department Officer', 'health_officer', 'Health@Sentinel2026'),
    ('environment', 'Environmental Department Officer', 'environmental_officer', 'Env@Sentinel2026'),
    ('workplace', 'Workplace Safety Officer', 'workplace_safety_officer', 'Work@Sentinel2026'),
]


def ensure_demo_users():
    db = SessionLocal()
    try:
        for username, display_name, role, password in DEMO_USERS:
            user = db.query(User).filter_by(username=username).first()
            if not user:
                db.add(User(username=username, display_name=display_name, role=role,
                            password_hash=hash_password(password), is_active=True))
        db.commit()
    finally:
        db.close()
