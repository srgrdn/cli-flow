#!/usr/bin/env python3

from database import get_db
from models import Answer, Question


def check_question(question_id):
    db = next(get_db())
    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        print(f"Вопрос с ID {question_id} не найден")
        return

    print(f"Вопрос ID: {question.id}")
    print(f"Текст: {question.text}")
    print(f"Тип экзамена: {question.exam_type}")
    print(f"Категория: {question.category}")
    print(f"Сложность: {question.difficulty}")

    print("\nВарианты ответов:")
    answers = db.query(Answer).filter(Answer.question_id == question_id).all()
    for i, answer in enumerate(answers, 1):
        correct = "✓" if answer.is_correct else "✗"
        print(f"{i}. {answer.text} [{correct}]")


if __name__ == "__main__":
    check_question(137)
