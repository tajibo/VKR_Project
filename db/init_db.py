# db/init_db.py
from db.database import engine, Base
import db.models  # noqa: F401

def init_db():
    print("Создание таблиц…")
    Base.metadata.create_all(bind=engine)
    print("Готово ✅")

if __name__ == "__main__":
    init_db()
