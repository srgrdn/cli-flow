#!/usr/bin/env python3
"""
Скрипт для тестирования системы логирования.
"""
import logging

from logger import setup_logger

# Инициализация логгера
logger = setup_logger()

if __name__ == "__main__":
    # Тестирование различных уровней логирования
    logger.debug("Это DEBUG сообщение")
    logger.info("Это INFO сообщение")
    logger.warning("Это WARNING сообщение")
    logger.error("Это ERROR сообщение")
    logger.critical("Это CRITICAL сообщение")

    # Тестирование логирования в разных модулях
    auth_logger = logging.getLogger("auth")
    admin_logger = logging.getLogger("admin")

    auth_logger.info("Тестовое сообщение от auth модуля")
    admin_logger.warning("Тестовое предупреждение от admin модуля")

    print("Тестирование логирования завершено. Проверьте файл logs/app.log")
