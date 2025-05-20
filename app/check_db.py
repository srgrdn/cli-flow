#!/usr/bin/env python3
"""
Скрипт для проверки данных в базе данных.
"""
from sqlalchemy import text

from database import engine


def check_db():
    """Check database tables and counts"""
    with engine.connect() as conn:
        # Check users table
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        users_count = result.fetchone()[0]
        print(f"Users count: {users_count}")

        # Check questions table
        result = conn.execute(text("SELECT COUNT(*) FROM questions"))
        questions_count = result.fetchone()[0]
        print(f"Questions count: {questions_count}")

        # Check answers table
        result = conn.execute(text("SELECT COUNT(*) FROM answers"))
        answers_count = result.fetchone()[0]
        print(f"Answers count: {answers_count}")

if __name__ == "__main__":
    check_db()
