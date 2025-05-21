#!/usr/bin/env python3
"""
Скрипт для создания резервных копий базы данных
"""
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

# Настройка логирования
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "db_backup.log")

logger = logging.getLogger("db_backup")
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

# Настройка директории для резервных копий
BACKUP_DIR = os.getenv("BACKUP_DIR", "/app/backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

# Максимальное количество хранимых резервных копий
MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "7"))


def create_backup():
    """Создает резервную копию базы данных"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"{dbname}_{timestamp}.sql")

    logger.info(f"Создание резервной копии базы данных {dbname} в файл {backup_file}")

    # Настройка переменных окружения для pg_dump
    env = os.environ.copy()
    env["PGPASSWORD"] = password

    try:
        # Запуск pg_dump для создания резервной копии
        cmd = [
            "pg_dump",
            "-h", host,
            "-p", str(port),
            "-U", user,
            "-d", dbname,
            "-f", backup_file,
            "--clean",
            "--if-exists"
        ]

        result = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            logger.info(f"Резервная копия успешно создана: {backup_file}")
            cleanup_old_backups()
            return True
        else:
            logger.error(f"Ошибка при создании резервной копии: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Исключение при создании резервной копии: {e}")
        return False


def cleanup_old_backups():
    """Удаляет старые резервные копии, оставляя только MAX_BACKUPS последних"""
    try:
        # Получаем список файлов резервных копий
        backup_files = [
            os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)
            if f.startswith(f"{dbname}_") and f.endswith(".sql")
        ]

        # Сортируем по времени изменения (от старых к новым)
        backup_files.sort(key=lambda x: os.path.getmtime(x))

        # Удаляем старые файлы, если их больше MAX_BACKUPS
        if len(backup_files) > MAX_BACKUPS:
            files_to_delete = backup_files[:-MAX_BACKUPS]
            for file_path in files_to_delete:
                os.remove(file_path)
                logger.info(f"Удалена старая резервная копия: {file_path}")

    except Exception as e:
        logger.error(f"Ошибка при очистке старых резервных копий: {e}")


def restore_backup(backup_file=None):
    """Восстанавливает базу данных из резервной копии"""
    if backup_file is None:
        # Если файл не указан, используем самую свежую резервную копию
        try:
            backup_files = [
                os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)
                if f.startswith(f"{dbname}_") and f.endswith(".sql")
            ]

            if not backup_files:
                logger.error("Резервные копии не найдены")
                return False

            # Сортируем по времени изменения (от старых к новым)
            backup_files.sort(key=lambda x: os.path.getmtime(x))
            backup_file = backup_files[-1]  # Берем самый свежий файл

        except Exception as e:
            logger.error(f"Ошибка при поиске резервных копий: {e}")
            return False

    logger.info(f"Восстановление базы данных {dbname} из файла {backup_file}")

    # Настройка переменных окружения для psql
    env = os.environ.copy()
    env["PGPASSWORD"] = password

    try:
        # Запуск psql для восстановления из резервной копии
        cmd = [
            "psql",
            "-h", host,
            "-p", str(port),
            "-U", user,
            "-d", "postgres",  # Подключаемся к postgres для безопасного восстановления
            "-f", backup_file
        ]

        result = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            logger.info(f"База данных успешно восстановлена из {backup_file}")
            return True
        else:
            logger.error(f"Ошибка при восстановлении базы данных: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Исключение при восстановлении базы данных: {e}")
        return False


if __name__ == "__main__":
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        if sys.argv[1] == "restore":
            # Восстановление из резервной копии
            backup_file = sys.argv[2] if len(sys.argv) > 2 else None
            restore_backup(backup_file)
        elif sys.argv[1] == "backup":
            # Создание резервной копии
            create_backup()
        elif sys.argv[1] == "--daemon":
            # Запуск в режиме демона
            backup_interval = int(os.getenv("BACKUP_INTERVAL", "86400"))  # По умолчанию 24 часа
            logger.info(f"Запуск в режиме демона с интервалом {backup_interval} секунд")

            while True:
                try:
                    create_backup()
                    time.sleep(backup_interval)
                except KeyboardInterrupt:
                    logger.info("Процесс резервного копирования остановлен.")
                    break
                except Exception as e:
                    logger.error(f"Неожиданная ошибка: {e}")
                    time.sleep(300)  # В случае ошибки ждем 5 минут перед следующей попыткой
        else:
            print(f"Неизвестная команда: {sys.argv[1]}")
            print("Использование: python backup_db.py [backup|restore|--daemon] [путь_к_файлу_для_восстановления]")
    else:
        # По умолчанию создаем резервную копию
        create_backup()
