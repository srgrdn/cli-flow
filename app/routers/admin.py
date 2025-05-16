from fastapi import APIRouter, Depends, HTTPException, Request, Security, Form, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import User, Question, Answer, UserAnswer
from routers.auth import AuthService
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Не найдено"}},
)

templates = Jinja2Templates(directory="templates")
security = HTTPBearer(auto_error=False)


# Проверка, что пользователь является администратором
async def check_admin_access(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    token: Optional[str] = None
):
    """Проверка прав администратора"""
    auth_token = None
    if credentials:
        auth_token = credentials.credentials
    elif token:
        auth_token = token

    if not auth_token:
        raise HTTPException(
            status_code=403,
            detail="Не авторизован. Токен не найден."
        )

    try:
        # Верификация токена
        payload = AuthService.decode_access_token(auth_token)
        if payload is None or "sub" not in payload:
            raise HTTPException(
                status_code=403,
                detail="Недействительный токен авторизации."
            )

        # Проверка пользователя
        user = db.query(User).filter(User.email == payload["sub"]).first()
        if user is None:
            raise HTTPException(
                status_code=403,
                detail="Пользователь не найден."
            )

        # Проверка прав администратора
        if not user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав для доступа к административной панели."
            )

        return user

    except Exception as e:
        raise HTTPException(
            status_code=403,
            detail=f"Ошибка авторизации: {str(e)}"
        )


# Главная страница админки
@router.get("/", response_model=None)
async def admin_dashboard(
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Административная панель"""
    # Получаем статистику
    users_count = db.query(User).count()
    questions_count = db.query(Question).count()

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "title": "Админ-панель",
            "admin": admin,
            "users_count": users_count,
            "questions_count": questions_count,
            "now": datetime.now(),
            "token": token
        }
    )


# Управление пользователями
@router.get("/users", response_model=None)
async def admin_users(
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Список пользователей"""
    users = db.query(User).all()

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "title": "Управление пользователями",
            "admin": admin,
            "users": users,
            "token": token
        }
    )


# Редактирование пользователя
@router.post("/users/{user_id}", response_model=None)
async def admin_edit_user(
    user_id: int,
    request: Request,
    is_active: str = Form(...),
    is_superuser: str = Form(...),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Редактирование пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Convert string values to boolean
    user.is_active = is_active.lower() == "true"
    user.is_superuser = is_superuser.lower() == "true"
    db.commit()

    # Перенаправляем на страницу со списком пользователей, добавляя токен
    redirect_url = "/admin/users"
    if token:
        redirect_url += f"?token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Управление вопросами
@router.get("/questions", response_model=None)
async def admin_questions(
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Список вопросов"""
    questions = db.query(Question).all()

    return templates.TemplateResponse(
        "admin/questions.html",
        {
            "request": request,
            "title": "Управление вопросами",
            "admin": admin,
            "questions": questions,
            "token": token
        }
    )


# Форма добавления вопроса
@router.get("/questions/add", response_model=None)
async def admin_add_question_form(
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access)
):
    """Форма добавления вопроса"""
    return templates.TemplateResponse(
        "admin/question_form.html",
        {
            "request": request,
            "title": "Добавление вопроса",
            "admin": admin,
            "token": token
        }
    )


# Добавление вопроса
@router.post("/questions/add", response_model=None)
async def admin_add_question(
    text: str = Form(...),
    difficulty: str = Form(...),
    category: str = Form(...),
    answers_text: List[str] = Form(...),
    is_correct: List[bool] = Form(...),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Добавление вопроса"""
    # Создаем вопрос
    question = Question(
        text=text,
        difficulty=difficulty,
        category=category
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    # Добавляем варианты ответов
    for i in range(len(answers_text)):
        answer = Answer(
            text=answers_text[i],
            is_correct=i in is_correct,
            question_id=question.id
        )
        db.add(answer)

    db.commit()

    # Перенаправляем на страницу со списком вопросов, добавляя токен
    redirect_url = "/admin/questions"
    if token:
        redirect_url += f"?token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Удаление вопроса
@router.get("/questions/{question_id}/delete", response_model=None)
async def admin_delete_question(
    question_id: int,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Удаление вопроса"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if question:
        # Сначала удаляем записи в user_answers, связанные с ответами на этот вопрос
        answers = db.query(Answer).filter(Answer.question_id == question_id).all()
        answer_ids = [answer.id for answer in answers]
        
        if answer_ids:
            db.query(UserAnswer).filter(UserAnswer.answer_id.in_(answer_ids)).delete(synchronize_session=False)
            db.commit()
        
        # Теперь можем удалить сам вопрос (и связанные ответы через каскад)
        db.delete(question)
        db.commit()

    # Перенаправляем на страницу со списком вопросов, добавляя токен
    redirect_url = "/admin/questions"
    if token:
        redirect_url += f"?token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)
