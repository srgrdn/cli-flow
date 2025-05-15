from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Question, Answer
from schemas import QuestionCreate, QuestionResponse
from routers.auth import get_current_user


router = APIRouter(
    prefix="/questions",
    tags=["questions"],
    responses={404: {"description": "Не найдено"}},
)

templates = Jinja2Templates(directory="templates")


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
async def test_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Страница с тестом (требует авторизации)"""
    questions = db.query(Question).all()
    return templates.TemplateResponse(
        "test.html", 
        {"request": request, "questions": questions, "title": "Теоретический тест RHCSA"}
    )


@router.get("/{question_id}", response_model=QuestionResponse)
async def read_question(question_id: int, db: Session = Depends(get_db)):
    """Получение конкретного вопроса по ID"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    return question
