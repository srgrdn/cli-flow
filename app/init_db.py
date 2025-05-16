"""Скрипт для инициализации базы данных тестовыми данными"""

import os
import sys

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine, Base
from models import Question, Answer

# Тестовые данные для заполнения базы
sample_questions = [
    {
        "text": "Какая команда используется для создания нового пользователя в Linux?",
        "difficulty": "easy",
        "category": "Управление пользователями",
        "answers": [
            {"text": "useradd", "is_correct": True},
            {"text": "usermod", "is_correct": False},
            {"text": "userdel", "is_correct": False},
            {"text": "userctl", "is_correct": False}
        ]
    },
    {
        "text": "Какой файл содержит информацию о точках монтирования файловых систем?",
        "difficulty": "medium",
        "category": "Файловые системы",
        "answers": [
            {"text": "/etc/fstab", "is_correct": True},
            {"text": "/etc/mtab", "is_correct": False},
            {"text": "/etc/filesystems", "is_correct": False},
            {"text": "/proc/mounts", "is_correct": False}
        ]
    },
    {
        "text": "Какая команда используется для изменения прав доступа к файлу?",
        "difficulty": "easy",
        "category": "Права доступа",
        "answers": [
            {"text": "chmod", "is_correct": True},
            {"text": "chown", "is_correct": False},
            {"text": "chgrp", "is_correct": False},
            {"text": "chattr", "is_correct": False}
        ]
    },
    {
        "text": "Какой тип RAID обеспечивает зеркалирование данных?",
        "difficulty": "medium",
        "category": "Хранение данных",
        "answers": [
            {"text": "RAID 1", "is_correct": True},
            {"text": "RAID 0", "is_correct": False},
            {"text": "RAID 5", "is_correct": False},
            {"text": "RAID 6", "is_correct": False}
        ]
    },
    {
        "text": "Какая команда используется для создания логического тома в LVM?",
        "difficulty": "hard",
        "category": "LVM",
        "answers": [
            {"text": "lvcreate", "is_correct": True},
            {"text": "vgcreate", "is_correct": False},
            {"text": "pvcreate", "is_correct": False},
            {"text": "lvextend", "is_correct": False}
        ]
    }
]

def init_db():
    """Инициализация базы данных тестовыми данными"""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже данные в базе
        existing_questions = db.query(Question).count()
        if existing_questions > 0:
            print("База данных уже содержит вопросы. Пропускаем инициализацию.")
            return
        
        # Добавляем тестовые вопросы и ответы
        for q_data in sample_questions:
            question = Question(
                text=q_data["text"],
                difficulty=q_data["difficulty"],
                category=q_data["category"]
            )
            db.add(question)
            db.commit()
            
            # Добавляем ответы для вопроса
            for a_data in q_data["answers"]:
                answer = Answer(
                    text=a_data["text"],
                    is_correct=a_data["is_correct"],
                    question_id=question.id
                )
                db.add(answer)
            
            db.commit()
        
        print(f"База данных успешно инициализирована {len(sample_questions)} вопросами.")
    
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
    finally:
        db.close()

# Обновление схемы базы данных
print("Убедитесь, что схема базы данных обновлена...")
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()