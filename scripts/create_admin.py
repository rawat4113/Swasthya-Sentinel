"""Create the first district administrator when seeded demo accounts are disabled."""
from pathlib import Path
import getpass
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import init_db
from app.database.connection import SessionLocal
from app.database.models import User
from app.core.security import hash_password


def main():
    init_db()
    username = input('Administrator username: ').strip()
    display_name = input('Administrator display name: ').strip()
    password = getpass.getpass('Password (minimum 10 characters): ')
    confirm = getpass.getpass('Confirm password: ')
    if password != confirm:
        raise SystemExit('Passwords do not match.')
    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        raise SystemExit(str(exc))
    db = SessionLocal()
    try:
        if db.query(User).filter_by(username=username).first():
            raise SystemExit('That username already exists.')
        db.add(User(username=username, display_name=display_name, role='district_admin',
                    password_hash=password_hash, is_active=True))
        db.commit()
        print(f'District administrator account {username!r} created.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
