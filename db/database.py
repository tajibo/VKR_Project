# db/database.py

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# URL вашей БД (PostgreSQL)
DATABASE_URL = "postgresql+psycopg2://postgres:dbDTProject05@localhost:5432/ai_bot_db"

# Создание синхронного движка
engine = create_engine(DATABASE_URL, echo=True, future=True)

# Конфигурация сессии (синхронная)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Базовый класс для моделей (импортируется в db/models.py)
Base = declarative_base()

# Проверка соединения (если запускать этот файл напрямую)
if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            print("✅ Успешное подключение к PostgreSQL:")
            for row in result:
                print(row)
    except Exception as e:
        print("❌ Ошибка подключения к базе данных:", e)
