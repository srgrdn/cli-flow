import logging
import os
from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    Security,
    status,
)
from fastapi.responses import RedirectResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserCreate

# Setup logger
logger = logging.getLogger("auth")

router = APIRouter(prefix="/auth", tags=["authentication"])

# Конфигурация безопасности
SECRET_KEY = os.getenv("SECRET_KEY", "secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 часа вместо 30 минут

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str):
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_access_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    @staticmethod
    def set_auth_cookie(response: Response, token: str):
        """Устанавливает куки с токеном авторизации"""
        # Устанавливаем куки на 24 часа
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,  # Защита от XSS
            max_age=86400,  # 24 часа в секундах
            expires=86400,  # Для совместимости с старыми браузерами
            path="/"
        )
        return response


security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = AuthService.decode_access_token(token)
    if payload is None or "sub" not in payload:
        logger.warning("Invalid authentication attempt with token")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if user is None:
        logger.warning(f"Authentication attempt with valid token but user not found: {payload['sub']}")
        raise HTTPException(status_code=401, detail="User not found")
    logger.info(f"User authenticated: {user.email}")
    return user


@router.post("/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db), request: Request = None):
    client_ip = request.client.host if request else "unknown"

    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"Registration attempt with existing email: {user_data.email} from IP: {client_ip}")
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = AuthService.get_password_hash(user_data.password)
    db_user = User(email=user_data.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()

    logger.info(f"New user registered: {user_data.email} from IP: {client_ip}")
    return {"message": "User created successfully"}


@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None
):
    client_ip = request.client.host if request else "unknown"

    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not AuthService.verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {form_data.username} from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = AuthService.create_access_token(data={"sub": user.email})
    logger.info(f"Successful login: {user.email} from IP: {client_ip}")

    # Устанавливаем токен в куки
    AuthService.set_auth_cookie(response, access_token)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/check-admin")
async def check_admin_rights(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    """Проверка прав администратора"""
    token = credentials.credentials
    payload = AuthService.decode_access_token(token)

    if not payload or "sub" not in payload:
        logger.warning("Admin check with invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        logger.warning(f"Admin check for non-existent user: {payload['sub']}")
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_superuser:
        logger.warning(f"Admin access attempt by non-admin user: {user.email}")
        raise HTTPException(status_code=403, detail="Not an admin")

    logger.info(f"Admin access granted to: {user.email}")
    return {"is_admin": True}


@router.get("/logout")
async def logout():
    """Выход из системы"""
    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token", path="/")
    logger.info("User logged out")
    return response
