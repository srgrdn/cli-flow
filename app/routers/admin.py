import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Security
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import (
    Answer,
    Question,
    QuestionCategory,
    TestAttempt,
    TheoryContent,
    TheoryResource,
    TheoryTopic,
    User,
    UserAnswer,
)
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


# Вспомогательная функция для получения типов экзаменов
def get_exam_types(db: Session):
    """Получает список уникальных типов экзаменов из базы данных"""
    exam_types = db.query(QuestionCategory.exam_type).distinct().all()
    exam_types = [et[0] for et in exam_types]

    # Если нет типов экзаменов из категорий, берем их из вопросов
    if not exam_types:
        exam_types = db.query(Question.exam_type).distinct().all()
        exam_types = [et[0] for et in exam_types]

    return exam_types


# Проверка, что пользователь является администратором
async def check_admin_access(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    token: Optional[str] = Query(None)
):
    """Проверка прав администратора"""
    auth_token = None

    # Приоритет 1: Проверяем куки
    auth_token = request.cookies.get("access_token")

    # Приоритет 2: Проверяем заголовок Authorization
    if not auth_token and credentials:
        auth_token = credentials.credentials

    # Приоритет 3: Проверяем параметр URL (для обратной совместимости)
    if not auth_token and token:
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
        if not user:
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
    topics_count = db.query(TheoryTopic).count()

    logger.info(f"Admin dashboard accessed by: {admin.email}")
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "title": "Админ-панель",
            "admin": admin,
            "users_count": users_count,
            "questions_count": questions_count,
            "topics_count": topics_count,
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
    exam_type: Optional[str] = Query(None),
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
    if exam_type:
        query = query.filter(Question.exam_type == exam_type)

    # Получаем отфильтрованные вопросы
    questions = query.all()

    # Получаем все уникальные категории из базы данных
    categories = db.query(Question.category).distinct().all()
    categories = [cat[0] for cat in categories]

    # Получаем все уникальные уровни сложности
    difficulties = db.query(Question.difficulty).distinct().all()
    difficulties = [diff[0] for diff in difficulties]

    # Получаем все уникальные типы экзаменов
    exam_types = db.query(Question.exam_type).distinct().all()
    exam_types = [et[0] for et in exam_types]

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
            "exam_types": exam_types,
            "selected_category": category,
            "selected_difficulty": difficulty,
            "selected_exam_type": exam_type,
            "token": token
        }
    )


# Форма добавления вопроса
@router.get("/questions/add", response_model=None)
async def admin_add_question_form(
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Форма добавления вопроса"""
    # Получаем все категории вопросов
    categories = db.query(QuestionCategory).order_by(QuestionCategory.name).all()

    logger.info(f"Question add form accessed by admin: {admin.email}")
    return templates.TemplateResponse(
        "admin/question_form.html",
        {
            "request": request,
            "title": "Добавление вопроса",
            "admin": admin,
            "token": token,
            "categories": categories
        }
    )


# Добавление вопроса
@router.post("/questions/add", response_model=None)
async def admin_add_question(
    request: Request,
    text: str = Form(...),
    difficulty: str = Form(...),
    category: str = Form(...),
    new_category: Optional[str] = Form(None),
    exam_type: str = Form(...),
    answers_text: List[str] = Form(...),
    is_correct: List[str] = Form(...),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Добавление вопроса"""
    # Определяем категорию
    category_name = new_category if category == "new_category" else category

    # Если это новая категория, добавляем её в базу данных
    category_id = None
    if category_name:
        existing_category = db.query(QuestionCategory).filter(
            QuestionCategory.name == category_name
        ).first()

        if existing_category:
            category_id = existing_category.id
        else:
            # Создаем новую категорию
            new_cat = QuestionCategory(
                name=category_name,
                exam_type=exam_type,
                description=f"Категория вопросов: {category_name}",
                created_at=datetime.utcnow()
            )
            db.add(new_cat)
            db.flush()  # Получаем ID без коммита
            category_id = new_cat.id
            logger.info(f"New category '{category_name}' created by admin: {admin.email}")

    # Создаем вопрос
    question = Question(
        text=text,
        difficulty=difficulty,
        category=category_name,
        category_id=category_id,
        exam_type=exam_type
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    # Добавляем варианты ответов
    is_correct_indices = [int(idx) for idx in is_correct]
    for i in range(len(answers_text)):
        answer = Answer(
            text=answers_text[i],
            is_correct=i in is_correct_indices,
            question_id=question.id
        )
        db.add(answer)

    db.commit()

    logger.info(
        f"New question added by admin {admin.email}: "
        f"ID: {question.id}, Category: {category_name}, Difficulty: {difficulty}, Exam type: {exam_type}"
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


# Массовое удаление вопросов
@router.post("/questions/batch-delete", response_model=None)
async def admin_batch_delete_questions(
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Массовое удаление вопросов"""
    try:
        # Получаем данные формы
        form = await request.form()

        # Преобразуем MultiDict формы в обычный dict для логирования
        form_data = dict(form)
        logger.info(f"Received form data keys: {list(form_data.keys())}")

        # Используем встроенный метод getlist для получения всех значений с одинаковым ключом
        question_ids_raw = form.getlist('question_ids')
        logger.info(f"Raw question_ids from form.getlist: {question_ids_raw}")

        # Преобразуем строковые ID в целочисленные
        question_ids = []
        for id_str in question_ids_raw:
            try:
                question_id = int(id_str)
                question_ids.append(question_id)
            except ValueError:
                logger.warning(f"Invalid question ID format: {id_str}")

        if question_ids:
            logger.info(f"Attempting to delete {len(question_ids)} questions: {question_ids}")

            try:
                # Удаляем связанные ответы пользователей
                user_answers_deleted = db.query(UserAnswer).filter(
                    UserAnswer.question_id.in_(question_ids)
                ).delete(synchronize_session=False)

                # Удаляем связанные ответы
                answers_deleted = db.query(Answer).filter(
                    Answer.question_id.in_(question_ids)
                ).delete(synchronize_session=False)

                # Удаляем сами вопросы
                deleted_count = db.query(Question).filter(
                    Question.id.in_(question_ids)
                ).delete(synchronize_session=False)

                db.commit()

                logger.info(
                    f"Batch deletion by admin: {admin.email}. "
                    f"Deleted {deleted_count} questions, {answers_deleted} answers, "
                    f"{user_answers_deleted} user answers. Question IDs: {question_ids}"
                )
            except Exception as e:
                db.rollback()
                logger.error(f"Error during batch deletion: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error during batch deletion: {str(e)}") from e
        else:
            logger.warning(f"Batch delete request without valid question IDs from admin: {admin.email}")

    except Exception as e:
        logger.error(f"Unexpected error in batch delete: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e

    # Перенаправляем на страницу со списком вопросов, сохраняя фильтры
    redirect_url = "/admin/questions"
    params = []

    if token:
        params.append(f"token={token}")

    # Сохраняем текущие фильтры
    for key, value in form.items():
        if key in ["category", "difficulty", "exam_type"] and value:
            params.append(f"{key}={value}")

    if params:
        redirect_url += "?" + "&".join(params)

    return RedirectResponse(url=redirect_url, status_code=303)


# Удаление категории вопросов
@router.post("/questions/delete-category", response_model=None)
async def admin_delete_category(
    request: Request,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Удаление всех вопросов определенной категории"""
    try:
        form = await request.form()
        form_data = dict(form)

        logger.info(f"Category deletion form data: {form_data}")

        category = form.get("category")
        exam_type = form.get("exam_type")

        if not category:
            logger.warning(f"Category deletion request without category from admin: {admin.email}")
            raise HTTPException(status_code=400, detail="Категория не указана")

        logger.info(f"Attempting to delete category '{category}' with exam_type filter: {exam_type}")

        try:
            # Строим базовый запрос
            query = db.query(Question).filter(Question.category == category)

            # Если указан тип экзамена, добавляем его в фильтр
            if exam_type:
                query = query.filter(Question.exam_type == exam_type)

            # Получаем ID вопросов для удаления
            questions = query.all()
            question_ids = [q.id for q in questions]

            logger.info(f"Found {len(question_ids)} questions in category '{category}' to delete")

            if question_ids:
                # Удаляем связанные ответы пользователей
                user_answers_deleted = db.query(UserAnswer).filter(
                    UserAnswer.question_id.in_(question_ids)
                ).delete(synchronize_session=False)

                # Удаляем связанные ответы
                answers_deleted = db.query(Answer).filter(
                    Answer.question_id.in_(question_ids)
                ).delete(synchronize_session=False)

                # Удаляем сами вопросы
                deleted_count = query.delete(synchronize_session=False)

                db.commit()

                logger.info(
                    f"Category '{category}' deletion by admin: {admin.email}. "
                    f"Deleted {deleted_count} questions, {answers_deleted} answers, "
                    f"{user_answers_deleted} user answers."
                )
            else:
                logger.info(f"No questions found in category '{category}' to delete")

        except Exception as e:
            db.rollback()
            logger.error(f"Error during category deletion: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error during category deletion: {str(e)}") from e

    except Exception as e:
        logger.error(f"Unexpected error in category deletion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e

    # Перенаправляем на страницу со списком вопросов, добавляя токен и сохраняя фильтры
    redirect_url = "/admin/questions"
    params = []

    if token:
        params.append(f"token={token}")

    if exam_type:
        params.append(f"exam_type={exam_type}")

    if params:
        redirect_url += "?" + "&".join(params)

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

    # Получаем все категории вопросов
    categories = db.query(QuestionCategory).order_by(QuestionCategory.name).all()

    return templates.TemplateResponse(
        "admin/question_form.html",
        {
            "request": request,
            "title": "Редактирование вопроса",
            "admin": admin,
            "token": token,
            "question": question,
            "answers": answers,
            "categories": categories,
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
    new_category: Optional[str] = Form(None),
    exam_type: str = Form(...),
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

    # Определяем категорию
    category_name = new_category if category == "new_category" else category

    # Если это новая категория, добавляем её в базу данных
    category_id = None
    if category_name:
        existing_category = db.query(QuestionCategory).filter(
            QuestionCategory.name == category_name
        ).first()

        if existing_category:
            category_id = existing_category.id
        else:
            # Создаем новую категорию
            new_cat = QuestionCategory(
                name=category_name,
                exam_type=exam_type,
                description=f"Категория вопросов: {category_name}",
                created_at=datetime.utcnow()
            )
            db.add(new_cat)
            db.flush()  # Получаем ID без коммита
            category_id = new_cat.id
            logger.info(f"New category '{category_name}' created by admin: {admin.email}")

    # Обновляем данные вопроса
    question.text = text
    question.difficulty = difficulty
    question.category = category_name
    question.category_id = category_id
    question.exam_type = exam_type
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

    logger.info(
        f"Question updated by admin {admin.email}: "
        f"ID: {question.id}, Category: {category_name}, Difficulty: {difficulty}, Exam type: {exam_type}"
    )

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


# Управление теоретическими материалами
@router.get("/theory", response_model=None)
async def admin_theory(
    request: Request,
    token: Optional[str] = Query(None),
    exam_type: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Список тем теоретических материалов"""
    # Базовый запрос для получения корневых тем
    query = db.query(TheoryTopic).filter(TheoryTopic.parent_id.is_(None))

    # Применяем фильтр по типу экзамена, если указан
    if exam_type:
        query = query.filter(TheoryTopic.exam_type == exam_type)

    # Получаем корневые темы
    root_topics = query.order_by(TheoryTopic.order).all()

    # Получаем все типы экзаменов для фильтра
    exam_types = db.query(TheoryTopic.exam_type).distinct().all()
    exam_types = [t[0] for t in exam_types if t[0]]

    # Если типов экзаменов из тем нет, берем их из вопросов
    if not exam_types:
        exam_types = db.query(Question.exam_type).distinct().all()
        exam_types = [t[0] for t in exam_types if t[0]]

    logger.info(f"Theory management accessed by admin: {admin.email}")
    return templates.TemplateResponse(
        "admin/theory.html",
        {
            "request": request,
            "title": "Управление теоретическими материалами",
            "admin": admin,
            "topics": root_topics,
            "current_exam_type": exam_type,
            "exam_types": exam_types,
            "token": token
        }
    )


# Добавление новой темы
@router.get("/theory/add", response_model=None)
async def admin_add_topic_form(
    request: Request,
    token: Optional[str] = Query(None),
    parent_id: Optional[int] = Query(None),
    exam_type: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Форма для добавления новой темы"""
    # Получаем все темы для выбора родительской
    topics = db.query(TheoryTopic).order_by(TheoryTopic.exam_type, TheoryTopic.title).all()

    # Получаем родительскую тему, если указана
    parent_topic = None
    if parent_id:
        parent_topic = db.query(TheoryTopic).filter(TheoryTopic.id == parent_id).first()

    # Получаем все типы экзаменов из вопросов
    exam_types = db.query(Question.exam_type).distinct().all()
    exam_types = [t[0] for t in exam_types if t[0]]

    # Если нет типов экзаменов из вопросов, используем стандартные
    if not exam_types:
        exam_types = ["rhcsa", "cka"]

    logger.info(f"Topic add form accessed by admin: {admin.email}")
    return templates.TemplateResponse(
        "admin/theory_add.html",
        {
            "request": request,
            "title": "Добавление новой темы",
            "admin": admin,
            "topics": topics,
            "parent_topic": parent_topic,
            "exam_types": exam_types,
            "default_exam_type": exam_type or "rhcsa",
            "token": token
        }
    )


# Добавление новой темы (обработка формы)
@router.post("/theory/add", response_model=None)
async def admin_add_topic(
    title: str = Form(...),
    description: str = Form(None),
    parent_id: Optional[int] = Form(None),
    exam_type: str = Form(...),
    order: int = Form(0),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Добавление новой темы"""
    # Проверяем существование родительской темы, если указана
    if parent_id:
        parent_topic = db.query(TheoryTopic).filter(TheoryTopic.id == parent_id).first()
        if not parent_topic:
            logger.warning(f"Admin {admin.email} attempted to add topic with non-existent parent ID: {parent_id}")
            raise HTTPException(status_code=404, detail="Родительская тема не найдена")

    # Создаем новую тему
    new_topic = TheoryTopic(
        title=title,
        description=description if description else None,
        parent_id=parent_id if parent_id else None,
        exam_type=exam_type,
        order=order
    )
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)

    logger.info(f"Topic '{title}' (ID: {new_topic.id}) added by admin: {admin.email}")

    # Перенаправляем на страницу просмотра темы
    redirect_url = f"/admin/theory/{new_topic.id}"
    if token:
        redirect_url += f"?token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Просмотр и редактирование темы
@router.get("/theory/{topic_id}", response_model=None)
async def admin_view_topic(
    topic_id: int,
    request: Request,
    token: Optional[str] = Query(None),
    tab: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Просмотр и редактирование темы"""
    # Загружаем тему со всеми связанными данными
    topic = db.query(TheoryTopic).options(
        joinedload(TheoryTopic.content),
        joinedload(TheoryTopic.resources),
        joinedload(TheoryTopic.children),
        joinedload(TheoryTopic.questions),
        joinedload(TheoryTopic.parent)
    ).filter(TheoryTopic.id == topic_id).first()

    if not topic:
        logger.warning(f"Admin {admin.email} attempted to view non-existent topic ID: {topic_id}")
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Получаем все темы для выбора родительской
    topics = db.query(TheoryTopic).filter(TheoryTopic.id != topic_id).order_by(TheoryTopic.exam_type, TheoryTopic.title).all()

    # Получаем все вопросы для типа экзамена текущей темы
    questions = db.query(Question).filter(Question.exam_type == topic.exam_type).all()

    # Получаем типы экзаменов из вопросов
    exam_types = db.query(Question.exam_type).distinct().all()
    exam_types = [t[0] for t in exam_types if t[0]]

    # Если нет типов экзаменов из вопросов, используем стандартные
    if not exam_types:
        exam_types = ["rhcsa", "cka"]

    logger.info(f"Topic '{topic.title}' (ID: {topic_id}) viewed by admin: {admin.email}")
    return templates.TemplateResponse(
        "admin/theory_edit.html",
        {
            "request": request,
            "title": f"Редактирование темы: {topic.title}",
            "admin": admin,
            "topic": topic,
            "topics": topics,
            "questions": questions,
            "exam_types": exam_types,
            "token": token,
            "active_tab": tab if tab else "info"
        }
    )


# Обновление основной информации о теме
@router.post("/theory/{topic_id}/update", response_model=None)
async def admin_update_topic(
    topic_id: int,
    title: str = Form(...),
    description: str = Form(None),
    parent_id: Optional[str] = Form(None),
    exam_type: str = Form(...),
    order: int = Form(0),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Обновление основной информации о теме"""
    # Получаем тему
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        logger.warning(f"Admin {admin.email} attempted to update non-existent topic ID: {topic_id}")
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Проверяем на циклические зависимости при выборе родителя
    new_parent_id = None if parent_id == "0" else int(parent_id) if parent_id else None

    if new_parent_id and new_parent_id == topic_id:
        logger.warning(f"Admin {admin.email} attempted to set topic as its own parent, topic ID: {topic_id}")
        raise HTTPException(status_code=400, detail="Тема не может быть родительской для самой себя")

    # Проверяем, не создаст ли новый родитель циклическую зависимость
    if new_parent_id:
        current_parent = db.query(TheoryTopic).filter(TheoryTopic.id == new_parent_id).first()
        if not current_parent:
            logger.warning(f"Admin {admin.email} attempted to set non-existent parent ID: {new_parent_id}")
            raise HTTPException(status_code=404, detail="Родительская тема не найдена")

        # Проверяем, нет ли циклической зависимости
        while current_parent:
            if current_parent.id == topic_id:
                logger.warning(f"Admin {admin.email} attempted to create circular dependency in topic hierarchy")
                raise HTTPException(
                    status_code=400,
                    detail="Невозможно создать циклическую зависимость в иерархии тем"
                )
            current_parent = db.query(TheoryTopic).filter(
                TheoryTopic.id == current_parent.parent_id
            ).first()

    # Обновляем тему
    topic.title = title
    topic.description = description if description else None
    topic.parent_id = new_parent_id
    topic.exam_type = exam_type
    topic.order = order

    db.commit()
    db.refresh(topic)

    logger.info(f"Topic '{title}' (ID: {topic_id}) updated by admin: {admin.email}")

    # Перенаправляем на страницу просмотра темы с активной вкладкой основной информации
    redirect_url = f"/admin/theory/{topic_id}?tab=info"
    if token:
        redirect_url += f"&token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Обновление содержимого темы
@router.post("/theory/{topic_id}/content", response_model=None)
async def admin_update_topic_content(
    topic_id: int,
    content: str = Form(...),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Обновление содержимого темы"""
    # Получаем тему
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        logger.warning(f"Admin {admin.email} attempted to update content for non-existent topic ID: {topic_id}")
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Проверяем, существует ли уже содержимое для этой темы
    existing_content = db.query(TheoryContent).filter(TheoryContent.topic_id == topic_id).first()

    if existing_content:
        # Обновляем существующее содержимое
        existing_content.content = content
        existing_content.updated_at = datetime.utcnow()
    else:
        # Создаем новое содержимое
        new_content = TheoryContent(
            topic_id=topic_id,
            content=content
        )
        db.add(new_content)

    db.commit()
    # Обновляем тему, чтобы обновить связанные данные
    db.refresh(topic)

    logger.info(f"Content for topic ID: {topic_id} updated by admin: {admin.email}")

    # Перенаправляем на страницу просмотра темы с активной вкладкой содержимого
    redirect_url = f"/admin/theory/{topic_id}?tab=content"
    if token:
        redirect_url += f"&token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Добавление ресурса к теме
@router.post("/theory/{topic_id}/resources/add", response_model=None)
async def admin_add_resource(
    topic_id: int,
    title: str = Form(...),
    url: str = Form(...),
    resource_type: str = Form("link"),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Добавление ресурса к теме"""
    # Получаем тему
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        logger.warning(f"Admin {admin.email} attempted to add resource to non-existent topic ID: {topic_id}")
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Создаем новый ресурс
    new_resource = TheoryResource(
        topic_id=topic_id,
        title=title,
        url=url,
        resource_type=resource_type
    )
    db.add(new_resource)
    db.commit()

    logger.info(f"Resource '{title}' added to topic ID: {topic_id} by admin: {admin.email}")

    # Перенаправляем на страницу просмотра темы с активной вкладкой ресурсов
    redirect_url = f"/admin/theory/{topic_id}?tab=resources"
    if token:
        redirect_url += f"&token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Удаление ресурса
@router.get("/theory/resources/{resource_id}/delete", response_model=None)
async def admin_delete_resource(
    resource_id: int,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Удаление ресурса"""
    # Получаем ресурс
    resource = db.query(TheoryResource).filter(TheoryResource.id == resource_id).first()
    if not resource:
        logger.warning(f"Admin {admin.email} attempted to delete non-existent resource ID: {resource_id}")
        raise HTTPException(status_code=404, detail="Ресурс не найден")

    # Запоминаем ID темы для перенаправления
    topic_id = resource.topic_id

    # Удаляем ресурс
    db.delete(resource)
    db.commit()

    logger.info(f"Resource ID: {resource_id} deleted by admin: {admin.email}")

    # Перенаправляем на страницу просмотра темы с активной вкладкой ресурсов
    redirect_url = f"/admin/theory/{topic_id}?tab=resources"
    if token:
        redirect_url += f"&token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Связывание вопроса с темой
@router.post("/theory/{topic_id}/questions/link", response_model=None)
async def admin_link_question(
    topic_id: int,
    question_id: int = Form(...),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Связывание вопроса с темой"""
    # Получаем тему
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        logger.warning(f"Admin {admin.email} attempted to link question to non-existent topic ID: {topic_id}")
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Получаем вопрос
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        logger.warning(f"Admin {admin.email} attempted to link non-existent question ID: {question_id}")
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    # Проверяем, не связан ли уже вопрос с этой темой
    if question in topic.questions:
        logger.info(f"Question ID: {question_id} already linked to topic ID: {topic_id}")
    else:
        # Связываем вопрос с темой
        topic.questions.append(question)
        db.commit()
        logger.info(f"Question ID: {question_id} linked to topic ID: {topic_id} by admin: {admin.email}")

    # Перенаправляем на страницу просмотра темы с активной вкладкой вопросов
    redirect_url = f"/admin/theory/{topic_id}?tab=questions"
    if token:
        redirect_url += f"&token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Удаление связи вопроса с темой
@router.get("/theory/{topic_id}/questions/{question_id}/unlink", response_model=None)
async def admin_unlink_question(
    topic_id: int,
    question_id: int,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Удаление связи вопроса с темой"""
    # Получаем тему
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        logger.warning(f"Admin {admin.email} attempted to unlink question from non-existent topic ID: {topic_id}")
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Получаем вопрос
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        logger.warning(f"Admin {admin.email} attempted to unlink non-existent question ID: {question_id}")
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    # Проверяем, связан ли вопрос с этой темой
    if question in topic.questions:
        # Удаляем связь вопроса с темой
        topic.questions.remove(question)
        db.commit()
        logger.info(f"Question ID: {question_id} unlinked from topic ID: {topic_id} by admin: {admin.email}")
    else:
        logger.info(f"Question ID: {question_id} was not linked to topic ID: {topic_id}")

    # Перенаправляем на страницу просмотра темы с активной вкладкой вопросов
    redirect_url = f"/admin/theory/{topic_id}?tab=questions"
    if token:
        redirect_url += f"&token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Удаление темы
@router.get("/theory/{topic_id}/delete", response_model=None)
async def admin_delete_topic(
    topic_id: int,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Удаление темы"""
    # Получаем тему
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        logger.warning(f"Admin {admin.email} attempted to delete non-existent topic ID: {topic_id}")
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Проверяем наличие дочерних тем
    child_topics = db.query(TheoryTopic).filter(TheoryTopic.parent_id == topic_id).count()
    if child_topics > 0:
        logger.warning(f"Admin {admin.email} attempted to delete topic ID: {topic_id} with {child_topics} child topics")
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить тему с дочерними темами. Сначала удалите {child_topics} дочерних тем."
        )

    # Запоминаем данные для перенаправления
    parent_id = topic.parent_id
    exam_type = topic.exam_type

    # Удаляем тему
    db.delete(topic)
    db.commit()

    logger.info(f"Topic ID: {topic_id} deleted by admin: {admin.email}")

    # Перенаправляем на родительскую тему или на список тем
    if parent_id:
        redirect_url = f"/admin/theory/{parent_id}"
    else:
        redirect_url = f"/admin/theory?exam_type={exam_type}"

    if token:
        redirect_url += f"{'&' if '?' in redirect_url else '?'}token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Управление категориями вопросов
@router.get("/categories", response_model=None)
async def admin_categories(
    request: Request,
    token: Optional[str] = Query(None),
    exam_type: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Список категорий вопросов"""
    # Базовый запрос
    query = db.query(QuestionCategory)

    # Применяем фильтр по типу экзамена, если указан
    if exam_type:
        query = query.filter(QuestionCategory.exam_type == exam_type)

    # Получаем отфильтрованные категории
    categories = query.all()

    # Получаем типы экзаменов
    exam_types = get_exam_types(db)

    logger.info(f"Category management accessed by admin: {admin.email}")
    return templates.TemplateResponse(
        "admin/categories.html",
        {
            "request": request,
            "title": "Управление категориями вопросов",
            "admin": admin,
            "categories": categories,
            "exam_types": exam_types,
            "selected_exam_type": exam_type,
            "token": token
        }
    )


# Добавление категории
@router.post("/categories/add", response_model=None)
async def admin_add_category(
    request: Request,
    name: str = Form(...),
    exam_type: str = Form(...),
    description: Optional[str] = Form(None),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Добавление новой категории вопросов"""
    try:
        # Проверяем уникальность имени категории
        existing_category = db.query(QuestionCategory).filter(
            QuestionCategory.name == name
        ).first()

        if existing_category:
            logger.warning(f"Attempt to create duplicate category '{name}' by admin: {admin.email}")
            # Получаем типы экзаменов
            exam_types = get_exam_types(db)

            return templates.TemplateResponse(
                "admin/categories.html",
                {
                    "request": request,
                    "title": "Управление категориями вопросов",
                    "admin": admin,
                    "categories": db.query(QuestionCategory).all(),
                    "exam_types": exam_types,
                    "selected_exam_type": None,
                    "token": token,
                    "error": f"Категория с названием '{name}' уже существует!"
                },
                status_code=400
            )

        # Создаем новую категорию
        category = QuestionCategory(
            name=name,
            exam_type=exam_type,
            description=description,
            created_at=datetime.utcnow()
        )

        db.add(category)
        db.commit()

        logger.info(f"New category '{name}' added by admin: {admin.email}")

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error when adding category '{name}' by admin: {admin.email}. Error: {str(e)}")
        # Получаем типы экзаменов
        exam_types = get_exam_types(db)

        return templates.TemplateResponse(
            "admin/categories.html",
            {
                "request": request,
                "title": "Управление категориями вопросов",
                "admin": admin,
                "categories": db.query(QuestionCategory).all(),
                "exam_types": exam_types,
                "selected_exam_type": None,
                "token": token,
                "error": f"Ошибка при добавлении категории: {str(e)}"
            },
            status_code=400
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error adding category '{name}': {str(e)}")
        logger.exception("Exception details:")
        # Получаем типы экзаменов
        exam_types = get_exam_types(db)

        return templates.TemplateResponse(
            "admin/categories.html",
            {
                "request": request,
                "title": "Управление категориями вопросов",
                "admin": admin,
                "categories": db.query(QuestionCategory).all(),
                "exam_types": exam_types,
                "selected_exam_type": None,
                "token": token,
                "error": f"Ошибка при добавлении категории: {str(e)}"
            },
            status_code=500
        )

    # Перенаправляем на страницу со списком категорий
    redirect_url = "/admin/categories"
    if token:
        redirect_url += f"?token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Редактирование категории
@router.post("/categories/edit", response_model=None)
async def admin_edit_category(
    request: Request,
    category_id: int = Form(...),
    name: str = Form(...),
    exam_type: str = Form(...),
    description: Optional[str] = Form(None),
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Редактирование категории вопросов"""
    try:
        # Получаем категорию по ID
        category = db.query(QuestionCategory).filter(
            QuestionCategory.id == category_id
        ).first()

        if not category:
            raise HTTPException(status_code=404, detail="Категория не найдена")

        # Проверяем уникальность имени, если оно изменилось
        if category.name != name:
            existing_category = db.query(QuestionCategory).filter(
                QuestionCategory.name == name,
                QuestionCategory.id != category_id
            ).first()

            if existing_category:
                raise HTTPException(status_code=400, detail="Категория с таким названием уже существует")

        # Обновляем данные категории
        category.name = name
        category.exam_type = exam_type
        category.description = description

        # Если категория изменила имя, обновляем поле category у вопросов
        if category.name != name:
            for question in category.questions:
                question.category = name

        db.commit()

        logger.info(f"Category ID: {category_id} updated by admin: {admin.email}")

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error when updating category ID: {category_id} by admin: {admin.email}")
        raise HTTPException(status_code=400, detail="Ошибка при обновлении категории") from e

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating category: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении категории: {str(e)}") from e

    # Перенаправляем на страницу со списком категорий
    redirect_url = "/admin/categories"
    if token:
        redirect_url += f"?token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)


# Удаление категории
@router.get("/categories/{category_id}/delete", response_model=None)
async def admin_delete_question_category(
    category_id: int,
    token: Optional[str] = Query(None),
    admin: User = Depends(check_admin_access),
    db: Session = Depends(get_db)
):
    """Удаление категории вопросов"""
    try:
        # Получаем категорию по ID
        category = db.query(QuestionCategory).filter(
            QuestionCategory.id == category_id
        ).first()

        if not category:
            logger.warning(f"Admin {admin.email} attempted to delete non-existent category ID: {category_id}")
            raise HTTPException(status_code=404, detail="Категория не найдена")

        # Обновляем связанные вопросы
        for question in category.questions:
            question.category_id = None

        # Удаляем категорию
        db.delete(category)
        db.commit()

        logger.info(f"Category ID: {category_id} deleted by admin: {admin.email}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting category: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении категории: {str(e)}") from e

    # Перенаправляем на страницу со списком категорий
    redirect_url = "/admin/categories"
    if token:
        redirect_url += f"?token={token}"

    return RedirectResponse(url=redirect_url, status_code=303)
