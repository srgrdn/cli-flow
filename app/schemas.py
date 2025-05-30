from datetime import datetime
from typing import Any, Dict, List, Optional

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
    exam_type: str = "rhcsa"


class QuestionCreate(QuestionBase):
    """Схема для создания вопроса"""
    answers: List[AnswerCreate]


class QuestionResponse(QuestionBase):
    """Схема для ответа с вопросом"""
    id: int
    answers: List[Answer]

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    """Базовая схема пользователя"""
    email: str


class UserCreate(UserBase):
    """Схема для регистрации пользователя"""
    password: str


class User(UserBase):
    """Схема пользователя из БД"""
    id: int

    class Config:
        orm_mode = True


class Token(BaseModel):
    """Схема для JWT токена"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Данные в токене"""
    email: Optional[str] = None


class TestSubmit(BaseModel):
    """Схема для отправки ответов на тест"""
    answers: Dict[int, int]  # question_id: answer_id


class UserAnswerResponse(BaseModel):
    """Схема для ответа пользователя на вопрос"""
    question_id: int
    answer_id: int
    is_correct: bool

    class Config:
        orm_mode = True


class TestAttemptBase(BaseModel):
    """Базовая схема для попытки прохождения теста"""
    start_time: datetime
    end_time: Optional[datetime] = None
    score: int
    max_score: int


class TestAttemptCreate(BaseModel):
    """Схема для создания попытки прохождения теста"""
    user_id: int


class TestAttemptResponse(TestAttemptBase):
    """Схема для ответа с результатами теста"""
    id: int
    user_id: int
    user_answers: List[UserAnswerResponse] = []

    class Config:
        orm_mode = True


class TestResult(BaseModel):
    """Схема для результатов теста"""
    score: int
    max_score: int
    percentage: float
    correct_answers: int
    total_questions: int
    details: List[Dict[str, Any]]


# Схемы для теоретических материалов

class TheoryResourceBase(BaseModel):
    """Базовая схема для ресурса теории"""
    title: str
    url: str
    resource_type: str = "link"


class TheoryResourceCreate(TheoryResourceBase):
    """Схема для создания ресурса теории"""
    pass


class TheoryResource(TheoryResourceBase):
    """Схема для ресурса теории из БД"""
    id: int
    topic_id: int

    class Config:
        orm_mode = True


class TheoryContentBase(BaseModel):
    """Базовая схема для содержимого теории"""
    content: str


class TheoryContentCreate(TheoryContentBase):
    """Схема для создания содержимого теории"""
    pass


class TheoryContent(TheoryContentBase):
    """Схема для содержимого теории из БД"""
    id: int
    topic_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TheoryTopicBase(BaseModel):
    """Базовая схема для темы теории"""
    title: str
    description: Optional[str] = None
    exam_type: str = "rhcsa"
    order: int = 0


class TheoryTopicCreate(TheoryTopicBase):
    """Схема для создания темы теории"""
    parent_id: Optional[int] = None


class TheoryTopicUpdate(BaseModel):
    """Схема для обновления темы теории"""
    title: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    exam_type: Optional[str] = None
    order: Optional[int] = None


class TheoryTopicResponse(TheoryTopicBase):
    """Схема для ответа с темой теории"""
    id: int
    parent_id: Optional[int] = None
    
    class Config:
        orm_mode = True


class TheoryTopicDetail(TheoryTopicResponse):
    """Детальная схема для темы теории с содержимым и ресурсами"""
    content: Optional[TheoryContent] = None
    resources: List[TheoryResource] = []
    children: List['TheoryTopicResponse'] = []
    questions: List[QuestionResponse] = []

    class Config:
        orm_mode = True


# Для поддержки рекурсивных ссылок
TheoryTopicDetail.update_forward_refs()
