from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Question, TheoryContent, TheoryResource, TheoryTopic, User
from routers.questions import get_current_user
from schemas import (
    TheoryContentCreate,
    TheoryResourceCreate,
    TheoryTopicCreate,
    TheoryTopicDetail,
    TheoryTopicResponse,
    TheoryTopicUpdate,
)
from schemas import TheoryResource as TheoryResourceSchema

router = APIRouter(
    prefix="/theory",
    tags=["theory"],
    responses={404: {"description": "Не найдено"}},
)

templates = Jinja2Templates(directory="templates")


# API для работы с темами теории
@router.post("/topics/", response_model=TheoryTopicResponse)
async def create_topic(
    topic: TheoryTopicCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Создание новой темы теории (требуется авторизация)"""
    # Проверяем, является ли пользователь администратором
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Недостаточно прав для создания тем")

    # Проверяем существование родительской темы, если указана
    if topic.parent_id:
        parent_topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic.parent_id).first()
        if not parent_topic:
            raise HTTPException(status_code=404, detail="Родительская тема не найдена")

    # Создаем новую тему
    db_topic = TheoryTopic(
        title=topic.title,
        description=topic.description,
        parent_id=topic.parent_id,
        exam_type=topic.exam_type,
        order=topic.order
    )
    db.add(db_topic)
    db.commit()
    db.refresh(db_topic)
    return db_topic


@router.get("/topics/", response_model=List[TheoryTopicResponse])
async def read_topics(
    exam_type: Optional[str] = None,
    parent_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получение списка тем теории с возможностью фильтрации"""
    query = db.query(TheoryTopic)

    # Применяем фильтры, если указаны
    if exam_type:
        query = query.filter(TheoryTopic.exam_type == exam_type)

    if parent_id is not None:
        query = query.filter(TheoryTopic.parent_id == parent_id)
    else:
        # Если parent_id не указан, возвращаем только корневые темы
        query = query.filter(TheoryTopic.parent_id is None)

    # Сортируем по порядку отображения
    query = query.order_by(TheoryTopic.order)

    # Применяем пагинацию
    topics = query.offset(skip).limit(limit).all()
    return topics


@router.get("/topics/{topic_id}", response_model=TheoryTopicDetail)
async def read_topic(topic_id: int, db: Session = Depends(get_db)):
    """Получение детальной информации о теме теории"""
    # Загружаем тему с содержимым, ресурсами, дочерними темами и вопросами
    topic = db.query(TheoryTopic).options(
        joinedload(TheoryTopic.content),
        joinedload(TheoryTopic.resources),
        joinedload(TheoryTopic.children),
        joinedload(TheoryTopic.questions)
    ).filter(TheoryTopic.id == topic_id).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    return topic


@router.put("/topics/{topic_id}", response_model=TheoryTopicResponse)
async def update_topic(
    topic_id: int,
    topic_update: TheoryTopicUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Обновление темы теории (требуется авторизация администратора)"""
    # Проверяем, является ли пользователь администратором
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Недостаточно прав для обновления тем")

    # Получаем тему из БД
    db_topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not db_topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Проверяем существование родительской темы, если указана
    if topic_update.parent_id is not None and topic_update.parent_id != db_topic.parent_id:
        if topic_update.parent_id == topic_id:
            raise HTTPException(status_code=400, detail="Тема не может быть родительской для самой себя")

        if topic_update.parent_id != 0:  # 0 означает сделать корневой темой
            parent_topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_update.parent_id).first()
            if not parent_topic:
                raise HTTPException(status_code=404, detail="Родительская тема не найдена")

            # Проверяем, не создаст ли это циклическую зависимость
            current_parent = parent_topic
            while current_parent:
                if current_parent.id == topic_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Невозможно создать циклическую зависимость в иерархии тем"
                    )
                current_parent = db.query(TheoryTopic).filter(
                    TheoryTopic.id == current_parent.parent_id
                ).first()

    # Обновляем поля темы
    update_data = topic_update.dict(exclude_unset=True)
    if topic_update.parent_id == 0:
        update_data["parent_id"] = None

    for key, value in update_data.items():
        setattr(db_topic, key, value)

    db.commit()
    db.refresh(db_topic)
    return db_topic


@router.delete("/topics/{topic_id}")
async def delete_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Удаление темы теории (требуется авторизация администратора)"""
    # Проверяем, является ли пользователь администратором
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления тем")

    # Проверяем наличие дочерних тем
    child_topics = db.query(TheoryTopic).filter(TheoryTopic.parent_id == topic_id).count()
    if child_topics > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить тему с дочерними темами. Сначала удалите {child_topics} дочерних тем."
        )

    # Удаляем тему
    db_topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not db_topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    db.delete(db_topic)
    db.commit()
    return {"message": "Тема успешно удалена"}


# API для работы с содержимым теории
@router.post("/topics/{topic_id}/content", response_model=TheoryTopicDetail)
async def create_or_update_content(
    topic_id: int,
    content: TheoryContentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Создание или обновление содержимого темы теории (требуется авторизация администратора)"""
    # Проверяем, является ли пользователь администратором
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования содержимого")

    # Проверяем существование темы
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Проверяем, существует ли уже содержимое для этой темы
    existing_content = db.query(TheoryContent).filter(TheoryContent.topic_id == topic_id).first()

    if existing_content:
        # Обновляем существующее содержимое
        existing_content.content = content.content
        db.commit()
        db.refresh(existing_content)
    else:
        # Создаем новое содержимое
        new_content = TheoryContent(
            topic_id=topic_id,
            content=content.content
        )
        db.add(new_content)
        db.commit()

    # Возвращаем обновленную тему с содержимым
    return await read_topic(topic_id, db)


# API для работы с ресурсами теории
@router.post("/topics/{topic_id}/resources", response_model=TheoryResourceSchema)
async def create_resource(
    topic_id: int,
    resource: TheoryResourceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Добавление ресурса к теме теории (требуется авторизация администратора)"""
    # Проверяем, является ли пользователь администратором
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Недостаточно прав для добавления ресурсов")

    # Проверяем существование темы
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Создаем новый ресурс
    db_resource = TheoryResource(
        topic_id=topic_id,
        title=resource.title,
        url=resource.url,
        resource_type=resource.resource_type
    )
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource


@router.delete("/resources/{resource_id}")
async def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Удаление ресурса (требуется авторизация администратора)"""
    # Проверяем, является ли пользователь администратором
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления ресурсов")

    # Удаляем ресурс
    db_resource = db.query(TheoryResource).filter(TheoryResource.id == resource_id).first()
    if not db_resource:
        raise HTTPException(status_code=404, detail="Ресурс не найден")

    db.delete(db_resource)
    db.commit()
    return {"message": "Ресурс успешно удален"}


# API для связывания вопросов с темами теории
@router.post("/topics/{topic_id}/questions/{question_id}")
async def link_question_to_topic(
    topic_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Связывание вопроса с темой теории (требуется авторизация администратора)"""
    # Проверяем, является ли пользователь администратором
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Недостаточно прав для связывания вопросов с темами")

    # Проверяем существование темы
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Проверяем существование вопроса
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    # Проверяем, не связан ли уже вопрос с этой темой
    if question in topic.questions:
        return {"message": "Вопрос уже связан с этой темой"}

    # Связываем вопрос с темой
    topic.questions.append(question)
    db.commit()
    return {"message": "Вопрос успешно связан с темой"}


@router.delete("/topics/{topic_id}/questions/{question_id}")
async def unlink_question_from_topic(
    topic_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Удаление связи вопроса с темой теории (требуется авторизация администратора)"""
    # Проверяем, является ли пользователь администратором
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления связей вопросов с темами")

    # Проверяем существование темы
    topic = db.query(TheoryTopic).filter(TheoryTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Проверяем существование вопроса
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    # Проверяем, связан ли вопрос с этой темой
    if question not in topic.questions:
        return {"message": "Вопрос не связан с этой темой"}

    # Удаляем связь вопроса с темой
    topic.questions.remove(question)
    db.commit()
    return {"message": "Связь вопроса с темой успешно удалена"}


# Веб-интерфейс для теории
@router.get("/", response_class=HTMLResponse)
async def theory_page(
    request: Request,
    exam_type: str = "rhcsa",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Страница с теоретическими материалами"""
    # Получаем корневые темы для выбранного типа экзамена
    # Используем .filter(TheoryTopic.parent_id.is_(None)) для SQLAlchemy
    root_topics = db.query(TheoryTopic).filter(
        TheoryTopic.parent_id.is_(None),
        TheoryTopic.exam_type == exam_type
    ).order_by(TheoryTopic.order).all()

    return templates.TemplateResponse(
        "theory_index.html",
        {
            "request": request,
            "title": f"Теоретические материалы - {exam_type.upper()}",
            "exam_type": exam_type,
            "topics": root_topics,
            "user": current_user  # Передаем информацию о пользователе в шаблон
        }
    )


@router.get("/{topic_id}", response_class=HTMLResponse)
async def theory_topic_page(
    request: Request,
    topic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Страница с содержимым темы теории"""
    # Загружаем тему с содержимым, ресурсами, дочерними темами и вопросами
    topic = db.query(TheoryTopic).options(
        joinedload(TheoryTopic.content),
        joinedload(TheoryTopic.resources),
        joinedload(TheoryTopic.children),
        joinedload(TheoryTopic.questions)
    ).filter(TheoryTopic.id == topic_id).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    # Отладка - выводим информацию о содержимом темы
    if hasattr(topic, 'content') and topic.content:
        content_items = topic.content
        if content_items and len(content_items) > 0:
            print(f"DEBUG: Topic {topic_id} has {len(content_items)} content items")
            print(f"DEBUG: First content item: {content_items[0].content[:100]}...")
        else:
            print(f"DEBUG: Topic {topic_id} has empty content list")
    else:
        print(f"DEBUG: Topic {topic_id} has no content attribute")

    # Получаем путь к теме (хлебные крошки)
    breadcrumbs = []
    current_topic = topic
    while current_topic:
        breadcrumbs.insert(0, current_topic)
        if current_topic.parent_id:
            current_topic = db.query(TheoryTopic).filter(
                TheoryTopic.id == current_topic.parent_id
            ).first()
        else:
            break

    return templates.TemplateResponse(
        "theory_topic.html",
        {
            "request": request,
            "title": topic.title,
            "topic": topic,
            "breadcrumbs": breadcrumbs,
            "user": current_user  # Передаем информацию о пользователе в шаблон
        }
    )
