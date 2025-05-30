import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import engine
from logger import setup_logger
from models import Base
from routers import admin, auth, questions, theory
from routers.auth import AuthService

# Setup logging
logger = setup_logger()

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CLI-Flow")

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


# Middleware для проверки авторизации
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Список публичных путей, не требующих авторизации
    public_paths = [
        "/login",
        "/register",
        "/auth/login",
        "/auth/register",
        "/static",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/theory"
    ]

    # Проверяем, является ли текущий путь публичным
    current_path = request.url.path
    is_public_path = False
    for path in public_paths:
        if current_path == path or current_path.startswith(path + "/"):
            is_public_path = True
            break

    # Если путь публичный, пропускаем проверку
    if is_public_path:
        return await call_next(request)

    # Проверяем наличие токена авторизации
    auth_token = request.cookies.get("access_token")
    if not auth_token:
        logger.warning(f"Unauthorized access attempt to {current_path} from {request.client.host}")
        return RedirectResponse(url="/login")

    # Проверяем валидность токена
    payload = AuthService.decode_access_token(auth_token)
    if not payload or "sub" not in payload:
        logger.warning(f"Invalid token access attempt to {current_path} from {request.client.host}")
        response = RedirectResponse(url="/login")
        response.delete_cookie(key="access_token")
        return response

    # Если всё в порядке, продолжаем обработку запроса
    return await call_next(request)


# Подключаем роутеры
app.include_router(questions.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(theory.router)


@app.get("/")
async def home(request: Request):
    """Главная страница приложения"""
    # Проверяем, авторизован ли пользователь
    user = None
    auth_token = request.cookies.get("access_token")

    if auth_token:
        payload = AuthService.decode_access_token(auth_token)
        if payload and "sub" in payload:
            # Передаем email пользователя в шаблон
            user = {"email": payload["sub"]}

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "CLI-Flow",
            "user": user
        }
    )


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
