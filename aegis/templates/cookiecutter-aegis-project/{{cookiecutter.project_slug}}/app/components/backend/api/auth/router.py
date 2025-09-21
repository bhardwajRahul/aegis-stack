"""Authentication API routes."""

from app.components.backend.api.deps import get_async_db
from app.core.security import create_access_token, verify_password
from app.models.user import UserCreate, UserResponse
from app.services.auth.auth_service import get_current_user_from_token
from app.services.auth.user_service import AsyncUserService
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/auth", tags=["authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """Register a new user."""
    user_service = AsyncUserService(db)

    # Check if user already exists
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    user = await user_service.create_user(user_data)
    return UserResponse.model_validate(user)


@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db),
):
    """Login and get access token."""
    user_service = AsyncUserService(db)

    # Get user by email (username field in OAuth2 form)
    user = await user_service.get_user_by_email(form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db),
):
    """Get current authenticated user."""
    user = await get_current_user_from_token(token, db)
    return UserResponse.model_validate(user)
