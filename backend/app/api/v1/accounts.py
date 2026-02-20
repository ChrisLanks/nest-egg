"""Account API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    get_verified_account,
    verify_household_member,
    get_user_accounts,
    get_all_household_accounts,
)
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.holding import Holding
from app.schemas.account import (
    Account as AccountSchema,
    AccountSummary,
    ManualAccountCreate,
    AccountUpdate,
)
from app.services.deduplication_service import DeduplicationService
from app.services.input_sanitization_service import input_sanitization_service
from app.services.rate_limit_service import rate_limit_service
from app.config import settings

_ALLOWED_VALUATION_PROVIDERS = {"rentcast", "attom", "marketcheck"}


class ProviderAvailability(BaseModel):
    """Response model for provider availability."""

    plaid: bool
    teller: bool
    mx: bool


class BulkVisibilityUpdate(BaseModel):
    """Request model for bulk visibility updates."""

    account_ids: List[UUID]
    is_active: bool


router = APIRouter()

# Initialize deduplication service
deduplication_service = DeduplicationService()


@router.get("/providers/availability", response_model=ProviderAvailability)
async def get_provider_availability(
    current_user: User = Depends(get_current_user),
):
    """
    Get availability status of account providers based on configured credentials.

    Returns which providers (Plaid, Teller, MX) are available based on whether
    their API credentials are configured in the environment.
    """
    return ProviderAvailability(
        plaid=settings.PLAID_ENABLED and bool(settings.PLAID_CLIENT_ID and settings.PLAID_SECRET),
        teller=settings.TELLER_ENABLED and bool(settings.TELLER_APP_ID and settings.TELLER_API_KEY),
        mx=False,  # MX not yet implemented
    )


@router.get("/", response_model=List[AccountSummary])
async def list_accounts(
    include_hidden: bool = Query(False, description="Include hidden accounts (admin view)"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all accounts for the current user's organization (provider-agnostic)."""
    # Query accounts directly to respect include_hidden parameter
    if include_hidden:
        # Admin view - include ALL accounts regardless of is_active status
        conditions = [Account.organization_id == current_user.organization_id]
        if user_id:
            await verify_household_member(db, user_id, current_user.organization_id)
            conditions.append(Account.user_id == user_id)

        result = await db.execute(
            select(Account)
            .options(joinedload(Account.plaid_item), joinedload(Account.teller_enrollment))
            .where(*conditions)
        )
        accounts = result.unique().scalars().all()
    else:
        # Normal view - use existing dependencies that filter by is_active
        if user_id:
            await verify_household_member(db, user_id, current_user.organization_id)
            accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        else:
            accounts = await get_all_household_accounts(db, current_user.organization_id)

    # Deduplicate accounts (shared accounts appear multiple times when multiple household members link the same account)
    accounts = deduplication_service.deduplicate_accounts(accounts)

    # Sort by name
    accounts = sorted(accounts, key=lambda a: a.name)

    # Construct AccountSummary with provider-agnostic sync status
    summaries = []
    for acc in accounts:
        # Determine which provider to use for sync status
        provider_item_id = None
        last_synced_at = None
        last_error_code = None
        last_error_message = None
        needs_reauth = None

        if acc.account_source.value == "plaid" and acc.plaid_item:
            provider_item_id = acc.plaid_item_id
            last_synced_at = acc.plaid_item.last_synced_at
            last_error_code = acc.plaid_item.last_error_code
            last_error_message = acc.plaid_item.last_error_message
            needs_reauth = acc.plaid_item.needs_reauth
        elif acc.account_source.value == "teller" and acc.teller_enrollment:
            provider_item_id = acc.teller_enrollment_id
            last_synced_at = acc.teller_enrollment.last_synced_at
            last_error_code = acc.teller_enrollment.last_error_code
            last_error_message = acc.teller_enrollment.last_error_message
            needs_reauth = False  # Teller doesn't use reauth concept

        summary = AccountSummary(
            id=acc.id,
            user_id=acc.user_id,
            name=acc.name,
            account_type=acc.account_type,
            account_source=acc.account_source,
            property_type=acc.property_type,
            institution_name=acc.institution_name,
            mask=acc.mask,
            current_balance=acc.current_balance,
            balance_as_of=acc.balance_as_of,
            is_active=acc.is_active,
            exclude_from_cash_flow=acc.exclude_from_cash_flow,
            plaid_item_hash=acc.plaid_item_hash,
            # Provider-agnostic sync status
            provider_item_id=provider_item_id,
            last_synced_at=last_synced_at,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
            needs_reauth=needs_reauth,
        )
        summaries.append(summary)

    return summaries


@router.get("/{account_id}", response_model=AccountSchema)
async def get_account(
    account: Account = Depends(get_verified_account),
):
    """Get a specific account."""
    return account


@router.post("/manual", response_model=AccountSchema)
async def create_manual_account(
    account_data: ManualAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual account."""
    # Generate hash for deduplication across household members
    plaid_item_hash = deduplication_service.calculate_manual_account_hash(
        account_type=account_data.account_type,
        institution_name=account_data.institution,
        mask=account_data.account_number_last4,
        name=account_data.name,
    )

    # Determine if account should be excluded from cash flow by default
    # Loans and mortgages are excluded to prevent double-counting (payment from checking + loan balance decrease)
    exclude_from_cash_flow = account_data.account_type in [
        AccountType.MORTGAGE,
        AccountType.LOAN,
        AccountType.STUDENT_LOAN,
        AccountType.CREDIT_CARD,
    ]

    # Create the account
    account = Account(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        name=input_sanitization_service.sanitize_html(account_data.name),
        account_type=account_data.account_type,
        property_type=account_data.property_type,
        account_source=account_data.account_source,
        institution_name=account_data.institution,
        mask=account_data.account_number_last4,
        current_balance=account_data.balance,
        plaid_item_hash=plaid_item_hash,
        is_manual=True,
        is_active=True,
        exclude_from_cash_flow=exclude_from_cash_flow,
        # Debt/Loan fields
        interest_rate=account_data.interest_rate,
        interest_rate_type=account_data.interest_rate_type,
        minimum_payment=account_data.minimum_payment,
        payment_due_day=account_data.payment_due_day,
        original_amount=account_data.original_amount,
        origination_date=account_data.origination_date,
        maturity_date=account_data.maturity_date,
        loan_term_months=account_data.loan_term_months,
        compounding_frequency=account_data.compounding_frequency,
        # Private Debt fields
        principal_amount=account_data.principal_amount,
        # Private Equity fields
        grant_type=account_data.grant_type,
        grant_date=account_data.grant_date,
        quantity=account_data.quantity,
        strike_price=account_data.strike_price,
        vesting_schedule=account_data.vesting_schedule,
        share_price=account_data.share_price,
        company_status=account_data.company_status,
        valuation_method=account_data.valuation_method,
        include_in_networth=account_data.include_in_networth,
        # Pension / Annuity income fields
        monthly_benefit=account_data.monthly_benefit,
        benefit_start_date=account_data.benefit_start_date,
        # Credit card fields
        limit=account_data.credit_limit,
        # Business Equity fields
        company_valuation=account_data.company_valuation,
        ownership_percentage=account_data.ownership_percentage,
        equity_value=account_data.equity_value,
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    # Create holdings if provided (for investment accounts)
    if account_data.holdings:
        for holding_data in account_data.holdings:
            # Calculate cost basis (use current price as cost basis)
            cost_basis_per_share = holding_data.price_per_share
            total_cost_basis = holding_data.shares * cost_basis_per_share

            holding = Holding(
                account_id=account.id,
                organization_id=current_user.organization_id,
                ticker=holding_data.ticker.upper(),
                shares=holding_data.shares,
                cost_basis_per_share=cost_basis_per_share,
                total_cost_basis=total_cost_basis,
                current_price_per_share=holding_data.price_per_share,
                current_total_value=holding_data.shares * holding_data.price_per_share,
            )
            db.add(holding)

        await db.commit()

    return account


@router.patch("/bulk-visibility")
async def bulk_update_visibility(
    request: BulkVisibilityUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update visibility for multiple accounts.
    Rate limited to 30 requests per minute.
    Only updates accounts owned by the current user.
    """
    # Rate limit: 30 bulk update requests per minute per IP
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=30,
        window_seconds=60,
    )

    import logging

    logger = logging.getLogger(__name__)

    logger.info(
        f"[bulk-visibility] Request: account_ids={request.account_ids}, is_active={request.is_active}, user_id={current_user.id}, org_id={current_user.organization_id}"
    )

    # Check which accounts exist and are owned by the user
    check_result = await db.execute(
        select(Account.id, Account.user_id, Account.organization_id, Account.is_active).where(
            Account.id.in_(request.account_ids)
        )
    )
    existing_accounts = check_result.all()
    logger.info(f"[bulk-visibility] Found {len(existing_accounts)} accounts: {existing_accounts}")

    # Only allow updating accounts owned by the current user
    result = await db.execute(
        update(Account)
        .where(
            Account.id.in_(request.account_ids),
            Account.organization_id == current_user.organization_id,
            Account.user_id == current_user.id,  # Must be account owner
        )
        .values(is_active=request.is_active)
    )
    await db.commit()

    logger.info(f"[bulk-visibility] Updated {result.rowcount} accounts")

    return {"updated_count": result.rowcount}


@router.patch("/{account_id}", response_model=AccountSchema)
async def update_account(
    account_data: AccountUpdate,
    account: Account = Depends(get_verified_account),
    db: AsyncSession = Depends(get_db),
):
    """Update account details."""
    # Update basic fields
    if account_data.name is not None:
        account.name = input_sanitization_service.sanitize_html(account_data.name)
    if account_data.is_active is not None:
        account.is_active = account_data.is_active
    if account_data.current_balance is not None:
        account.current_balance = account_data.current_balance
    if account_data.mask is not None:
        account.mask = account_data.mask
    if account_data.exclude_from_cash_flow is not None:
        account.exclude_from_cash_flow = account_data.exclude_from_cash_flow

    # Update Debt/Loan fields
    if account_data.interest_rate is not None:
        account.interest_rate = account_data.interest_rate
    if account_data.interest_rate_type is not None:
        account.interest_rate_type = account_data.interest_rate_type
    if account_data.minimum_payment is not None:
        account.minimum_payment = account_data.minimum_payment
    if account_data.payment_due_day is not None:
        account.payment_due_day = account_data.payment_due_day
    if account_data.original_amount is not None:
        account.original_amount = account_data.original_amount
    if account_data.origination_date is not None:
        account.origination_date = account_data.origination_date
    if account_data.maturity_date is not None:
        account.maturity_date = account_data.maturity_date
    if account_data.loan_term_months is not None:
        account.loan_term_months = account_data.loan_term_months
    if account_data.compounding_frequency is not None:
        account.compounding_frequency = account_data.compounding_frequency

    # Update Private Debt fields
    if account_data.principal_amount is not None:
        account.principal_amount = account_data.principal_amount

    # Update Private Equity fields
    if account_data.grant_type is not None:
        account.grant_type = account_data.grant_type
    if account_data.grant_date is not None:
        account.grant_date = account_data.grant_date
    if account_data.quantity is not None:
        account.quantity = account_data.quantity
    if account_data.strike_price is not None:
        account.strike_price = account_data.strike_price
    if account_data.vesting_schedule is not None:
        account.vesting_schedule = account_data.vesting_schedule
    if account_data.share_price is not None:
        account.share_price = account_data.share_price
    if account_data.company_status is not None:
        account.company_status = account_data.company_status
    if account_data.valuation_method is not None:
        account.valuation_method = account_data.valuation_method
    if account_data.include_in_networth is not None:
        account.include_in_networth = account_data.include_in_networth

    # Update Pension / Annuity income fields
    if account_data.monthly_benefit is not None:
        account.monthly_benefit = account_data.monthly_benefit
    if account_data.benefit_start_date is not None:
        account.benefit_start_date = account_data.benefit_start_date

    # Update credit card limit
    if account_data.credit_limit is not None:
        account.limit = account_data.credit_limit

    # Update Business Equity fields
    if account_data.company_valuation is not None:
        account.company_valuation = account_data.company_valuation
    if account_data.ownership_percentage is not None:
        account.ownership_percentage = account_data.ownership_percentage
    if account_data.equity_value is not None:
        account.equity_value = account_data.equity_value

    # Property auto-valuation fields
    if account_data.property_address is not None:
        account.property_address = account_data.property_address
    if account_data.property_zip is not None:
        account.property_zip = account_data.property_zip

    # Vehicle auto-valuation fields
    if account_data.vehicle_vin is not None:
        account.vehicle_vin = account_data.vehicle_vin.upper()
    if account_data.vehicle_mileage is not None:
        account.vehicle_mileage = account_data.vehicle_mileage

    await db.commit()
    await db.refresh(account)

    return account


@router.get("/valuation-providers")
async def get_valuation_providers(
    current_user: User = Depends(get_current_user),
):
    """
    Return the lists of configured valuation providers.

    The frontend uses this to decide whether to show/hide the "Refresh
    Valuation" button and, when multiple providers are available, render
    a provider selector.

    Response shape:
        {
            "property": ["rentcast", "attom"],   # zero or more
            "vehicle":  ["marketcheck"]           # zero or more
        }
    """
    from app.services.valuation_service import (
        get_available_property_providers,
        get_available_vehicle_providers,
    )
    return {
        "property": get_available_property_providers(),
        "vehicle": get_available_vehicle_providers(),
    }


@router.post("/{account_id}/refresh-valuation")
async def refresh_account_valuation(
    account_id: UUID,
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh the current_balance of a property or vehicle account via
    the configured auto-valuation APIs.

    Optional query param:
        provider=rentcast|attom|marketcheck
    When omitted, the first available configured provider is used.
    """
    from datetime import datetime, timezone
    from app.services.valuation_service import (
        get_property_value,
        get_vehicle_value,
        decode_vin_nhtsa,
        get_available_property_providers,
        get_available_vehicle_providers,
    )
    from fastapi import HTTPException

    if provider is not None and provider not in _ALLOWED_VALUATION_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid provider")

    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    valuation_result = None
    vin_info = None

    if account.account_type == AccountType.PROPERTY:
        if not account.property_address or not account.property_zip:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Set property_address and property_zip on this account "
                    "before requesting an auto-valuation."
                ),
            )
        if not get_available_property_providers():
            logger.warning(
                "property_valuation: no provider configured — "
                "set RENTCAST_API_KEY (free) or ATTOM_API_KEY"
            )
            raise HTTPException(
                status_code=503,
                detail="Automatic property valuation is not available at this time.",
            )
        valuation_result = await get_property_value(
            account.property_address, account.property_zip, provider=provider
        )

    elif account.account_type == AccountType.VEHICLE:
        if account.vehicle_vin:
            vin_info = await decode_vin_nhtsa(account.vehicle_vin)

        if not get_available_vehicle_providers():
            logger.warning(
                "vehicle_valuation: no provider configured — set MARKETCHECK_API_KEY"
            )
            raise HTTPException(
                status_code=503,
                detail="Automatic vehicle valuation is not available at this time.",
            )
        if not account.vehicle_vin:
            raise HTTPException(
                status_code=422,
                detail="Set vehicle_vin on this account before requesting an auto-valuation.",
            )
        valuation_result = await get_vehicle_value(
            account.vehicle_vin, account.vehicle_mileage, provider=provider
        )

    else:
        raise HTTPException(
            status_code=422,
            detail="Auto-valuation is only supported for property and vehicle accounts.",
        )

    if valuation_result is None:
        raise HTTPException(
            status_code=502,
            detail="The valuation provider did not return a value. Please try again later.",
        )

    now = datetime.now(timezone.utc)
    await db.execute(
        update(Account)
        .where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
        .values(
            current_balance=valuation_result.value,
            last_auto_valued_at=now,
            balance_as_of=now,
        )
    )
    await db.commit()

    return {
        "id": str(account.id),
        "new_value": float(valuation_result.value),
        "provider": valuation_result.provider,
        "low": float(valuation_result.low) if valuation_result.low else None,
        "high": float(valuation_result.high) if valuation_result.high else None,
        "last_auto_valued_at": now.isoformat(),
        "vin_info": vin_info,
    }


@router.post("/bulk-delete")
async def bulk_delete_accounts(
    account_ids: List[UUID],
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple accounts at once. Only deletes accounts owned by the current user."""
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=60,
    )
    # Only allow deletion of accounts owned by the current user
    result = await db.execute(
        delete(Account).where(
            Account.id.in_(account_ids),
            Account.organization_id == current_user.organization_id,
            Account.user_id == current_user.id,  # Must be account owner
        )
    )
    await db.commit()
    return {"deleted_count": result.rowcount}
