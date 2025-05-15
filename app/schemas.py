from typing import List, Optional
from pydantic import BaseModel


class AnswerBase(BaseModel):
    """Базовая схема для ответа"""
    text: str
    is_correct: bool


class AnswerCreate(AnswerBase):
    """Схема для создания ответа"""
    pass


class Answer(AnswerBase):
    """Схема для ответа из БД"""
    id: int
    question_id: int

    class Config:
        orm_mode = True


class QuestionBase(BaseModel):
    """Базовая схема для вопроса"""
    text: str
    difficulty: str
    category: str


class QuestionCreate(QuestionBase):
    """Схема для создания вопроса"""
    answers: List[AnswerCreate]


class QuestionResponse(QuestionBase):
    """Схема для ответа с вопросом"""
    id: int
    answers: List[Answer]

    class Config:
        orm_mode = True
