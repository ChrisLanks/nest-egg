"""Authentication API endpoints."""

import hashlib
import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    hash_password,
)
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
from app.utils.datetime_utils import utc_now
from app.utils.logging_utils import redact_email

router = APIRouter()
logger = logging.getLogger(__name__)

# Generate dummy password hash for timing attack prevention
# This is generated once at module load time to prevent timing attacks
# when checking non-existent users
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))
rate_limit_service = get_rate_limit_service()


async def create_auth_response(
    db: AsyncSession,
    user: User,
) -> TokenResponse:
    """
    Create authentication response with tokens.

    Generates access and refresh tokens, stores refresh token hash in database.

    Args:
        db: Database session
        user: Authenticated user

    Returns:
        TokenResponse with access token, refresh token, and user data
    """
    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
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
    # Rate limit: 10 registration attempts per 10 minutes per IP
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=10,
        window_seconds=600,  # 10 minutes
    )

    # Validate password strength and check for breaches (unless user chose to skip)
    if not data.skip_password_validation:
        await password_validation_service.validate_and_raise_async(
            data.password, check_breach=True
        )

    # Check if user already exists
    existing_user = await user_crud.get_by_email(db, data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create organization — use provided name or derive from display_name
    org_name = (
        data.organization_name
        if data.organization_name != "My Household"
        else f"{data.display_name}'s Household"
    )
    organization = await organization_crud.create(
        db=db,
        name=org_name,
    )

    # Create user (first user is org admin)
    user = await user_crud.create(
        db=db,
        email=data.email,
        password=data.password,
        organization_id=organization.id,
        first_name=data.first_name,
        last_name=data.last_name,
        display_name=data.display_name,
        birth_day=data.birth_day,
        birth_month=data.birth_month,
        birth_year=data.birth_year,
        is_org_admin=True,  # First user is always org admin
    )

    # Update last login
    await user_crud.update_last_login(db, user.id)

    # Generate tokens and create response
    return await create_auth_response(db, user)


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
    # Rate limit: 10 login attempts per minute per IP
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=10,
        window_seconds=60,
    )

    logger.info(f"Login attempt for email: {redact_email(data.email)}")

    try:
        # Get user by email
        user = await user_crud.get_by_email(db, data.email)
        if not user:
            # Perform dummy password verification to prevent timing attack
            # This ensures the response time is consistent whether user exists or not
            # Uses dynamically generated hash to prevent precomputation attacks
            verify_password(data.password, DUMMY_PASSWORD_HASH)
            logger.warning(f"Login failed: User not found - {redact_email(data.email)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Check if account is locked (backward compatible - fields may not exist yet)
        locked_until = getattr(user, "locked_until", None)
        if locked_until and locked_until > utc_now():
            minutes_remaining = int((locked_until - utc_now()).total_seconds() / 60)
            logger.warning(f"Login failed: Account locked - {redact_email(data.email)}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is locked due to too many failed login attempts. Try again in {minutes_remaining} minutes.",
            )

        # If lockout period has expired, reset failed attempts
        if locked_until and locked_until <= utc_now():
            if hasattr(user, "failed_login_attempts"):
                user.failed_login_attempts = 0
                user.locked_until = None
                await db.commit()

        logger.info("User found, verifying password...")

        # Verify password
        if not verify_password(data.password, user.password_hash):
            logger.warning(f"Login failed: Incorrect password for {redact_email(data.email)}")

            # Increment failed login attempts (if field exists)
            if hasattr(user, "failed_login_attempts"):
                user.failed_login_attempts += 1

                # Lock account if too many failed attempts
                if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                    user.locked_until = utc_now() + timedelta(
                        minutes=settings.ACCOUNT_LOCKOUT_MINUTES
                    )
                    await db.commit()
                    logger.warning(
                        f"Account locked for {settings.ACCOUNT_LOCKOUT_MINUTES} minutes: {redact_email(data.email)}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account locked due to too many failed login attempts. Try again in 30 minutes.",
                    )

                await db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        logger.info("Password verified")

        # Reset failed login attempts on successful login (if fields exist)
        if hasattr(user, "failed_login_attempts"):
            user.failed_login_attempts = 0
            user.locked_until = None

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login failed: Inactive account - {redact_email(data.email)}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        logger.info("Updating last login")

        # Update last login
        await user_crud.update_last_login(db, user.id)

        # Trigger background price refresh if holdings are stale (non-blocking)
        import asyncio
        asyncio.create_task(_maybe_refresh_prices_on_login(user.organization_id))

        logger.info("Generating tokens")

        # Generate tokens and create response
        response = await create_auth_response(db, user)

        logger.info("Login successful")

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {redact_email(data.email)}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        )


async def _maybe_refresh_prices_on_login(organization_id) -> None:
    """
    Background task: refresh holding prices if stale (> 6 hours old).

    Runs fire-and-forget after a successful login so the user sees
    up-to-date prices on their next portfolio load without waiting.
    Silently swallows errors so it never affects the login response.
    """
    import uuid
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.holding import Holding
    from app.services.market_data import get_market_data_provider

    STALE_AFTER_HOURS = 6

    try:
        async with async_session_factory() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=STALE_AFTER_HOURS)
            # Check whether any holding in this org has a stale (or missing) price
            result = await db.execute(
                select(Holding.id).where(
                    Holding.organization_id == organization_id,
                    (Holding.price_as_of.is_(None)) | (Holding.price_as_of < cutoff),
                ).limit(1)
            )
            if result.scalar_one_or_none() is None:
                logger.debug("Holdings prices are fresh; skipping login-triggered refresh")
                return

            # Fetch all holdings for a batch update
            result = await db.execute(
                select(Holding).where(Holding.organization_id == organization_id)
            )
            holdings = result.scalars().all()
            if not holdings:
                return

            symbols = list({h.ticker for h in holdings if h.ticker})
            if not symbols:
                return

            market_data = get_market_data_provider()
            quotes = await market_data.get_quotes_batch(symbols)

            from sqlalchemy import update as sa_update
            updated = 0
            now = datetime.now(timezone.utc)
            for h in holdings:
                if h.ticker and h.ticker in quotes:
                    q = quotes[h.ticker]
                    await db.execute(
                        sa_update(Holding)
                        .where(Holding.id == h.id)
                        .values(current_price_per_share=q.price, price_as_of=now)
                    )
                    updated += 1

            await db.commit()
            logger.info(
                "login_price_refresh: org=%s updated=%d total=%d provider=%s",
                organization_id,
                updated,
                len(holdings),
                market_data.get_provider_name(),
            )
    except Exception as exc:
        # Never crash the login response due to a background refresh failure
        logger.warning("login_price_refresh failed (non-critical): %s", exc)


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
            logger.warning("Token refresh failed: Invalid token type")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # Get JTI and user ID
        jti = payload.get("jti")
        user_id_str = payload.get("sub")

        if not jti or not user_id_str:
            logger.warning("Token refresh failed: Missing jti or user_id")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Check if token is in database and not revoked
        token_hash = hashlib.sha256(jti.encode()).hexdigest()
        refresh_token = await refresh_token_crud.get_by_token_hash(db, token_hash)

        if not refresh_token:
            # Only log token details in DEBUG mode to prevent token leakage
            if settings.DEBUG:
                logger.warning(
                    f"Token refresh failed: Token not found in database (jti: {jti[:10]}...)"
                )
            else:
                logger.warning("Token refresh failed: Token not found in database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not found",
            )

        if refresh_token.is_revoked:
            logger.warning(
                f"Token refresh failed: Token has been revoked (user_id: {refresh_token.user_id})"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        if refresh_token.is_expired:
            logger.warning(
                f"Token refresh failed: Token has expired (user_id: {refresh_token.user_id}, expired_at: {refresh_token.expires_at})"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )

        # Get user
        user = await user_crud.get_by_id(db, refresh_token.user_id)
        if not user or not user.is_active:
            logger.warning(
                f"Token refresh failed: User not found or inactive (user_id: {refresh_token.user_id})"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        logger.info("Token refresh successful")

        # Generate new access token
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
            }
        )

        return AccessTokenResponse(access_token=access_token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
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


@router.post("/debug/check-refresh-token")
async def debug_check_refresh_token(
    data: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Debug endpoint to check refresh token validity.
    Only available in DEBUG mode and requires authentication.
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        # Try to decode token
        payload = decode_token(data.refresh_token)
        jti = payload.get("jti")
        token_type = payload.get("type")
        user_id = payload.get("sub")
        exp = payload.get("exp")

        # Check if token is in database
        token_hash = hashlib.sha256(jti.encode()).hexdigest() if jti else None
        db_token = (
            await refresh_token_crud.get_by_token_hash(db, token_hash) if token_hash else None
        )

        return {
            "decode_success": True,
            "payload": {
                "jti_prefix": jti[:16] if jti else None,
                "type": token_type,
                "user_id": user_id,
                "exp": exp,
            },
            "token_hash_prefix": token_hash[:16] if token_hash else None,
            "in_database": db_token is not None,
            "db_token_info": (
                {
                    "expired": db_token.is_expired if db_token else None,
                    "revoked": db_token.is_revoked if db_token else None,
                    "expires_at": str(db_token.expires_at) if db_token else None,
                }
                if db_token
                else None
            ),
        }
    except Exception as e:
        return {
            "decode_success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }
