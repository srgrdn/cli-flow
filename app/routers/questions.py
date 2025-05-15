from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Question, Answer, User
from schemas import QuestionCreate, QuestionResponse
from routers.auth import AuthService
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter(
    prefix="/questions",
    tags=["questions"],
    responses={404: {"description": "Не найдено"}},
)

templates = Jinja2Templates(directory="templates")
security = HTTPBearer(auto_error=False)


@router.post("/", response_model=QuestionResponse)
async def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    """Создание нового вопроса с вариантами ответов"""
    db_question = Question(
        text=question.text,
        difficulty=question.difficulty,
        category=question.category
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    # Добавляем варианты ответов
    for answer in question.answers:
        db_answer = Answer(
            text=answer.text,
            is_correct=answer.is_correct,
            question_id=db_question.id
        )
        db.add(db_answer)

    db.commit()
    db.refresh(db_question)
    return db_question


@router.get("/", response_model=List[QuestionResponse])
async def read_questions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получение списка вопросов"""
    questions = db.query(Question).offset(skip).limit(limit).all()
    return questions


@router.get("/test", response_model=None)
async def test_page(
    request: Request, 
    db: Session = Depends(get_db), 
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    token: Optional[str] = None
):
    """Страница с тестом (требует авторизации)"""
    
    # Проверяем токен из заголовка Authorization или из query параметра
    auth_token = None
    if credentials:
        auth_token = credentials.credentials
    elif token:
        auth_token = token
    
    if not auth_token:
        raise HTTPException(
            status_code=403, 
            detail="Не авторизован. Токен не найден. Пожалуйста, войдите в систему."
        )
    
    try:
        # Верификация токена
        payload = AuthService.decode_access_token(auth_token)
        if payload is None or "sub" not in payload:
            raise HTTPException(
                status_code=403, 
                detail="Недействительный токен авторизации. Пожалуйста, войдите в систему снова."
            )
        
        # Проверка пользователя
        user = db.query(User).filter(User.email == payload["sub"]).first()
        if user is None:
            raise HTTPException(
                status_code=403, 
                detail="Пользователь не найден. Возможно, учетная запись была удалена."
            )
        
        # Получаем вопросы
        questions = db.query(Question).all()
        return templates.TemplateResponse(
            "test.html", 
            {"request": request, "questions": questions, "title": "Теоретический тест RHCSA"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=403,
            detail=f"Ошибка авторизации: {str(e)}"
        )


@router.get("/{question_id}", response_model=QuestionResponse)
async def read_question(question_id: int, db: Session = Depends(get_db)):
    """Получение конкретного вопроса по ID"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    return question 