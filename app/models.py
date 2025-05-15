from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Question(Base):
    """Модель для вопросов теоретического тестирования"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    difficulty = Column(String, default="medium")  # easy, medium, hard
    category = Column(String, nullable=False)  # категория вопроса (например, 'файловые системы', 'пользователи')

    # Связь с ответами
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    """Модель для вариантов ответов"""
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    question_id = Column(Integer, ForeignKey("questions.id"))

    # Связь с вопросом
    question = relationship("Question", back_populates="answers")
