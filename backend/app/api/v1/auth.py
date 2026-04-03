"""Authentication API endpoints."""

import asyncio
import hashlib
import logging
import secrets
from datetime import timedelta

import jwt
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import (
    create_access_token,
    create_mfa_pending_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.crud.user import organization_crud, refresh_token_crud, user_crud
from app.dependencies import get_current_user
from app.models.holding import Holding
from app.models.mfa import UserMFA
from app.models.transaction import Category
from app.models.user import (
    ConsentType,
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserConsent,
)
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import User as UserSchema
from app.services.email_service import (
    create_password_reset_token,
    create_verification_token,
    email_service,
    hash_token,
)
from app.services.input_sanitization_service import input_sanitization_service
from app.services.market_data import get_market_data_provider
from app.services.market_data.cache import invalidate_quotes
from app.services.mfa_service import mfa_service
from app.services.password_validation_service import password_validation_service
from app.services.rate_limit_service import get_rate_limit_service
from app.utils.datetime_utils import utc_now

# Module-level set holding references to fire-and-forget background tasks.
# asyncio only keeps weak references to tasks; without a strong reference the
# GC can cancel a task before it finishes.  Tasks remove themselves via the
# done-callback once complete.
_background_tasks: set[asyncio.Task] = set()


class AuthMessageResponse(BaseModel):
    message: str


class MFAChallengeResponse(BaseModel):
    """Response returned when MFA verification is required before completing login."""

    mfa_required: bool = True
    mfa_token: str  # Short-lived JWT (5 min) with type="mfa_pending"


class MFAVerifyRequest(BaseModel):
    """Request body to complete MFA login challenge."""

    mfa_token: str
    code: str  # 6-digit TOTP code or XXXX-XXXX backup code


router = APIRouter()
logger = logging.getLogger(__name__)

# Generate dummy password hash for timing attack prevention
# This is generated once at module load time to prevent timing attacks
# when checking non-existent users
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))
rate_limit_service = get_rate_limit_service()


_REFRESH_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


def _set_refresh_cookie(response: Response, refresh_token_str: str) -> None:
    """Set the refresh token as an httpOnly cookie on the response."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",  # HTTPS-only in production
        samesite="lax",  # lax works across same-host different ports in dev
        max_age=_REFRESH_COOKIE_MAX_AGE,
        path="/api/v1/auth",  # Scope cookie to auth endpoints only
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie (on logout or invalid token)."""
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")


async def create_auth_response(
    db: AsyncSession,
    user: User,
    response: Response | None = None,
) -> TokenResponse:
    """
    Create authentication response with tokens.

    Generates access and refresh tokens, stores refresh token hash in database.
    When a FastAPI Response object is provided, the refresh token is delivered as
    an httpOnly cookie instead of in the response body.

    Args:
        db: Database session
        user: Authenticated user
        response: Optional FastAPI Response for setting httpOnly cookie

    Returns:
        TokenResponse with access token and user data (refresh_token omitted from body)
    """
    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token_str, jti, expires_at = create_refresh_token(str(user.id))

    # Store refresh token hash
    token_hash = hashlib.sha256(jti.encode()).hexdigest()
    await refresh_token_crud.create(
        db=db,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    # Record JTI in Redis for O(1) revocation checks on /refresh (prod only)
    if settings.ENFORCE_JTI_REDIS_CHECK:
        from app.core.jti_store import store_jti

        await store_jti(jti, str(user.id), _REFRESH_COOKIE_MAX_AGE)

    if response is not None:
        # Deliver refresh token as httpOnly cookie — not readable by JavaScript
        _set_refresh_cookie(response, refresh_token_str)
        return TokenResponse(
            access_token=access_token,
            refresh_token=None,
            user=UserSchema.from_orm(user),
        )

    # Fallback: include refresh token in body (used by tests / non-browser clients)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        user=UserSchema.from_orm(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    response: Response,
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

    # Always validate password strength and check for breaches
    await password_validation_service.validate_and_raise_async(data.password, check_breach=True)

    # Check if user already exists — return identical-shaped response to prevent
    # enumeration.  The response body MUST have the same keys as a real
    # registration so that an attacker cannot distinguish the two.
    existing_user = await user_crud.get_by_email(db, data.email)
    if existing_user:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "access_token": None,
                "refresh_token": None,
                "user": None,
                "message": "Registration successful."
                " Please check your email to verify your account.",
            },
        )

    # Create organization — use provided name or derive from display_name
    raw_org_name = (
        data.organization_name
        if data.organization_name != "My Household"
        else f"{data.display_name}'s Household"
    )
    org_name = input_sanitization_service.sanitize_html(raw_org_name)
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

    # Record consent (GDPR / CCPA compliance)
    client_ip = request.client.host if request.client else None
    for consent_type in (ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY):
        db.add(
            UserConsent(
                user_id=user.id,
                consent_type=consent_type.value,
                version=settings.TERMS_VERSION,
                ip_address=client_ip,
            )
        )
    await db.flush()

    # Seed default categories for the new organization
    _default_categories = [
        {"name": "Housing", "color": "#EF5350"},
        {"name": "Groceries", "color": "#66BB6A"},
        {"name": "Dining", "color": "#FFA726"},
        {"name": "Transportation", "color": "#42A5F5"},
        {"name": "Utilities", "color": "#AB47BC"},
        {"name": "Entertainment", "color": "#EC407A"},
        {"name": "Healthcare", "color": "#26A69A"},
        {"name": "Shopping", "color": "#26C6DA"},
    ]
    for _cat in _default_categories:
        db.add(
            Category(
                organization_id=organization.id,
                name=_cat["name"],
                color=_cat["color"],
            )
        )

    # Update last login
    await user_crud.update_last_login(db, user.id)

    # Send email verification (non-blocking — failure doesn't prevent registration)
    try:
        raw_token = await create_verification_token(db, user.id)
        await email_service.send_verification_email(
            to_email=user.email,
            token=raw_token,
            display_name=user.display_name or user.first_name or user.email,
        )
    except Exception:
        logger.warning("Failed to create/send verification token after registration", exc_info=True)

    # Generate tokens and create response (refresh token set as httpOnly cookie)
    return await create_auth_response(db, user, response)


@router.post("/login", response_model=None)
async def login(
    request: Request,
    response: Response,
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

    logger.info("Login attempt")

    try:
        # Get user by email
        user = await user_crud.get_by_email(db, data.email)
        if not user:
            # Perform dummy password verification to prevent timing attack
            # This ensures the response time is consistent whether user exists or not
            # Uses dynamically generated hash to prevent precomputation attacks
            verify_password(data.password, DUMMY_PASSWORD_HASH)
            logger.warning("Login failed: User not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Account lockout — controlled by ENFORCE_ACCOUNT_LOCKOUT flag
        # (auto-disabled in development, enabled in staging/production).
        if not settings.ENFORCE_ACCOUNT_LOCKOUT:
            logger.debug("Account lockout disabled (ENFORCE_ACCOUNT_LOCKOUT=false)")
        else:
            locked_until = getattr(user, "locked_until", None)
            if locked_until and locked_until > utc_now():
                minutes_remaining = max(1, int((locked_until - utc_now()).total_seconds() / 60))
                logger.warning("Login failed: Account locked for user=%s", user.id)
                raise HTTPException(
                    status_code=423,
                    detail=(
                        "Account is locked due to too many failed login attempts."
                        f" Try again in {minutes_remaining} minutes."
                    ),
                )

            # If lockout period has expired, reset failed attempts atomically.
            # Using a single UPDATE avoids a TOCTOU race where two concurrent
            # login requests both see the expired lock and both proceed past it
            # before either can commit the reset.
            if locked_until and locked_until <= utc_now():
                await db.execute(
                    sa_update(User)
                    .where(User.id == user.id)
                    .values(failed_login_attempts=0, locked_until=None)
                )
                await db.commit()
                await db.refresh(user)

        logger.info("User found, verifying password...")

        # Verify password
        if not verify_password(data.password, user.password_hash):
            logger.warning("Login failed: Incorrect password for user=%s", user.id)

            # Increment failed login attempts and lock if threshold reached
            if settings.ENFORCE_ACCOUNT_LOCKOUT and hasattr(user, "failed_login_attempts"):
                user.failed_login_attempts += 1

                # Lock account if too many failed attempts
                if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                    user.locked_until = utc_now() + timedelta(
                        minutes=settings.ACCOUNT_LOCKOUT_MINUTES
                    )
                    await db.commit()
                    lockout_min = settings.ACCOUNT_LOCKOUT_MINUTES
                    logger.warning("Account locked for %d minutes: user=%s", lockout_min, user.id)
                    raise HTTPException(
                        status_code=423,
                        detail=(
                            "Account locked due to too many failed attempts."
                            f" Try again in {lockout_min} minutes."
                        ),
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
            logger.warning("Login failed: Inactive account for user=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        # MFA enforcement — controlled by ENFORCE_MFA flag
        # (auto-disabled in development, enabled in staging/production).
        if not settings.ENFORCE_MFA:
            logger.debug("MFA enforcement disabled (ENFORCE_MFA=false)")
        else:
            mfa_result = await db.execute(select(UserMFA).where(UserMFA.user_id == user.id))
            user_mfa = mfa_result.scalar_one_or_none()
            if user_mfa and user_mfa.is_enabled and user_mfa.is_verified:
                mfa_token = create_mfa_pending_token(
                    user_id=str(user.id),
                    expires_delta=timedelta(minutes=5),
                )
                return MFAChallengeResponse(mfa_token=mfa_token)

        logger.info("Updating last login")

        # Update last login
        await user_crud.update_last_login(db, user.id)

        # Trigger background price refresh if holdings are stale (non-blocking).
        # Store the task reference to prevent the GC from cancelling it mid-flight.
        _task = asyncio.create_task(_maybe_refresh_prices_on_login(user.organization_id))
        _background_tasks.add(_task)
        _task.add_done_callback(_background_tasks.discard)

        # Trigger net worth snapshot capture if last snapshot is older than 24h (non-blocking).
        _snap_task = asyncio.create_task(_maybe_capture_snapshot_on_login(user.organization_id))
        _background_tasks.add(_snap_task)
        _snap_task.add_done_callback(_background_tasks.discard)

        logger.info("Generating tokens")

        # Generate tokens and create response (refresh token set as httpOnly cookie)
        auth_response = await create_auth_response(db, user, response)

        logger.info("Login successful")

        return auth_response
    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.error("Database error during login", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        )
    except Exception as e:
        logger.error("Login error: %s", str(e), exc_info=True)
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
    STALE_AFTER_HOURS = 6

    try:
        async with AsyncSessionLocal() as db:
            cutoff = utc_now() - timedelta(hours=STALE_AFTER_HOURS)
            # Check whether any holding in this org has a stale (or missing) price
            result = await db.execute(
                select(Holding.id)
                .where(
                    Holding.organization_id == organization_id,
                    (Holding.price_as_of.is_(None)) | (Holding.price_as_of < cutoff),
                )
                .limit(1)
            )
            if result.scalar_one_or_none() is None:
                logger.debug("Holdings prices are fresh; skipping login-triggered refresh")
                return

            # Fetch only stale holdings — no need to re-fetch fresh prices
            result = await db.execute(
                select(Holding).where(
                    Holding.organization_id == organization_id,
                    (Holding.price_as_of.is_(None)) | (Holding.price_as_of < cutoff),
                )
            )
            stale_holdings = result.scalars().all()
            if not stale_holdings:
                return

            symbols = list({h.ticker for h in stale_holdings if h.ticker})
            if not symbols:
                return

            market_data = get_market_data_provider()
            quotes = await market_data.get_quotes_batch(symbols)

            # Batch UPDATE per ticker (not per holding) for efficiency
            updated = 0
            now = utc_now()
            for ticker in symbols:
                if ticker in quotes:
                    q = quotes[ticker]
                    result = await db.execute(
                        sa_update(Holding)
                        .where(
                            Holding.organization_id == organization_id,
                            Holding.ticker == ticker,
                        )
                        .values(current_price_per_share=q.price, price_as_of=now)
                    )
                    updated += result.rowcount

            await db.commit()
            # Invalidate cached quotes so dashboard sees fresh prices immediately
            await invalidate_quotes(*symbols)
            logger.info(
                "login_price_refresh: org=%s updated=%d stale=%d provider=%s",
                organization_id,
                updated,
                len(stale_holdings),
                market_data.get_provider_name(),
            )
    except Exception as exc:
        # Never crash the login response due to a background refresh failure
        logger.warning("login_price_refresh failed (non-critical): %s", exc)


async def _maybe_capture_snapshot_on_login(organization_id) -> None:
    """
    Background task: dispatch a net worth snapshot Celery task if the most
    recent snapshot for this org is older than 24 hours.

    Uses a small random jitter (0–300 s) so that a burst of logins from the
    same household doesn't fan out into simultaneous snapshot captures.
    Silently swallows errors so it never affects the login response.
    """
    import random

    from sqlalchemy import desc

    from app.models.net_worth_snapshot import NetWorthSnapshot
    from app.workers.tasks.snapshot_tasks import capture_org_portfolio_snapshot

    STALE_AFTER_HOURS = 24
    MAX_JITTER_SECONDS = 300

    try:
        async with AsyncSessionLocal() as db:
            cutoff = utc_now() - timedelta(hours=STALE_AFTER_HOURS)
            result = await db.execute(
                select(NetWorthSnapshot.snapshot_date)
                .where(
                    NetWorthSnapshot.organization_id == organization_id,
                    NetWorthSnapshot.user_id.is_(None),
                )
                .order_by(desc(NetWorthSnapshot.snapshot_date))
                .limit(1)
            )
            latest_date = result.scalar_one_or_none()

        # snapshot_date is a plain date; compare against cutoff date to avoid tz issues
        if latest_date is not None:
            if latest_date >= cutoff.date():
                logger.debug(
                    "login_snapshot_check: org=%s snapshot is fresh (%s), skipping",
                    organization_id,
                    latest_date,
                )
                return

        jitter = random.randint(0, MAX_JITTER_SECONDS)
        logger.info(
            "login_snapshot_check: org=%s snapshot stale/missing, scheduling capture with %ds jitter",
            organization_id,
            jitter,
        )
        capture_org_portfolio_snapshot.apply_async(
            args=[str(organization_id)],
            countdown=jitter,
        )
    except Exception as exc:
        # Never crash the login response due to a background snapshot failure
        logger.warning("login_snapshot_check failed (non-critical): %s", exc)


async def _verify_and_consume_backup_code(
    db: AsyncSession,
    user_mfa: UserMFA,
    code: str,
) -> bool:
    """Verify a backup code and mark it used (removes the code so it cannot be reused)."""
    if not user_mfa.backup_codes:
        return False
    try:
        stored_hashes = mfa_service.decrypt_backup_codes(user_mfa.backup_codes)
    except Exception:
        return False

    for i, hashed_code in enumerate(stored_hashes):
        if hashed_code and mfa_service.verify_backup_code(code, hashed_code):
            stored_hashes[i] = ""
            remaining = [c for c in stored_hashes if c]
            user_mfa.backup_codes = (
                mfa_service.encrypt_backup_codes(remaining) if remaining else None
            )
            await db.flush()
            return True
    return False


@router.post("/mfa/verify", response_model=TokenResponse)
async def verify_mfa_challenge(
    request: Request,
    response: Response,
    data: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete an MFA login challenge.

    Called after /login returns mfa_required=true. Accepts the short-lived
    mfa_token from that response together with a 6-digit TOTP code (or a
    XXXX-XXXX backup code). Returns a full TokenResponse on success.
    Rate limited to 3 attempts per minute per IP, and 5 per 15 minutes per
    user ID embedded in the MFA token (prevents distributed IP bypass).
    """
    # Primary IP-based rate limit
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=3,
        window_seconds=60,
    )

    # Secondary per-user rate limit: extract user_id from mfa_token without
    # full signature verification (verification happens below). This prevents
    # distributed-IP bypass where many IPs share the same mfa_pending token.
    try:
        unverified = jwt.decode(
            data.mfa_token,
            options={"verify_signature": False},
            algorithms=[settings.ALGORITHM],
        )
        if token_sub := unverified.get("sub"):
            await rate_limit_service.check_rate_limit(
                request=request,
                max_requests=5,
                window_seconds=900,  # 15 minutes
                identifier=f"mfa_user:{token_sub}",
            )
    except Exception:
        pass  # Full decode below will reject invalid tokens

    try:
        payload = decode_token(data.mfa_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        )

    if payload.get("type") != "mfa_pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(
        select(User)
        .where(User.id == user_id, User.is_active.is_(True))
        .options(selectinload(User.mfa))
    )
    user = result.scalar_one_or_none()

    if not user or not user.mfa or not user.mfa.is_enabled or not user.mfa.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA verification failed",
        )

    # Verify TOTP code first, then try backup code
    decrypted_secret = mfa_service.decrypt_secret(user.mfa.secret)
    code_ok = mfa_service.verify_totp(decrypted_secret, data.code)
    if not code_ok:
        code_ok = await _verify_and_consume_backup_code(db, user.mfa, data.code)
    if not code_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    user.mfa.last_used_at = utc_now()
    await user_crud.update_last_login(db, user.id)
    await db.commit()

    return await create_auth_response(db, user, response)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    data: RefreshTokenRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Accepts the refresh token from either the httpOnly cookie (preferred) or the
    request body (for non-browser clients / backward compatibility).
    Rate limited to 10 refreshes per minute to prevent abuse.
    """
    # Rate limit: 10 refresh attempts per minute per IP
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=10,
        window_seconds=60,
    )

    # Prefer httpOnly cookie; fall back to body for non-browser clients
    raw_token = request.cookies.get("refresh_token") or (data.refresh_token if data else None)
    if not raw_token:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    try:
        # Decode refresh token
        payload = decode_token(raw_token)

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
            if settings.DEBUG:
                logger.warning(
                    f"Token refresh failed: Token not found in database (jti: {jti[:10]}...)"
                )
            else:
                logger.warning("Token refresh failed: Token not found in database")
            _clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not found",
            )

        if refresh_token.is_revoked:
            logger.warning(
                f"Token refresh failed: Token has been revoked (user_id: {refresh_token.user_id})"
            )
            _clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        if refresh_token.is_expired:
            logger.warning(
                f"Token refresh failed: Token has expired (user_id: {refresh_token.user_id})"
            )
            _clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )

        # Fast-path Redis JTI check (production only) — O(1) revocation detection
        # before the DB lookup completes.  Falls through when Redis is unavailable.
        if settings.ENFORCE_JTI_REDIS_CHECK:
            from app.core.jti_store import verify_jti

            if not await verify_jti(jti):
                logger.warning("Token refresh failed: JTI not found in Redis (revoked or expired)")
                _clear_refresh_cookie(response)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has been revoked",
                )

        # Get user
        user = await user_crud.get_by_id(db, refresh_token.user_id)
        if not user or not user.is_active:
            logger.warning(
                "Token refresh failed: User not found or inactive"
                f" (user_id: {refresh_token.user_id})"
            )
            _clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        logger.info("Token refresh successful")

        # Generate new access token
        access_token = create_access_token(
            data={
                "sub": str(user.id),
            }
        )

        # Rotate the refresh token: issue a new one, revoke the old one.
        # This means a stolen token can only be used once — the next legitimate
        # refresh will fail (token revoked), alerting the real user.
        new_refresh_token_str, new_jti, new_expires_at = create_refresh_token(str(user.id))
        new_token_hash = hashlib.sha256(new_jti.encode()).hexdigest()
        await refresh_token_crud.create(
            db=db,
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
        )
        await refresh_token_crud.revoke(db, token_hash)

        # Mirror token rotation in Redis — add new JTI, remove old one
        if settings.ENFORCE_JTI_REDIS_CHECK:
            from app.core.jti_store import delete_jti, store_jti

            await store_jti(new_jti, str(user.id), _REFRESH_COOKIE_MAX_AGE)
            await delete_jti(jti)

        if request.cookies.get("refresh_token"):
            _set_refresh_cookie(response, new_refresh_token_str)

        return AccessTokenResponse(
            access_token=access_token,
            user=UserSchema.from_orm(user),
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.error("Database error during token refresh", exc_info=True)
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token refresh",
        )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token",
        )


@router.get("/verify-email", response_model=Dict[str, Any])
async def verify_email(
    request: Request,
    token: str = Query(..., description="Email verification token from the link"),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a user's email address using the token sent to their inbox.
    Rate limited to 10 attempts per minute to prevent brute-forcing tokens.
    """
    await rate_limit_service.check_rate_limit(request=request, max_requests=10, window_seconds=60)

    token_hash = hash_token(token)
    result = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()

    if not record or not record.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link. Please request a new one.",
        )

    # Mark token as used and verify the user's email
    record.used_at = utc_now()
    user = await user_crud.get_by_id(db, record.user_id)
    if user:
        user.email_verified = True
    await db.commit()

    logger.info("Email verified for user %s", record.user_id)
    return {"message": "Email verified successfully"}


@router.post("/resend-verification", response_model=Dict[str, Any])
async def resend_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resend an email verification link to the currently authenticated user.
    Rate limited to 3 requests per hour per user to prevent abuse.
    """
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=3,
        window_seconds=3600,
        identifier=str(current_user.id),
    )

    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified",
        )

    raw_token = await create_verification_token(db, current_user.id)
    await email_service.send_verification_email(
        to_email=current_user.email,
        token=raw_token,
        display_name=current_user.display_name or current_user.first_name or current_user.email,
    )

    response: dict = {"message": "Verification email sent"}
    # In development+debug, return the raw token so devs can test without SMTP.
    # Requires both flags to prevent accidental token leakage.
    if settings.ENVIRONMENT == "development" and settings.DEBUG:
        response["debug_token"] = raw_token
    return response


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


@router.post("/forgot-password", response_model=Dict[str, Any])
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset email.

    Always returns 200 regardless of whether the email is registered — this
    prevents user enumeration. Rate limited to 3 requests per hour per IP to
    prevent email flooding. In development+debug mode, the raw token is
    included in the response for testing without a real SMTP server.
    """
    await rate_limit_service.check_rate_limit(request=request, max_requests=3, window_seconds=3600)

    result = await db.execute(
        select(User).where(User.email == data.email, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()

    response: dict = {
        "message": "If that email is registered, a password reset link has been sent."
    }

    if user:
        raw_token = await create_password_reset_token(db, user.id)
        await email_service.send_password_reset_email(
            to_email=user.email,
            token=raw_token,
            display_name=user.display_name or user.first_name or user.email,
        )
        logger.info("Password reset requested for user=%s", user.id)
        # In development+debug, return the raw token so devs can test without SMTP.
        if settings.ENVIRONMENT == "development" and settings.DEBUG:
            response["debug_token"] = raw_token

    return response


@router.post("/reset-password", response_model=AuthMessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset a user's password using a token from the forgot-password email.

    Validates the token, updates the password, clears any account lockout,
    and marks the token as used. Rate limited to 3 requests per hour per IP.
    """
    await rate_limit_service.check_rate_limit(request=request, max_requests=3, window_seconds=3600)

    token_hash = hash_token(data.token)
    result = await db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .options(selectinload(PasswordResetToken.user))
    )
    record = result.scalar_one_or_none()

    if not record or not record.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link",
        )

    user = record.user

    # Validate password strength and check against breach database —
    # same checks applied at registration and change-password endpoints.
    await password_validation_service.validate_and_raise_async(data.new_password, check_breach=True)

    user.password_hash = hash_password(data.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    record.used_at = utc_now()

    # Revoke all existing refresh tokens for this user
    await db.execute(
        sa_update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utc_now())
    )

    await db.commit()

    logger.info("Password reset completed for user %s", user.id)
    return AuthMessageResponse(message="Password reset successfully. You can now log in with your new password.")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    request: Request,
    response: Response,
    data: RefreshTokenRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Logout by revoking the refresh token and clearing the httpOnly cookie.
    """
    try:
        # Prefer cookie; fall back to body for non-browser clients
        raw_token = request.cookies.get("refresh_token") or (data.refresh_token if data else None)
        if raw_token:
            payload = decode_token(raw_token)
            jti = payload.get("jti")
            if jti:
                token_hash = hashlib.sha256(jti.encode()).hexdigest()
                await refresh_token_crud.revoke(db, token_hash)
                # Remove from Redis immediately — token is now dead in both stores
                if settings.ENFORCE_JTI_REDIS_CHECK:
                    from app.core.jti_store import delete_jti

                    await delete_jti(jti)
    except Exception:
        pass  # If token is invalid, still clear cookie and return success

    _clear_refresh_cookie(response)
    return None


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout_all_devices(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke every active refresh token for this user (logout all devices).

    Marks all non-revoked RefreshToken rows as revoked in Postgres, removes
    all JTIs from Redis (production), and clears the current device's cookie.
    """
    # Revoke all tokens in DB
    await db.execute(
        sa_update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=utc_now())
    )
    await db.commit()

    # Remove all JTIs from Redis — any in-flight tokens are immediately dead
    if settings.ENFORCE_JTI_REDIS_CHECK:
        from app.core.jti_store import delete_all_jtis_for_user

        await delete_all_jtis_for_user(str(current_user.id))

    _clear_refresh_cookie(response)
    logger.info("logout_all: revoked all tokens for user=%s", current_user.id)
    return None


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information.
    """
    return UserSchema.from_orm(current_user)


if settings.DEBUG:

    @router.post("/debug/check-refresh-token", response_model=Dict[str, Any])
    async def debug_check_refresh_token(
        data: RefreshTokenRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """
        Debug endpoint to check refresh token validity.
        Only available in DEBUG mode and requires authentication.
        """
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
        except Exception:
            return {
                "decode_success": False,
                "error": "Token decode failed",
            }