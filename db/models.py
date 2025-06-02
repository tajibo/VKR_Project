# db/models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Float,
    func,
)
from sqlalchemy.orm import relationship

from db.database import Base

class Role(Base):
    __tablename__ = "roles"
    id   = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    telegram_id   = Column(Integer, unique=True, nullable=True)  # можно null, если регистрируются не через Telegram
    username      = Column(String(255), unique=True, nullable=False)  # Логин (email или псевдоним)
    password_hash = Column(String(255), nullable=False)  # Хэш пароля
    role_id       = Column(Integer, ForeignKey("roles.id"), nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    role     = relationship("Role", back_populates="users")
    settings = relationship("UserSetting", back_populates="user", uselist=False)
    pomodoros = relationship("PomodoroSession", back_populates="user")
    flashcards = relationship("Flashcard", back_populates="user")
    reflections = relationship("Reflection", back_populates="user")
    logs       = relationship("Log", back_populates="user")
    summaries  = relationship("Summary", back_populates="user")
    deadlines  = relationship("Deadline", back_populates="user")
    files      = relationship("File", back_populates="user")
    activity     = relationship("UserActivity", back_populates="user")
    error_logs   = relationship("ErrorLog", back_populates="user")
    feedbacks    = relationship("UserFeedback", back_populates="user")


class UserActivity(Base):
    __tablename__ = "user_activity"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # стала nullable=True
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    query_text = Column(Text, nullable=True)
    intent_label = Column(String(100), nullable=True)
    handler_name = Column(String(100), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    user = relationship("User", back_populates="activity")

class UserSetting(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    pomodoro_duration = Column(Integer, default=25)
    break_duration = Column(Integer, default=5)
    notifications_enabled = Column(Boolean, default=True)

    preferred_language = Column(String(2), default="ru", nullable=False)
    default_summary_length = Column(Integer, default=3, nullable=False)
    deadline_notifications = Column(Boolean, default=True, nullable=False)
    flashcard_notifications = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="settings")

class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False)

    user = relationship("User", back_populates="pomodoros")

class Flashcard(Base):
    __tablename__ = "flashcards"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="flashcards")
    reviews = relationship("FlashcardReview", back_populates="card")

class FlashcardReview(Base):
    __tablename__ = "flashcard_reviews"
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    review_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    success = Column(Boolean, nullable=False)

    card = relationship("Flashcard", back_populates="reviews")

class Reflection(Base):
    __tablename__ = "reflections"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="reflections")

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="logs")

class Summary(Base):
    __tablename__ = "summaries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    input_text = Column(Text, nullable=False)
    summary_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="summaries")

class Deadline(Base):
    __tablename__ = "deadlines"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_name = Column(String(255))
    deadline_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="deadlines")

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="files")

class ModelMetrics(Base):
    __tablename__ = "model_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    metric_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accuracy = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

class ErrorLog(Base):
    __tablename__ = "error_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    handler_name = Column(String(100), nullable=True)
    error_text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="error_logs")

class UserFeedback(Base):
    __tablename__ = "user_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query_text = Column(Text, nullable=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="feedbacks")
