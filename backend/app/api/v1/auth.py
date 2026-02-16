"""Authentication API endpoints."""

import hashlib
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.crud.user import organization_crud, refresh_token_crud, user_crud
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import User as UserSchema
from app.services.rate_limit_service import get_rate_limit_service
from app.services.password_validation_service import password_validation_service

router = APIRouter()
logger = logging.getLogger(__name__)
rate_limit_service = get_rate_limit_service()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user and organization.

    Creates both an organization and the first user (admin) in a single transaction.
    Rate limited to 3 registrations per 10 minutes per IP to prevent abuse.
    """
    # Rate limit: 3 registration attempts per 10 minutes per IP
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=3,
        window_seconds=600,  # 10 minutes
    )

    # Validate password strength and check for breaches
    await password_validation_service.validate_and_raise_async(data.password, check_breach=True)

    # Check if user already exists
    existing_user = await user_crud.get_by_email(db, data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create organization
    organization = await organization_crud.create(
        db=db,
        name=data.organization_name,
    )

    # Create user (first user is org admin)
    user = await user_crud.create(
        db=db,
        email=data.email,
        password=data.password,
        organization_id=organization.id,
        first_name=data.first_name,
        last_name=data.last_name,
        is_org_admin=True,  # First user is always org admin
    )

    # Update last login
    await user_crud.update_last_login(db, user.id)

    # Generate tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    refresh_token_str, jti, expires_at = create_refresh_token(str(user.id))

    # Store refresh token hash
    token_hash = hashlib.sha256(jti.encode()).hexdigest()
    await refresh_token_crud.create(
        db=db,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        user=UserSchema.from_orm(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password.

    Returns access and refresh tokens.
    Rate limited to 5 attempts per minute per IP to prevent brute force attacks.
    """
    # Rate limit: 5 login attempts per minute per IP
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=5,
        window_seconds=60,
    )

    logger.info(f"Login attempt for email: {data.email}")

    try:
        # Get user by email
        user = await user_crud.get_by_email(db, data.email)
        if not user:
            logger.warning(f"Login failed: User not found - {data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Check if account is locked (backward compatible - fields may not exist yet)
        locked_until = getattr(user, 'locked_until', None)
        if locked_until and locked_until > datetime.utcnow():
            minutes_remaining = int((locked_until - datetime.utcnow()).total_seconds() / 60)
            logger.warning(f"Login failed: Account locked - {data.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is locked due to too many failed login attempts. Try again in {minutes_remaining} minutes.",
            )

        # If lockout period has expired, reset failed attempts
        if locked_until and locked_until <= datetime.utcnow():
            if hasattr(user, 'failed_login_attempts'):
                user.failed_login_attempts = 0
                user.locked_until = None
                await db.commit()

        logger.info(f"User found: {user.email}, verifying password...")

        # Verify password
        if not verify_password(data.password, user.password_hash):
            logger.warning(f"Login failed: Incorrect password for {data.email}")

            # Increment failed login attempts (if field exists)
            if hasattr(user, 'failed_login_attempts'):
                user.failed_login_attempts += 1

                # Lock account if too many failed attempts (5 failures = 30 min lockout)
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                    await db.commit()
                    logger.warning(f"Account locked for 30 minutes: {data.email}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account locked due to too many failed login attempts. Try again in 30 minutes.",
                    )

                await db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        logger.info(f"Password verified for {user.email}")

        # Reset failed login attempts on successful login (if fields exist)
        if hasattr(user, 'failed_login_attempts'):
            user.failed_login_attempts = 0
            user.locked_until = None

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login failed: Inactive account - {data.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        logger.info(f"Updating last login for {user.email}")

        # Update last login
        await user_crud.update_last_login(db, user.id)

        logger.info(f"Generating tokens for {user.email}")

        # Generate tokens
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
            }
        )
        refresh_token_str, jti, expires_at = create_refresh_token(str(user.id))

        # Store refresh token hash
        token_hash = hashlib.sha256(jti.encode()).hexdigest()
        await refresh_token_crud.create(
            db=db,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        logger.info(f"Login successful for {user.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            user=UserSchema.from_orm(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {data.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(
    request: Request,
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    Rate limited to 10 refreshes per minute to prevent abuse.
    """
    # Rate limit: 10 refresh attempts per minute per IP
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=10,
        window_seconds=60,
    )

    try:
        # Decode refresh token
        payload = decode_token(data.refresh_token)

        # Check token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # Get JTI and user ID
        jti = payload.get("jti")
        user_id_str = payload.get("sub")

        if not jti or not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Check if token is in database and not revoked
        token_hash = hashlib.sha256(jti.encode()).hexdigest()
        refresh_token = await refresh_token_crud.get_by_token_hash(db, token_hash)

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not found",
            )

        if refresh_token.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        if refresh_token.is_expired:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )

        # Get user
        user = await user_crud.get_by_id(db, refresh_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Generate new access token
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
            }
        )

        return AccessTokenResponse(access_token=access_token)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token",
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Logout by revoking the refresh token.
    """
    try:
        # Decode refresh token to get JTI
        payload = decode_token(data.refresh_token)
        jti = payload.get("jti")

        if jti:
            # Revoke token
            token_hash = hashlib.sha256(jti.encode()).hexdigest()
            await refresh_token_crud.revoke(db, token_hash)

    except Exception:
        # If token is invalid, that's fine - just return success
        pass

    return None


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information.
    """
    return UserSchema.from_orm(current_user)
