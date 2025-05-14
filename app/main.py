import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.predict import router as predict_router
from app.routers.user import router as user_router

# Добавляем корень проекта в sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Создаём таблицы в БД
Base.metadata.create_all(bind=engine)

# Инициализация FastAPI приложения
app = FastAPI()

# Подключаем роутеры
app.include_router(user_router)
app.include_router(predict_router)

# Добавление CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ubiquitous-space-carnival-5ggxqqqpv57v3vvj6-3000.app.github.dev",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root() -> dict[str, str]:
    """Корневой эндпоинт возвращает приветственное сообщение."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def read_root():

    return {"message": "Hello, World!"}
