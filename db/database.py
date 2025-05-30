from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# URL вашей БД
DATABASE_URL = "postgresql+psycopg2://postgres:dbDTProject05@localhost:5432/ai_bot_db"

# Создание движка
engine = create_engine(DATABASE_URL, echo=True, future=True)

# Конфигурация сессии
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Базовый класс для всех моделей
Base = declarative_base()

# Проверка соединения
if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            # Обязательно обёрнуто в text()
            result = connection.execute(text("SELECT version();"))
            print("✅ Успешное подключение к PostgreSQL:")
            for row in result:
                print(row)
    except Exception as e:
        print("❌ Ошибка подключения к базе данных:", e)
