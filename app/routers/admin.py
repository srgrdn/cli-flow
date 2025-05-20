import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Security
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Answer, Question, TestAttempt, User, UserAnswer
from routers.auth import AuthService

# Setup logger
logger = logging.getLogger("admin")

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
        logger.warning(f"Admin access attempt without token from IP: {request.client.host}")
        raise HTTPException(
            status_code=403,
            detail="Не авторизован. Токен не найден."
        )

    try:
        # Верификация токена
        payload = AuthService.decode_access_token(auth_token)
        if payload is None or "sub" not in payload:
            logger.warning(f"Admin access attempt with invalid token from IP: {request.client.host}")
            raise HTTPException(
                status_code=403,
                detail="Недействительный токен авторизации."
            )

        # Проверка пользователя
        user = db.query(User).filter(User.email == payload["sub"]).first()
        if user is None:
            logger.warning(f"Admin access attempt with non-existent user: {payload.get('sub', 'unknown')} from IP: {request.client.host}")
            raise HTTPException(
                status_code=403,
                detail="Пользователь не найден."
            )

        # Проверка прав администратора
        if not user.is_superuser:
            logger.warning(f"Admin access attempt by non-admin user: {user.email} from IP: {request.client.host}")
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав для доступа к административной панели."
            )

        logger.info(f"Admin access granted to: {user.email} from IP: {request.client.host}")
        return user

    except Exception as e:
        logger.error(f"Admin access error: {str(e)} from IP: {request.client.host}")
        raise HTTPException(
            status_code=403,
            detail=f"Ошибка авторизации: {str(e)}"
        ) from e


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

    logger.info(f"Admin dashboard accessed by: {admin.email}")
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

    logger.info(f"User management accessed by admin: {admin.email}")
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
        logger.warning(f"Admin {admin.email} attempted to edit non-existent user ID: {user_id}")
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Convert string values to boolean
    old_is_active = user.is_active
    old_is_superuser = user.is_superuser

    user.is_active = is_active.lower() == "true"
    user.is_superuser = is_superuser.lower() == "true"
    db.commit()

    logger.info(
        f"User {user.email} (ID: {user_id}) updated by admin {admin.email}: "
        f"is_active: {old_is_active} -> {user.is_active}, "
        f"is_superuser: {old_is_superuser} -> {user.is_superuser}"
    )

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
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Список вопросов с возможностью фильтрации"""
    # Базовый запрос
    query = db.query(Question)

    # Применяем фильтры, если они указаны
    if category:
        query = query.filter(Question.category == category)

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    questions = query.all()

    # Получаем все уникальные категории для фильтра
    categories = db.query(Question.category).distinct().all()
    categories = [cat[0] for cat in categories]

    # Получаем все уникальные уровни сложности для фильтра
    difficulties = ["easy", "medium", "hard"]

    logger.info(f"Question management accessed by admin: {admin.email}")
    return templates.TemplateResponse(
        "admin/questions.html",
        {
            "request": request,
            "title": "Управление вопросами",
            "admin": admin,
            "questions": questions,
            "categories": categories,
            "difficulties": difficulties,
            "selected_category": category,
            "selected_difficulty": difficulty,
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
    logger.info(f"Question add form accessed by admin: {admin.email}")
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

    logger.info(
        f"New question added by admin {admin.email}: "
        f"ID: {question.id}, Category: {category}, Difficulty: {difficulty}"
    )

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
        logger.info(f"Question ID: {question_id} deleted by admin: {admin.email}")
        # Удаляем связанные ответы
        db.query(Answer).filter(Answer.question_id == question_id).delete()
        # Удаляем связанные ответы пользователей
        db.query(UserAnswer).filter(UserAnswer.question_id == question_id).delete()
        # Удаляем сам вопрос
        db.delete(question)
        db.commit()
    else:
        logger.warning(f"Admin {admin.email} attempted to delete non-existent question ID: {question_id}")

    # Перенаправляем на страницу со списком вопросов, добавляя токен
    redirect_url = "/admin/questions"
    if token:
        redirect_url += f"?token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Форма редактирования вопроса
@router.get("/questions/{question_id}/edit", response_model=None)
async def admin_edit_question_form(
    question_id: int,
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Форма редактирования вопроса"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    answers = db.query(Answer).filter(Answer.question_id == question_id).all()

    return templates.TemplateResponse(
        "admin/question_form.html",
        {
            "request": request,
            "title": "Редактирование вопроса",
            "admin": admin,
            "token": token,
            "question": question,
            "answers": answers,
            "edit_mode": True
        }
    )


# Обновление вопроса
@router.post("/questions/{question_id}/edit", response_model=None)
async def admin_update_question(
    question_id: int,
    text: str = Form(...),
    difficulty: str = Form(...),
    category: str = Form(...),
    answers_text: List[str] = Form(...),
    is_correct: List[str] = Form(...),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Обновление вопроса"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    # Обновляем данные вопроса
    question.text = text
    question.difficulty = difficulty
    question.category = category
    db.commit()

    # Удаляем старые ответы
    old_answers = db.query(Answer).filter(Answer.question_id == question_id).all()
    answer_ids = [answer.id for answer in old_answers]

    if answer_ids:
        # Удаляем связанные user_answers
        db.query(UserAnswer).filter(UserAnswer.answer_id.in_(answer_ids)).delete(synchronize_session=False)
        db.commit()

        # Удаляем старые ответы
        db.query(Answer).filter(Answer.question_id == question_id).delete(synchronize_session=False)
        db.commit()

    # Добавляем новые ответы
    is_correct_indices = [int(idx) for idx in is_correct]
    for i in range(len(answers_text)):
        answer = Answer(
            text=answers_text[i],
            is_correct=i in is_correct_indices,
            question_id=question.id
        )
        db.add(answer)

    db.commit()

    # Перенаправляем на страницу со списком вопросов, добавляя токен
    redirect_url = "/admin/questions"
    if token:
        redirect_url += f"?token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Просмотр истории тестирования пользователя
@router.get("/users/{user_id}/history", response_model=None)
async def admin_user_test_history(
    user_id: int,
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """История тестирования пользователя"""
    # Проверяем существование пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Admin {admin.email} attempted to view history of non-existent user ID: {user_id}")
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Получаем историю тестирования пользователя
    test_attempts = db.query(TestAttempt).filter(
        TestAttempt.user_id == user_id
    ).order_by(TestAttempt.start_time.desc()).all()

    logger.info(f"Admin {admin.email} viewed test history of user {user.email} (ID: {user_id})")

    return templates.TemplateResponse(
        "admin/user_test_history.html",
        {
            "request": request,
            "title": f"История тестирования пользователя {user.email}",
            "admin": admin,
            "user": user,
            "test_attempts": test_attempts,
            "token": token
        }
    )


# Просмотр деталей попытки тестирования
@router.get("/test_attempts/{attempt_id}", response_model=None)
async def admin_test_attempt_details(
    attempt_id: int,
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Подробности попытки тестирования"""
    # Получаем попытку тестирования
    test_attempt = db.query(TestAttempt).filter(TestAttempt.id == attempt_id).first()
    if not test_attempt:
        logger.warning(f"Admin {admin.email} attempted to view non-existent test attempt ID: {attempt_id}")
        raise HTTPException(status_code=404, detail="Попытка тестирования не найдена")

    # Получаем пользователя
    user = db.query(User).filter(User.id == test_attempt.user_id).first()

    # Получаем ответы пользователя с деталями вопросов
    user_answers = db.query(UserAnswer).filter(
        UserAnswer.test_attempt_id == attempt_id
    ).all()

    logger.info(f"Admin {admin.email} viewed test attempt details (ID: {attempt_id}) of user {user.email}")

    return templates.TemplateResponse(
        "admin/test_attempt_details.html",
        {
            "request": request,
            "title": f"Детали попытки тестирования #{attempt_id}",
            "admin": admin,
            "user": user,
            "test_attempt": test_attempt,
            "user_answers": user_answers,
            "token": token
        }
    )
