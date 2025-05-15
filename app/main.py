from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db, engine
from models import Base, Question, Answer
from schemas import QuestionCreate, QuestionResponse
from routers import questions, auth

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RHCSA Testing Service")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настраиваем шаблоны
templates = Jinja2Templates(directory="templates")

# Подключаем роутеры
app.include_router(questions.router)
app.include_router(auth.router)


@app.get("/")
async def home(request: Request):
    """Главная страница приложения"""
    return templates.TemplateResponse("index.html", {"request": request, "title": "RHCSA Testing Service"})


@app.get("/login")
async def login_page(request: Request):
    """Страница входа в систему"""
    return templates.TemplateResponse("login.html", {"request": request, "title": "Вход в систему"})


@app.get("/register")
async def register_page(request: Request):
    """Страница регистрации"""
    return templates.TemplateResponse("register.html", {"request": request, "title": "Регистрация"})


@app.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    return {"status": "ok"}
