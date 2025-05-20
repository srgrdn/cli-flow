import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import engine
from logger import setup_logger
from models import Base
from routers import admin, auth, questions

# Setup logging
logger = setup_logger()

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RHCSA Testing Service")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настраиваем шаблоны
templates = Jinja2Templates(directory="templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Get client IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = forwarded_for.split(",")[0] if forwarded_for else request.client.host

    # Log request details
    logger.info(
        f"Request started: {request.method} {request.url.path} from {client_ip}"
    )

    response = await call_next(request)

    # Calculate request processing time
    process_time = time.time() - start_time

    # Log response details
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"status={response.status_code} duration={process_time:.3f}s"
    )

    return response

# Подключаем роутеры
app.include_router(questions.router)
app.include_router(auth.router)
app.include_router(admin.router)


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
