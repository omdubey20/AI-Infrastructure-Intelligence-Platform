from datetime import datetime, timedelta
import os

import bcrypt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
except Exception:
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()

import models
import schemas
from database import get_db

load_dotenv()

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

# =========================
# JWT CONFIG
# =========================

SECRET_KEY = os.getenv("SECRET_KEY", "cWfTKKTNDUNou3R-W_Dv-Haz-GSWZMHFD9O-h_ASwtL2WBPWe4XWtj_o7--1-wuCFymyMdF-Qg67GYztmQUhYQ")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

# =========================
# PASSWORD HELPERS
# =========================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

# =========================
# JWT HELPERS
# =========================

def create_access_token(data: dict) -> str:
    payload = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload.update({"exp": expire})

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

# =========================
# CURRENT USER
# =========================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = (
        db.query(models.User)
        .filter(
            models.User.username == username
        )
        .first()
    )

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user

# =========================
# ROLE CHECKER
# =========================

def require_role(allowed_roles: list):
    def role_checker(
        current_user=Depends(get_current_user)
    ):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )

        return current_user

    return role_checker

# =========================
# REGISTER (admin-only after first user)
# =========================

@router.post(
    "/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("5/minute")
def register(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    # First user can self-register (bootstrap); after that, admin-only
    user_count = db.query(models.User).count()
    if user_count > 0:
        # Require admin auth for subsequent registrations
        try:
            current_user = get_current_user(
                token=request.headers.get("Authorization", "").replace("Bearer ", ""),
                db=db
            )
            if current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can register new users"
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin authentication required to register new users"
            )

    existing_user = (
        db.query(models.User)
        .filter(
            models.User.username == user.username
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    # First user gets admin role, subsequent users get viewer
    role = "admin" if user_count == 0 else "viewer"

    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(
            user.password
        ),
        is_active=True,
        role=role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

# =========================
# LOGIN
# =========================

@router.post(
    "/login",
    response_model=schemas.Token
)
@router.post(
    "/auth/login",
    response_model=schemas.Token
)
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = (
        db.query(models.User)
        .filter(
            models.User.username == form_data.username
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if not verify_password(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    access_token = create_access_token(
        {
            "sub": user.username,
            "id": user.id,
            "role": user.role
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# =========================
# CURRENT USER INFO
# =========================

@router.get(
    "/me",
    response_model=schemas.UserOut
)
def get_me(
    current_user=Depends(
        get_current_user
    )
):
    return current_user