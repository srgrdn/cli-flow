from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Question(Base):
    """Модель для вопросов теоретического тестирования"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    difficulty = Column(String, default="medium")  # easy, medium, hard
    category = Column(String, nullable=False)  # категория вопроса
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class User(Base):
    """Модель пользователя системы"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    test_attempts = relationship("TestAttempt", back_populates="user")


class Answer(Base):
    """Модель для вариантов ответов"""
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    question_id = Column(Integer, ForeignKey("questions.id"))

    # Связь с вопросом
    question = relationship("Question", back_populates="answers")


class TestAttempt(Base):
    """Модель для попыток прохождения теста"""
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)

    # Связь с пользователем
    user = relationship("User", back_populates="test_attempts")
    # Связь с ответами на вопросы
    user_answers = relationship("UserAnswer", back_populates="test_attempt", cascade="all, delete-orphan")


class UserAnswer(Base):
    """Модель для ответов пользователя на вопросы"""
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    test_attempt_id = Column(Integer, ForeignKey("test_attempts.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    answer_id = Column(Integer, ForeignKey("answers.id"))
    is_correct = Column(Boolean, default=False)

    # Связи
    test_attempt = relationship("TestAttempt", back_populates="user_answers")
    question = relationship("Question")
    answer = relationship("Answer")
