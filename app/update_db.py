import os
import sys
from datetime import datetime

from sqlalchemy.sql import text

from database import SessionLocal, engine
from models import Base, Question, QuestionCategory

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_tables():
    """Создание таблиц в базе данных"""
    Base.metadata.create_all(bind=engine)
    print("Таблицы созданы.")


def migrate_categories():
    """Миграция существующих категорий вопросов в новую таблицу"""
    db = SessionLocal()
    try:
        # Проверяем, существует ли таблица категорий
        db.execute(text("SELECT 1 FROM question_categories LIMIT 1"))
        print("Таблица категорий уже существует.")
    except Exception:
        print("Создаем таблицу категорий...")
        create_tables()

    # Получаем все уникальные категории из вопросов
    categories = db.query(Question.category, Question.exam_type).distinct().all()

    # Создаем категории в новой таблице
    for category, exam_type in categories:
        if not category:
            continue

        # Проверяем, существует ли уже такая категория
        existing = db.query(QuestionCategory).filter(QuestionCategory.name == category).first()
        if existing:
            print(f"Категория '{category}' уже существует.")
            continue

        # Создаем новую категорию
        new_category = QuestionCategory(
            name=category,
            exam_type=exam_type or "rhcsa",
            description=f"Категория вопросов: {category}",
            created_at=datetime.utcnow()
        )
        db.add(new_category)

    # Сохраняем изменения
    try:
        db.commit()
        print(f"Создано {len(categories)} категорий.")
    except Exception as e:
        db.rollback()
        print(f"Ошибка при создании категорий: {str(e)}")

    # Обновляем связи вопросов с категориями
    try:
        # Обновляем для каждого вопроса поле category_id
        for category, _ in categories:
            if not category:
                continue

            # Получаем ID категории
            cat = db.query(QuestionCategory).filter(QuestionCategory.name == category).first()
            if not cat:
                continue

            # Обновляем вопросы этой категории
            db.query(Question).filter(Question.category == category).update({"category_id": cat.id})

        db.commit()
        print("Связи вопросов с категориями обновлены.")
    except Exception as e:
        db.rollback()
        print(f"Ошибка при обновлении связей: {str(e)}")

    db.close()


if __name__ == "__main__":
    migrate_categories()
    print("Миграция завершена.")
