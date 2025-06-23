# scripts/seed_users.py
import bcrypt
from db.database import get_db
from db.models import Role, User

def get_password_hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def seed():
    with get_db() as db:
        existing = {r.name for r in db.query(Role).all()}
        for r in ("admin", "manager", "client"):
            if r not in existing:
                db.add(Role(name=r))
        db.commit()

        roles = {r.name: r for r in db.query(Role).all()}
        users = [
            ("admin_user@example.com", "AdminPass123!", roles["admin"]),
            ("manager_user@example.com", "ManagerPass123!", roles["manager"]),
            ("client_user@example.com", "ClientPass123!", roles["client"]),
        ]
        for uname, pwd, role in users:
            if not db.query(User).filter(User.username == uname).first():
                db.add(User(username=uname, password_hash=get_password_hash(pwd), role_id=role.id))
        db.commit()
        print("Сидирование завершено.")

if __name__ == "__main__":
    seed()
