"""
MX Platform API integration service.

MX provides bank account aggregation via the MX Platform API.
Enterprise-only (requires sales contract for production access).

- Sandbox: https://int-api.mx.com (100 users, 25 members/user)
- Production: https://api.mx.com
- Auth: HTTP Basic (client_id:api_key)
- Header: Accept: application/vnd.mx.api.v1+json

Note: Uses httpx directly instead of mx-platform-python SDK due to
pydantic v1/v2 incompatibility.
"""

import hashlib
import logging
import httpx
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.account import Account, MxMember, AccountSource, AccountType
from app.models.transaction import Transaction
from app.services.encryption_service import get_encryption_service
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30.0

_MX_BASE_URLS = {
    "sandbox": "https://int-api.mx.com",
    "production": "https://api.mx.com",
}


class MxService:
    """Service for MX Platform API integration."""

    def __init__(self):
        if not settings.MX_CLIENT_ID or not settings.MX_API_KEY:
            raise ValueError(
                "MX_CLIENT_ID and MX_API_KEY must be configured. "
                "Contact MX for API credentials: https://www.mx.com/products/platform-api"
            )
        self.base_url = _MX_BASE_URLS.get(settings.MX_ENV, _MX_BASE_URLS["sandbox"])
        self._auth = (settings.MX_CLIENT_ID, settings.MX_API_KEY)
        self.encryption_service = get_encryption_service()

    async def _make_request(
        self,
        method: str,
        path: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        """Make authenticated request to MX Platform API."""
        headers = {
            "Accept": "application/vnd.mx.api.v1+json",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                auth=self._auth,
                headers=headers,
                json=json,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    # ── User management ────────────────────────────────────────────────────

    async def create_user(self, user_id: UUID) -> str:
        """Create an MX user and return the mx_user_guid.

        MX requires a user record before members can be created.
        We use our internal user_id as the external identifier for traceability.
        """
        data = await self._make_request(
            "POST",
            "/users",
            json={
                "user": {
                    "metadata": str(user_id),
                }
            },
        )
        return data["user"]["guid"]

    async def get_or_create_user(self, db: AsyncSession, user_id: UUID) -> str:
        """Get existing MX user GUID or create one.

        Looks for any MxMember belonging to this user to reuse the mx_user_guid.
        If none exists, creates a new MX user.
        """
        result = await db.execute(
            select(MxMember.mx_user_guid).where(MxMember.user_id == user_id).limit(1)
        )
        existing_guid = result.scalar_one_or_none()
        if existing_guid:
            return existing_guid

        return await self.create_user(user_id)

    # ── Connect widget ─────────────────────────────────────────────────────

    async def get_connect_widget_url(self, mx_user_guid: str) -> Tuple[str, str]:
        """Request a Connect Widget URL for the given MX user.

        Returns (widget_url, expiration).
        The frontend should embed this URL in an iframe or webview.
        """
        data = await self._make_request(
            "POST",
            f"/users/{mx_user_guid}/connect_widget_url",
            json={
                "config": {
                    "mode": "aggregation",
                    "ui_message_version": 4,
                }
            },
        )
        widget = data["user"]["connect_widget_url"]
        return widget["url"], widget.get("expiration", "10m")

    # ── Member management ──────────────────────────────────────────────────

    async def create_member_record(
        self,
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID,
        mx_user_guid: str,
        member_guid: str,
        institution_code: Optional[str] = None,
        institution_name: Optional[str] = None,
    ) -> MxMember:
        """Persist an MxMember after the user completes the Connect widget."""
        member = MxMember(
            organization_id=organization_id,
            user_id=user_id,
            mx_user_guid=mx_user_guid,
            member_guid=member_guid,
            institution_code=institution_code,
            institution_name=institution_name,
            connection_status="CONNECTED",
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member

    async def get_member_status(self, mx_user_guid: str, member_guid: str) -> Dict:
        """Check the aggregation/connection status of a member."""
        data = await self._make_request(
            "GET",
            f"/users/{mx_user_guid}/members/{member_guid}/status",
        )
        return data.get("member", {})

    # ── Account sync ───────────────────────────────────────────────────────

    async def sync_accounts(self, db: AsyncSession, member: MxMember) -> List[Account]:
        """Fetch accounts from MX for a given member and upsert locally."""
        data = await self._make_request(
            "GET",
            f"/users/{member.mx_user_guid}/members/{member.member_guid}/accounts",
        )
        mx_accounts = data.get("accounts", [])

        # Pre-fetch existing accounts for this member to avoid N+1 queries
        existing_result = await db.execute(
            select(Account).where(Account.mx_member_id == member.id)
        )
        existing_accounts = {
            acc.external_account_id: acc for acc in existing_result.scalars().all()
        }

        synced: List[Account] = []
        for mx_acc in mx_accounts:
            # Check for existing account using pre-fetched map
            account = existing_accounts.get(mx_acc["guid"])

            if not account:
                account = Account(
                    organization_id=member.organization_id,
                    user_id=member.user_id,
                    mx_member_id=member.id,
                    external_account_id=mx_acc["guid"],
                    name=mx_acc.get("name", "Unknown Account"),
                    account_type=self._map_account_type(mx_acc.get("type")),
                    account_source=AccountSource.MX,
                    mask=mx_acc.get("account_number")[-4:] if mx_acc.get("account_number") else None,
                    institution_name=member.institution_name,
                    current_balance=Decimal(str(mx_acc.get("balance", 0))),
                    available_balance=Decimal(str(mx_acc.get("available_balance", 0)))
                    if mx_acc.get("available_balance") is not None
                    else None,
                )
                db.add(account)
            else:
                account.current_balance = Decimal(str(mx_acc.get("balance", 0)))
                if mx_acc.get("available_balance") is not None:
                    account.available_balance = Decimal(str(mx_acc.get("available_balance", 0)))
                account.updated_at = utc_now()

            synced.append(account)

        await db.commit()

        member.last_synced_at = utc_now()
        await db.commit()

        return synced

    # ── Transaction sync ───────────────────────────────────────────────────

    async def sync_transactions(
        self, db: AsyncSession, account: Account, days_back: int = 90
    ) -> List[Transaction]:
        """Fetch transactions from MX and upsert locally."""
        member = account.mx_member
        if not member:
            raise ValueError("Account does not have MX member")

        from_date = (utc_now().date() - timedelta(days=days_back)).isoformat()

        data = await self._make_request(
            "GET",
            f"/users/{member.mx_user_guid}/accounts/{account.external_account_id}/transactions",
            params={"from_date": from_date, "records_per_page": 250},
        )
        mx_transactions = data.get("transactions", [])

        # Pre-fetch existing external IDs for this account to avoid N+1 queries
        ext_result = await db.execute(
            select(Transaction.external_transaction_id).where(
                Transaction.account_id == account.id,
                Transaction.external_transaction_id.isnot(None),
            )
        )
        existing_ext_ids = {row[0] for row in ext_result.all()}

        synced: List[Transaction] = []
        for txn in mx_transactions:
            if txn["guid"] in existing_ext_ids:
                continue  # Already imported

            transaction = Transaction(
                organization_id=account.organization_id,
                account_id=account.id,
                external_transaction_id=txn["guid"],
                date=datetime.fromisoformat(txn["transacted_at"].replace("Z", "+00:00")).date()
                if txn.get("transacted_at")
                else datetime.fromisoformat(txn["date"]).date(),
                amount=Decimal(str(txn["amount"])),
                merchant_name=txn.get("merchant_category_code") and txn.get("description"),
                description=txn.get("description") or txn.get("original_description"),
                category_primary=txn.get("top_level_category"),
                category_detailed=txn.get("category"),
                is_pending=txn.get("status") == "PENDING",
                deduplication_hash=self._generate_dedup_hash(account.id, txn),
            )
            db.add(transaction)
            synced.append(transaction)

        await db.commit()
        return synced

    # ── Disconnect ─────────────────────────────────────────────────────────

    async def delete_member(self, mx_user_guid: str, member_guid: str) -> None:
        """Delete a member connection on MX side."""
        await self._make_request(
            "DELETE",
            f"/users/{mx_user_guid}/members/{member_guid}",
        )

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _map_account_type(self, mx_type: Optional[str]) -> AccountType:
        """Map MX account type to our AccountType enum.

        MX types: CHECKING, SAVINGS, LOAN, CREDIT_CARD, INVESTMENT,
                  MORTGAGE, PROPERTY, LINE_OF_CREDIT, etc.
        """
        type_map = {
            "CHECKING": AccountType.CHECKING,
            "SAVINGS": AccountType.SAVINGS,
            "MONEY_MARKET": AccountType.MONEY_MARKET,
            "CERTIFICATE_OF_DEPOSIT": AccountType.CD,
            "CREDIT_CARD": AccountType.CREDIT_CARD,
            "LOAN": AccountType.LOAN,
            "STUDENT_LOAN": AccountType.STUDENT_LOAN,
            "MORTGAGE": AccountType.MORTGAGE,
            "LINE_OF_CREDIT": AccountType.LOAN,
            "INVESTMENT": AccountType.BROKERAGE,
            "RETIREMENT": AccountType.RETIREMENT_401K,
            "PROPERTY": AccountType.PROPERTY,
        }
        return type_map.get((mx_type or "").upper(), AccountType.OTHER)

    def _generate_dedup_hash(self, account_id: UUID, txn: Dict) -> str:
        """Generate deduplication hash for transaction."""
        components = [
            str(account_id),
            txn.get("transacted_at") or txn.get("date", ""),
            str(txn.get("amount", "")),
            txn.get("description", ""),
        ]
        return hashlib.sha256("|".join(components).encode()).hexdigest()


def get_mx_service() -> MxService:
    """Get MX service instance."""
    return MxService()
