# Question Manager для CLI-Flow

Инструмент для управления вопросами в CLI-Flow через API.

## Возможности

- Добавление вопросов из JSON-файла
- Проверка существующих вопросов перед добавлением
- Кэширование добавленных вопросов для предотвращения дубликатов
- Поддержка разных типов экзаменов (RHCSA, CKA)
- Режим проверки без добавления вопросов

## Требования

- Python 3.6+
- Библиотека requests (`pip install requests`)

### Установка зависимостей

```bash
# Установка из файла requirements.txt
pip install -r requirements.txt

# Или напрямую
pip install requests
```

## Структура JSON-файла с вопросами

```json
[
    {
        "text": "Текст вопроса",
        "difficulty": "easy|medium|hard",
        "category": "Категория вопроса",
        "exam_type": "rhcsa|cka",
        "answers": [
            {"text": "Вариант ответа 1", "is_correct": false},
            {"text": "Вариант ответа 2", "is_correct": true},
            {"text": "Вариант ответа 3", "is_correct": false},
            {"text": "Вариант ответа 4", "is_correct": false}
        ]
    },
    // Другие вопросы...
]
```

## Использование

### Базовое использование

```bash
python add_questions.py -f path/to/questions.json -u admin@example.com -p password -b http://localhost
```

### Проверка вопросов без добавления

```bash
python add_questions.py -f path/to/questions.json -u admin@example.com -p password -b http://localhost -c
```

### Указание типа экзамена для всех вопросов

```bash
python add_questions.py -f path/to/questions.json -u admin@example.com -p password -b http://localhost -e cka
```

## Параметры командной строки

- `-f, --file`: JSON-файл с вопросами (обязательный)
- `-u, --username`: Имя пользователя для авторизации (обязательный)
- `-p, --password`: Пароль для авторизации (обязательный)
- `-b, --base-url`: Базовый URL API (по умолчанию: http://localhost:80)
- `-c, --check`: Проверить вопросы без добавления
- `-e, --exam-type`: Тип экзамена (если не указан в файле): rhcsa или cka

## Примеры

### Добавление вопросов для CKA

```bash
python add_questions.py -f question_templates/cka_questions.json -u admin@admin.admin -p admin -b http://localhost
```

### Проверка вопросов для RHCSA

```bash
python add_questions.py -f question_templates/rhcsa_questions.json -u admin@admin.admin -p admin -b http://localhost -c
```

### Добавление вопросов с указанием типа экзамена

```bash
python add_questions.py -f custom_questions.json -u admin@admin.admin -p admin -b http://localhost -e rhcsa
```

## Шаблоны вопросов

В директории `question_templates` находятся шаблоны JSON-файлов с вопросами:

- `cka_template.json` - шаблон для вопросов CKA
- `rhcsa_template.json` - шаблон для вопросов RHCSA

Используйте эти шаблоны как основу для создания своих файлов с вопросами.

## Кэширование вопросов

Скрипт создает файл `added_questions_cache.json`, в котором хранится информация о добавленных вопросах. Это позволяет избежать повторного добавления одних и тех же вопросов при повторном запуске скрипта.

Если вы хотите принудительно добавить вопросы, даже если они уже существуют, удалите файл `added_questions_cache.json` перед запуском скрипта. 