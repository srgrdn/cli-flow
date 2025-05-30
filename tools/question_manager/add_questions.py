#!/usr/bin/env python3
"""
Скрипт для добавления вопросов в CLI-Flow через API.
Поддерживает проверку существующих вопросов перед добавлением.
"""

import argparse
import json
import sys
import time
import os

try:
    import requests
except ImportError:
    print("Ошибка: библиотека requests не установлена")
    print("Установите ее с помощью команды: pip install requests")
    sys.exit(1)

from typing import Dict, List


class QuestionManager:
    """Класс для управления вопросами через API CLI-Flow"""

    def __init__(self, base_url: str, username: str, password: str):
        """
        Инициализация менеджера вопросов.
        
        Args:
            base_url: Базовый URL API (например, http://localhost)
            username: Имя пользователя для авторизации
            password: Пароль для авторизации
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()
        self.added_questions_cache = self._load_added_questions_cache()
    
    def login(self) -> bool:
        """
        Авторизация в системе и получение токена.
        
        Returns:
            bool: True, если авторизация успешна, иначе False
        """
        try:
            login_url = f"{self.base_url}/auth/login"
            print(f"Авторизация на {login_url}")
            
            # Используем form-data вместо JSON
            auth_data = {"username": self.username, "password": self.password}
            response = self.session.post(login_url, data=auth_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if not self.token:
                    print("Ошибка: токен не получен")
                    return False
                
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print("Успешная авторизация")
                return True
            else:
                print(f"Ошибка авторизации: {response.status_code}")
                return False
        except Exception as e:
            print(f"Ошибка при авторизации: {str(e)}")
            return False
    
    def get_questions(self) -> List[Dict]:
        """
        Получение списка вопросов из системы с поддержкой пагинации.
        
        Returns:
            List[Dict]: Список вопросов
        """
        try:
            questions_url = f"{self.base_url}/questions/"
            print(f"Получение вопросов с {questions_url}")
            
            all_questions = []
            page = 1
            per_page = 100
            max_pages = 10  # Ограничиваем количество страниц для безопасности
            
            while page <= max_pages:
                params = {"page": page, "per_page": per_page}
                print(f"Запрос страницы {page} с {per_page} вопросами на странице")
                response = self.session.get(questions_url, params=params)
                
                if response.status_code == 200:
                    questions = response.json()
                    print(f"Получено {len(questions)} вопросов на странице {page}")
                    
                    if not questions:
                        break  # Если пустой список, значит достигли конца
                    
                    all_questions.extend(questions)
                    
                    # Если получено меньше вопросов, чем per_page, значит это последняя страница
                    if len(questions) < per_page:
                        break
                    
                    page += 1
                else:
                    print(f"Ошибка получения вопросов: {response.status_code}")
                    break
            
            print(f"Всего получено {len(all_questions)} вопросов")
            return all_questions
        except Exception as e:
            print(f"Ошибка при получении вопросов: {str(e)}")
            return []
    
    def question_exists(self, question_text: str) -> bool:
        """
        Проверка существования вопроса по тексту и в кэше добавленных вопросов.
        
        Args:
            question_text: Текст вопроса
            
        Returns:
            bool: True, если вопрос существует, иначе False
        """
        # Проверка в кэше добавленных вопросов
        normalized_text = " ".join(question_text.lower().split())
        if normalized_text in self.added_questions_cache:
            print("Вопрос найден в кэше добавленных вопросов")
            return True
        
        # Если не найден в кэше, проверяем через API
        return self._check_exists_in_all_questions(question_text)
    
    def _check_exists_in_all_questions(self, question_text: str) -> bool:
        """
        Проверка существования вопроса по всем страницам вопросов.
        
        Args:
            question_text: Текст вопроса
            
        Returns:
            bool: True, если вопрос существует, иначе False
        """
        questions = self.get_questions()
        
        # Нормализация текста для сравнения
        normalized_text = " ".join(question_text.lower().split())
        print(f"Проверка по всем вопросам: '{normalized_text[:50]}...'")
        
        for question in questions:
            existing_text = " ".join(question.get("text", "").lower().split())
            if normalized_text == existing_text:
                print(f"Найден существующий вопрос с ID {question.get('id')}")
                return True
        
        print("Вопрос не найден в базе данных")
        return False
    
    def add_question(self, question_data: Dict) -> int:
        """
        Добавление вопроса через API.
        
        Args:
            question_data: Данные вопроса в формате API
            
        Returns:
            int: ID добавленного вопроса или 0 в случае ошибки
        """
        try:
            questions_url = f"{self.base_url}/questions/"
            response = self.session.post(questions_url, json=question_data)
            
            if response.status_code == 200:
                result = response.json()
                question_id = result.get("id", 0)
                
                # Сохраняем текст вопроса в кэш добавленных вопросов
                if question_id > 0:
                    normalized_text = " ".join(question_data["text"].lower().split())
                    self.added_questions_cache[normalized_text] = question_id
                    self._save_added_questions_cache()
                
                return question_id
            else:
                print(f"Ошибка добавления вопроса: {response.status_code}")
                return 0
        except Exception as e:
            print(f"Ошибка при добавлении вопроса: {str(e)}")
            return 0
    
    def _load_added_questions_cache(self) -> Dict[str, int]:
        """
        Загрузка кэша добавленных вопросов из файла.
        
        Returns:
            Dict[str, int]: Словарь с текстами вопросов и их ID
        """
        cache_file = "added_questions_cache.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except Exception as e:
                print(f"Ошибка при загрузке кэша: {str(e)}")
        
        return {}
    
    def _save_added_questions_cache(self):
        """Сохранение кэша добавленных вопросов в файл."""
        cache_file = "added_questions_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as file:
                json.dump(self.added_questions_cache, file, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении кэша: {str(e)}")


def load_questions_from_file(file_path: str) -> List[Dict]:
    """
    Загрузка вопросов из JSON-файла.
    
    Args:
        file_path: Путь к JSON-файлу с вопросами
        
    Returns:
        List[Dict]: Список вопросов
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Ошибка при загрузке файла {file_path}: {str(e)}")
        return []


def parse_args():
    """
    Парсинг аргументов командной строки.
    
    Returns:
        argparse.Namespace: Аргументы командной строки
    """
    parser = argparse.ArgumentParser(description='Добавление вопросов в CLI-Flow')
    parser.add_argument('-f', '--file', required=True, help='JSON-файл с вопросами')
    parser.add_argument('-u', '--username', required=True, help='Имя пользователя для авторизации')
    parser.add_argument('-p', '--password', required=True, help='Пароль для авторизации')
    parser.add_argument('-b', '--base-url', default='http://localhost:80', help='Базовый URL API (по умолчанию: http://localhost:80)')
    parser.add_argument('-c', '--check', action='store_true', help='Проверить вопросы без добавления')
    parser.add_argument('-e', '--exam-type', choices=['rhcsa', 'cka'], help='Тип экзамена (если не указан в файле)')
    return parser.parse_args()


def main():
    """Основная функция скрипта"""
    args = parse_args()
    
    # Загрузка вопросов из файла
    questions = load_questions_from_file(args.file)
    if not questions:
        print("Не удалось загрузить вопросы из файла")
        sys.exit(1)
    
    # Инициализация менеджера вопросов
    manager = QuestionManager(args.base_url, args.username, args.password)
    
    # Авторизация
    if not manager.login():
        print("Не удалось авторизоваться")
        sys.exit(1)
    
    # Статистика
    total_questions = len(questions)
    added_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"\nНачинаем обработку {total_questions} вопросов из файла {args.file}")
    
    # Обработка вопросов
    for i, question_data in enumerate(questions, 1):
        # Если тип экзамена указан в аргументах и не указан в вопросе, добавляем его
        if args.exam_type and "exam_type" not in question_data:
            question_data["exam_type"] = args.exam_type
        
        # Проверка наличия обязательных полей
        if "text" not in question_data or "answers" not in question_data:
            print(f"Пропуск вопроса #{i}: отсутствуют обязательные поля")
            error_count += 1
            continue
        
        # Проверка существования вопроса
        if manager.question_exists(question_data["text"]):
            print(f"Пропуск вопроса #{i}: уже существует в базе данных")
            skipped_count += 1
            continue
        
        # Если режим проверки, просто выводим информацию
        if args.check:
            print(f"Вопрос #{i} будет добавлен: {question_data['text'][:50]}...")
            continue
        
        # Добавление вопроса
        question_id = manager.add_question(question_data)
        if question_id > 0:
            print(f"Добавлен вопрос #{i} с ID {question_id}: {question_data['text'][:50]}...")
            added_count += 1
        else:
            print(f"Ошибка при добавлении вопроса #{i}")
            error_count += 1
        
        # Небольшая пауза между запросами
        time.sleep(0.5)
    
    # Вывод статистики
    print("\nСтатистика:")
    print(f"Всего вопросов в файле: {total_questions}")
    
    if args.check:
        print(f"Вопросов для добавления: {total_questions - skipped_count - error_count}")
        print(f"Пропущено (уже существуют): {skipped_count}")
        print(f"Ошибок: {error_count}")
    else:
        print(f"Добавлено: {added_count}")
        print(f"Пропущено (уже существуют): {skipped_count}")
        print(f"Ошибок: {error_count}")


if __name__ == "__main__":
    main() 