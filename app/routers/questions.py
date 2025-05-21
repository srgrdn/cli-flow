from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Answer, Question, TestAttempt, User, UserAnswer
from routers.auth import AuthService
from schemas import QuestionCreate, QuestionResponse

router = APIRouter(
    prefix="/questions",
    tags=["questions"],
    responses={404: {"description": "Не найдено"}},
)

templates = Jinja2Templates(directory="templates")
security = HTTPBearer(auto_error=False)


# Функция для проверки авторизации пользователя
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    token: Optional[str] = Query(None)
):
    """Получение текущего пользователя из токена"""
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

        return user
    except Exception as e:
        raise HTTPException(
            status_code=403,
            detail=f"Ошибка авторизации: {str(e)}"
        ) from e


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
    user: User = Depends(get_current_user)
):
    """Страница выбора категорий и сложности для теста (требует авторизации)"""
    # Получаем все уникальные категории из базы данных
    categories = db.query(Question.category).distinct().all()
    categories = [cat[0] for cat in categories]

    # Получаем все уникальные уровни сложности
    difficulties = db.query(Question.difficulty).distinct().all()
    difficulties = [diff[0] for diff in difficulties]

    return templates.TemplateResponse(
        "test_categories.html",
        {
            "request": request,
            "categories": categories,
            "difficulties": difficulties,
            "title": "Выбор параметров для тестирования RHCSA",
            "user": user
        }
    )


@router.post("/start_test", response_model=None)
async def start_test(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Начать тест с выбранными категориями и сложностью"""
    form_data = await request.form()

    # Получаем выбранные категории из формы
    selected_categories = []
    for key, value in form_data.items():
        if key == "categories":
            selected_categories.append(value)

    # Получаем выбранные уровни сложности из формы
    selected_difficulties = []
    for key, value in form_data.items():
        if key == "difficulties":
            selected_difficulties.append(value)

    # Строим запрос на основе выбранных фильтров
    query = db.query(Question)

    # Применяем фильтр по категориям, если они выбраны
    if selected_categories:
        query = query.filter(Question.category.in_(selected_categories))

    # Применяем фильтр по сложности, если она выбрана
    if selected_difficulties:
        query = query.filter(Question.difficulty.in_(selected_difficulties))

    # Получаем отфильтрованные вопросы
    questions = query.all()

    # Создаем новую попытку прохождения теста
    test_attempt = TestAttempt(
        user_id=user.id,
        start_time=datetime.utcnow(),
        max_score=len(questions)
    )
    db.add(test_attempt)
    db.commit()
    db.refresh(test_attempt)

    # Add selected categories as hidden fields to pass them to the results page
    return templates.TemplateResponse(
        "test.html",
        {
            "request": request,
            "questions": questions,
            "title": "Теоретический тест RHCSA",
            "test_attempt_id": test_attempt.id,
            "user": user,
            "selected_categories": selected_categories,
            "selected_difficulties": selected_difficulties
        }
    )


@router.post("/submit", response_model=None)
async def submit_test(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    test_attempt_id: int = Form(...),
):
    """Отправка и проверка ответов на тест"""
    # Получаем текущую попытку прохождения теста
    test_attempt = db.query(TestAttempt).filter(
        TestAttempt.id == test_attempt_id,
        TestAttempt.user_id == user.id
    ).first()

    if not test_attempt:
        raise HTTPException(status_code=404, detail="Попытка прохождения теста не найдена")

    # Завершаем попытку
    test_attempt.end_time = datetime.utcnow()

    # Обрабатываем данные формы
    form_data = await request.form()

    # Получаем выбранные категории, если они были переданы
    selected_categories = []
    for key, value in form_data.items():
        if key.startswith('selected_category_'):
            selected_categories.append(value)

    # Получаем выбранные уровни сложности, если они были переданы
    selected_difficulties = []
    for key, value in form_data.items():
        if key.startswith('selected_difficulty_'):
            selected_difficulties.append(value)

    # Словарь для результатов
    results = {
        "score": 0,
        "max_score": 0,
        "correct_answers": 0,
        "total_questions": 0,
        "details": []
    }

    # Обрабатываем ответы
    for key, value in form_data.items():
        if key.startswith('question_') and key != 'test_attempt_id':
            question_id = int(key.replace('question_', ''))
            answer_id = int(value)

            # Получаем вопрос и ответ
            question = db.query(Question).filter(Question.id == question_id).first()
            answer = db.query(Answer).filter(Answer.id == answer_id).first()

            if question and answer:
                results["total_questions"] += 1
                results["max_score"] += 1

                # Проверяем правильность ответа
                is_correct = answer.is_correct
                if is_correct:
                    results["correct_answers"] += 1
                    results["score"] += 1

                # Сохраняем ответ пользователя
                user_answer = UserAnswer(
                    test_attempt_id=test_attempt.id,
                    question_id=question_id,
                    answer_id=answer_id,
                    is_correct=is_correct
                )
                db.add(user_answer)

                # Добавляем детали для отображения
                correct_answer = db.query(Answer).filter(
                    Answer.question_id == question_id,
                    Answer.is_correct == True  # noqa: E712
                ).first()

                results["details"].append({
                    "question_id": question_id,
                    "question_text": question.text,
                    "user_answer": answer.text,
                    "is_correct": is_correct,
                    "correct_answer": correct_answer.text if correct_answer else "Нет правильного ответа"
                })

    # Обновляем результаты теста
    test_attempt.score = results["score"]
    test_attempt.max_score = results["max_score"]
    db.commit()

    # Рассчитываем процент правильных ответов
    results["percentage"] = (results["score"] / results["max_score"]) * 100 if results["max_score"] > 0 else 0

    # Отображаем результаты
    return templates.TemplateResponse(
        "test_results.html",
        {
            "request": request,
            "title": "Результаты теста",
            "results": results,
            "user": user,
            "selected_categories": selected_categories,
            "selected_difficulties": selected_difficulties
        }
    )


@router.get("/history", response_model=None)
async def test_history(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """История прохождения тестов пользователя"""
    # Получаем историю прохождения тестов
    test_attempts = db.query(TestAttempt).filter(
        TestAttempt.user_id == user.id,
        TestAttempt.end_time.is_not(None)  # noqa: E711
    ).order_by(TestAttempt.end_time.desc()).all()

    return templates.TemplateResponse(
        "test_history.html",
        {
            "request": request,
            "title": "История тестирования",
            "test_attempts": test_attempts,
            "user": user
        }
    )


@router.get("/{question_id}", response_model=QuestionResponse)
async def read_question(question_id: int, db: Session = Depends(get_db)):
    """Получение конкретного вопроса по ID"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    return question
