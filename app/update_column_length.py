import os
import sys

from sqlalchemy.sql import text

from database import SessionLocal

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def update_column_types():
    """Обновление типов колонок в таблице question_categories"""
    db = SessionLocal()
    try:
        # Изменяем тип колонки name на VARCHAR(255)
        db.execute(text("ALTER TABLE question_categories ALTER COLUMN name TYPE VARCHAR(255)"))

        # Изменяем тип колонки exam_type на VARCHAR(50)
        db.execute(text("ALTER TABLE question_categories ALTER COLUMN exam_type TYPE VARCHAR(50)"))

        db.commit()
        print("Типы колонок в таблице question_categories успешно обновлены")
        db.close()
        return True

    except Exception as e:
        db.rollback()
        print(f"Ошибка при обновлении типов колонок: {str(e)}")
        db.close()
        return False


if __name__ == "__main__":
    update_column_types()
    print("Миграция завершена.")
