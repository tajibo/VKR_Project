from .database import engine, Base
import db.models 

def init_db():
    print("Создание таблиц в базе…")
    Base.metadata.create_all(bind=engine)
    print("Готово ✅")

if __name__ == "__main__":
    init_db()
