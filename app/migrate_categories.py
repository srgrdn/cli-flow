import os
import sys

from sqlalchemy.sql import text

from database import SessionLocal

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def add_category_id_column():
    """Добавление колонки category_id в таблицу questions"""
    db = SessionLocal()
    try:
        # Проверяем, существует ли уже колонка category_id
        check_query = text("SELECT column_name FROM information_schema.columns WHERE table_name='questions' AND column_name='category_id'")
        result = db.execute(check_query)
        column_exists = result.fetchone() is not None

        if not column_exists:
            # Добавляем колонку category_id
            alter_query = text("ALTER TABLE questions ADD COLUMN category_id INTEGER")
            db.execute(alter_query)
            db.commit()
            print("Колонка category_id добавлена в таблицу questions")
        else:
            print("Колонка category_id уже существует в таблице questions")

        db.close()
        return True

    except Exception as e:
        db.rollback()
        print(f"Ошибка при добавлении колонки: {str(e)}")
        db.close()
        return False


if __name__ == "__main__":
    add_category_id_column()
    print("Миграция завершена.")
