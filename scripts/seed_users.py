# scripts/seed_users.py

import bcrypt
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import Role, User

def get_password_hash(plain_password: str) -> str:
    # Генерируем соль и хэшируем пароль
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def seed():
    db: Session = SessionLocal()
    try:
        # 1. Создаём роли, если их нет
        existing_roles = {r.name for r in db.query(Role).all()}
        roles_to_create = []
        for role_name in ["admin", "manager", "client"]:
            if role_name not in existing_roles:
                roles_to_create.append(Role(name=role_name))
        if roles_to_create:
            db.add_all(roles_to_create)
            db.commit()

        # Получаем объекты ролей из БД (свежие)
        role_admin   = db.query(Role).filter(Role.name == "admin").first()
        role_manager = db.query(Role).filter(Role.name == "manager").first()
        role_client  = db.query(Role).filter(Role.name == "client").first()

        # 2. Создаём трех пользователей с логинами и паролями
        # Здесь — примерные учетные данные, которые вы потом укажете во Введении ВКР
        initial_users = [
            {
                "username": "admin_user@example.com",
                "password": "AdminPass123!",
                "role": role_admin,
            },
            {
                "username": "manager_user@example.com",
                "password": "ManagerPass123!",
                "role": role_manager,
            },
            {
                "username": "client_user@example.com",
                "password": "ClientPass123!",
                "role": role_client,
            },
        ]

        for user_data in initial_users:
            exists = db.query(User).filter(User.username == user_data["username"]).first()
            if exists:
                print(f"[seed] Пользователь {user_data['username']} уже существует, пропускаем.")
                continue
            hashed = get_password_hash(user_data["password"])
            new_user = User(
                username=user_data["username"],
                password_hash=hashed,
                role_id=user_data["role"].id,
                telegram_id=None  # пока нет привязки к Telegram
            )
            db.add(new_user)
        db.commit()
        print("[seed] Успешно добавлены роли и первичные пользователи.")
    except Exception as e:
        db.rollback()
        print(f"[seed][ERROR] {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
