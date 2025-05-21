#!/usr/bin/env python3
"""
Скрипт для проверки состояния базы данных и её восстановления при необходимости
"""
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

import psycopg2

# Настройка логирования
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "db_health_check.log")

logger = logging.getLogger("db_health_check")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Получаем URL базы данных из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/rhcsa_db")

# Парсим URL для получения параметров подключения
url = urlparse(DATABASE_URL)
dbname = url.path[1:]  # Убираем начальный слеш
user = url.username
password = url.password
host = url.hostname
port = url.port


def check_and_create_database():
    """Проверяет существование базы данных и создает её, если она не существует"""
    try:
        # Подключаемся к postgres для создания базы данных
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Проверяем существование базы данных
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{dbname}'")
        exists = cursor.fetchone()

        if not exists:
            logger.warning(f"База данных '{dbname}' не существует. Создаем...")
            cursor.execute(f"CREATE DATABASE {dbname}")
            logger.info(f"База данных '{dbname}' успешно создана.")
            return True
        else:
            logger.info(f"База данных '{dbname}' существует.")
            return False

    except Exception as e:
        logger.error(f"Ошибка при проверке/создании базы данных: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()


def check_database_connection():
    """Проверяет подключение к базе данных"""
    try:
        # Пытаемся подключиться к базе данных
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.close()
        logger.info("Подключение к базе данных успешно.")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return False


def run_health_check():
    """Запускает проверку здоровья базы данных"""
    logger.info("Запуск проверки состояния базы данных...")

    # Проверяем подключение к базе данных
    if not check_database_connection():
        # Если не удалось подключиться, пробуем создать базу данных
        if check_and_create_database():
            logger.info("База данных была восстановлена.")
            # Здесь можно добавить код для запуска инициализации базы данных
            # например, запуск init_db.py
            try:
                logger.info("Запуск инициализации схемы базы данных...")
                # Импортируем необходимые модули
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from database import Base, engine
                Base.metadata.create_all(bind=engine)
                logger.info("Схема базы данных успешно создана.")
            except Exception as e:
                logger.error(f"Ошибка при инициализации схемы базы данных: {e}")
        else:
            logger.error("Не удалось восстановить базу данных.")
    else:
        logger.info("База данных работает нормально.")


if __name__ == "__main__":
    # Если скрипт запущен напрямую, выполняем одну проверку
    run_health_check()

    # Если передан аргумент --daemon, запускаем в режиме демона
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        check_interval = int(os.getenv("DB_HEALTH_CHECK_INTERVAL", "300"))  # По умолчанию 5 минут
        logger.info(f"Запуск в режиме демона с интервалом {check_interval} секунд")

        while True:
            try:
                time.sleep(check_interval)
                run_health_check()
            except KeyboardInterrupt:
                logger.info("Проверка состояния базы данных остановлена.")
                break
            except Exception as e:
                logger.error(f"Неожиданная ошибка: {e}")
                time.sleep(60)  # В случае ошибки ждем минуту перед следующей попыткой
