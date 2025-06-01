# db/database.py

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# URL вашей БД (PostgreSQL)
DATABASE_URL = "postgresql+psycopg2://postgres:dbDTProject05@localhost:5432/ai_bot_db"

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            print("✅ Успешное подключение к PostgreSQL:")
            for row in result:
                print(row)
    except Exception as e:
        print("❌ Ошибка подключения к базе данных:", e)
