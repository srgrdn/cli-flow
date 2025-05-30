import sys
import logging
from sqlalchemy import create_engine, text

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database():
    """
    Добавляет столбец exam_type в таблицу questions, если его не существует
    """
    try:
        # Подключение к базе данных
        # Используем правильное имя базы данных
        engine = create_engine("postgresql://postgres:postgres@db:5432/rhcsa_db")
        conn = engine.connect()
        
        # Проверяем, существует ли уже столбец exam_type
        check_query = text("SELECT column_name FROM information_schema.columns WHERE table_name='questions' AND column_name='exam_type'")
        result = conn.execute(check_query)
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            # Добавляем столбец exam_type с значением по умолчанию 'rhcsa'
            alter_query = text("ALTER TABLE questions ADD COLUMN exam_type VARCHAR(20) NOT NULL DEFAULT 'rhcsa'")
            conn.execute(alter_query)
            conn.commit()
            logger.info("Столбец exam_type успешно добавлен в таблицу questions")
        else:
            logger.info("Столбец exam_type уже существует в таблице questions")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении базы данных: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Начало обновления структуры базы данных")
    success = update_database()
    if success:
        logger.info("Обновление базы данных завершено успешно")
    else:
        logger.error("Обновление базы данных завершилось с ошибкой")
        sys.exit(1) 