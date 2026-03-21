"""Plaid API service with test mode for development."""

import hashlib
import logging
import uuid
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

import httpx
import jwt
import plaid
from fastapi import HTTPException
from jwt import PyJWK
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import (
    LinkTokenCreateRequestUser,
)
from plaid.model.products import Products
from plaid.model.transactions_sync_request import (
    TransactionsSyncRequest,
)

from app.config import settings
from app.models.user import User
from app.services.circuit_breaker import CircuitOpenError, get_circuit_breaker
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# Plaid API base URLs per environment
_PLAID_BASE_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}

# Map settings.PLAID_ENV to plaid.Environment
_PLAID_ENVIRONMENTS = {
    "sandbox": plaid.Environment.Sandbox,
    "development": plaid.Environment.Development,
    "production": plaid.Environment.Production,
}

import time as _time

# Cache for Plaid webhook verification JWK keys, keyed by key_id
_JWK_CACHE_TTL = 86400  # 24 hours
_JWK_CACHE_MAX_SIZE = 20  # Max keys to cache
_jwk_cache: Dict[str, tuple[PyJWK, float]] = {}  # key_id -> (jwk, timestamp)


class PlaidService:
    """Service for interacting with Plaid API."""

    def __init__(self):
        """Initialize Plaid service."""
        self._client_id = settings.PLAID_CLIENT_ID
        self._secret = settings.PLAID_SECRET
        self._base_url = _PLAID_BASE_URLS.get(settings.PLAID_ENV, _PLAID_BASE_URLS["sandbox"])
        self._plaid_api: Optional[plaid_api.PlaidApi] = None

    def _get_plaid_api(self) -> plaid_api.PlaidApi:
        """Get or create Plaid API client.

        Raises HTTPException 503 if credentials are not configured.
        """
        if self._plaid_api is not None:
            return self._plaid_api

        if not self._client_id or not self._secret:
            raise HTTPException(
                status_code=503,
                detail="Plaid is not configured. Set PLAID_CLIENT_ID and PLAID_SECRET.",
            )

        configuration = plaid.Configuration(
            host=_PLAID_ENVIRONMENTS.get(settings.PLAID_ENV, plaid.Environment.Sandbox),
            api_key={
                "clientId": self._client_id,
                "secret": self._secret,
            },
        )
        api_client = plaid.ApiClient(configuration)
        self._plaid_api = plaid_api.PlaidApi(api_client)
        return self._plaid_api

    def is_test_user(self, user: User) -> bool:
        """Check if user is a test user (test@test.com)."""
        return user.email == "test@test.com"

    @staticmethod
    async def _fetch_jwk(key_id: str) -> PyJWK:
        """Fetch a webhook verification key from Plaid by key_id.

        Plaid rotates keys; we cache them by key_id and fetch a new one
        when an unknown key_id appears in a webhook JWT header.
        """
        # Check cache (with TTL)
        if key_id in _jwk_cache:
            jwk, cached_at = _jwk_cache[key_id]
            if _time.time() - cached_at < _JWK_CACHE_TTL:
                return jwk
            del _jwk_cache[key_id]

        base_url = _PLAID_BASE_URLS.get(settings.PLAID_ENV, _PLAID_BASE_URLS["sandbox"])

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{base_url}/webhook_verification_key/get",
                json={
                    "client_id": settings.PLAID_CLIENT_ID,
                    "secret": settings.PLAID_SECRET,
                    "key_id": key_id,
                },
            )
            response.raise_for_status()
            data = response.json()

        jwk_data = data.get("key")
        if not jwk_data:
            raise ValueError(f"No key returned from Plaid for key_id={key_id}")

        key = PyJWK(jwk_data)
        # Evict oldest if at capacity
        if len(_jwk_cache) >= _JWK_CACHE_MAX_SIZE:
            oldest_key = min(_jwk_cache, key=lambda k: _jwk_cache[k][1])
            del _jwk_cache[oldest_key]
        _jwk_cache[key_id] = (key, _time.time())
        return key

    @staticmethod
    async def verify_webhook_signature(
        webhook_verification_header: Optional[str], webhook_body: bytes
    ) -> bool:
        """
        Verify Plaid webhook signature using asymmetric JWT verification.

        Plaid signs webhooks with a rotating EC private key and sends
        the JWT in the 'Plaid-Verification' header. Verification:
        1. Decode JWT header (unverified) to get key_id
        2. Fetch the matching public JWK from Plaid's endpoint (cached)
        3. Verify JWT signature with the public key (ES256)
        4. Verify request_body_sha256 claim matches actual body hash

        Args:
            webhook_verification_header: Value of 'Plaid-Verification' header
            webhook_body: Raw webhook request body

        Returns:
            True if signature is valid, raises HTTPException otherwise
        """
        if not settings.PLAID_CLIENT_ID or not settings.PLAID_SECRET:
            raise HTTPException(
                status_code=500,
                detail="Plaid credentials not configured for webhook verification.",
            )

        if not webhook_verification_header:
            raise HTTPException(status_code=401, detail="Missing Plaid-Verification header")

        try:
            # 1. Decode header without verification to extract key_id
            unverified_header = jwt.get_unverified_header(webhook_verification_header)
            key_id = unverified_header.get("kid")
            if not key_id:
                raise HTTPException(status_code=401, detail="Missing kid in webhook JWT header")

            # 2. Fetch the public key from Plaid (cached by key_id)
            jwk = await PlaidService._fetch_jwk(key_id)

            # 3. Verify JWT signature with the public key
            decoded = jwt.decode(
                webhook_verification_header,
                jwk.key,
                algorithms=["ES256"],
            )

            # 4. Verify body hash
            body_hash_claim = decoded.get("request_body_sha256")
            if not body_hash_claim:
                raise HTTPException(
                    status_code=401, detail="Missing body hash claim in webhook JWT"
                )
            body_hash = hashlib.sha256(webhook_body).hexdigest()
            if body_hash != body_hash_claim:
                raise HTTPException(status_code=401, detail="Webhook body hash mismatch")

            logger.info("Webhook signature verified (key_id=%s)", key_id)
            return True

        except HTTPException:
            raise
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Webhook verification token expired")
        except jwt.InvalidTokenError as e:
            logger.error("Invalid webhook JWT: %s", e, exc_info=True)
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        except httpx.HTTPError as e:
            logger.error("Failed to fetch Plaid JWK: %s", e, exc_info=True)
            raise HTTPException(
                status_code=502, detail="Failed to fetch webhook verification key from Plaid"
            )
        except Exception as e:
            logger.error("Webhook verification error: %s", str(e), exc_info=True)
            raise HTTPException(status_code=401, detail="Webhook verification failed")

    async def create_link_token(self, user: User) -> Tuple[str, str]:
        """
        Create a Plaid Link token.

        For test@test.com users, returns a dummy token.
        For real users, calls Plaid API.

        Returns:
            Tuple of (link_token, expiration)
        """
        if self.is_test_user(user):
            dummy_token = f"link-sandbox-{uuid.uuid4()}"
            expiration = (utc_now() + timedelta(hours=4)).isoformat()
            return dummy_token, expiration

        client = self._get_plaid_api()

        request = LinkTokenCreateRequest(
            client_name="Nest Egg",
            user=LinkTokenCreateRequestUser(client_user_id=str(user.id)),
            products=[Products("transactions"), Products("investments")],
            country_codes=[CountryCode("US")],
            language="en",
        )

        try:
            response = client.link_token_create(request)
            return response.link_token, response.expiration
        except plaid.ApiException as e:
            logger.error("Plaid link_token_create failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=502,
                detail="Failed to create Plaid link token",
            )

    async def exchange_public_token(
        self,
        user: User,
        public_token: str,
        institution_id: Optional[str] = None,
        institution_name: Optional[str] = None,
        accounts_metadata: Optional[List[dict]] = None,
    ) -> Tuple[str, List[dict]]:
        """
        Exchange public token for access token and retrieve accounts.

        For test@test.com users, returns dummy data.
        For real users, calls Plaid API.

        Returns:
            Tuple of (access_token, accounts_list)
        """
        if self.is_test_user(user):
            dummy_access_token = f"access-sandbox-{uuid.uuid4()}"
            dummy_accounts = self._create_dummy_accounts(institution_name or "Test Bank")
            return dummy_access_token, dummy_accounts

        client = self._get_plaid_api()

        try:
            # 1. Exchange public token for access token
            exchange_request = ItemPublicTokenExchangeRequest(
                public_token=public_token,
            )
            exchange_response = client.item_public_token_exchange(exchange_request)
            access_token = exchange_response.access_token

            # 2. Fetch accounts using the new access token
            accounts_request = AccountsGetRequest(access_token=access_token)
            accounts_response = client.accounts_get(accounts_request)

            # 3. Normalize to the dict format expected by callers
            accounts = self._normalize_plaid_accounts(accounts_response.accounts)

            return access_token, accounts

        except plaid.ApiException as e:
            logger.error("Plaid exchange_public_token failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=502,
                detail="Failed to exchange Plaid public token",
            )

    @staticmethod
    def _normalize_plaid_accounts(plaid_accounts: list) -> List[dict]:
        """Normalize Plaid SDK account objects to the dict format used throughout the app."""
        accounts = []
        for acc in plaid_accounts:
            balances = acc.balances
            accounts.append(
                {
                    "account_id": acc.account_id,
                    "name": acc.name,
                    "mask": acc.mask,
                    "official_name": acc.official_name,
                    "type": acc.type.value if hasattr(acc.type, "value") else str(acc.type),
                    "subtype": acc.subtype.value
                    if acc.subtype and hasattr(acc.subtype, "value")
                    else str(acc.subtype)
                    if acc.subtype
                    else None,
                    "current_balance": float(balances.current)
                    if balances.current is not None
                    else None,
                    "available_balance": float(balances.available)
                    if balances.available is not None
                    else None,
                    "limit": float(balances.limit) if balances.limit is not None else None,
                }
            )
        return accounts

    def _create_dummy_accounts(self, institution_name: str) -> List[dict]:
        """Create dummy account data for testing."""
        return [
            {
                "account_id": f"acc_{uuid.uuid4().hex[:16]}",
                "name": f"{institution_name} Checking",
                "mask": "1234",
                "official_name": f"{institution_name} Premium Checking Account",
                "type": "depository",
                "subtype": "checking",
                "current_balance": 5420.50,
                "available_balance": 5420.50,
                "limit": None,
            },
            {
                "account_id": f"acc_{uuid.uuid4().hex[:16]}",
                "name": f"{institution_name} Savings",
                "mask": "5678",
                "official_name": f"{institution_name} High-Yield Savings",
                "type": "depository",
                "subtype": "savings",
                "current_balance": 12350.75,
                "available_balance": 12350.75,
                "limit": None,
            },
            {
                "account_id": f"acc_{uuid.uuid4().hex[:16]}",
                "name": f"{institution_name} Credit Card",
                "mask": "9012",
                "official_name": f"{institution_name} Platinum Card",
                "type": "credit",
                "subtype": "credit_card",
                "current_balance": -1250.00,  # Negative for credit cards (amount owed)
                "available_balance": None,
                "limit": 10000.00,
            },
            {
                "account_id": f"acc_{uuid.uuid4().hex[:16]}",
                "name": f"{institution_name} Brokerage",
                "mask": "3456",
                "official_name": f"{institution_name} Investment Account",
                "type": "investment",
                "subtype": "brokerage",
                "current_balance": 45680.25,  # Total portfolio value
                "available_balance": None,
                "limit": None,
            },
        ]

    async def get_accounts(self, user: User, access_token: str) -> List[dict]:
        """
        Fetch accounts for a connected Plaid item.

        For test@test.com users, returns empty list.
        For real users, calls Plaid API.
        """
        if self.is_test_user(user):
            return []

        client = self._get_plaid_api()

        try:
            request = AccountsGetRequest(access_token=access_token)
            response = client.accounts_get(request)
            return self._normalize_plaid_accounts(response.accounts)
        except plaid.ApiException as e:
            logger.error("Plaid accounts_get failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch Plaid accounts",
            )

    async def get_investment_holdings(
        self, user: User, access_token: str
    ) -> Tuple[List[dict], List[dict]]:
        """
        Fetch investment holdings from Plaid.

        Returns:
            Tuple of (holdings_list, securities_list)
        """
        if self.is_test_user(user):
            # Return dummy holdings for test user
            return self._create_dummy_holdings()

        # For real users, call Plaid investments/holdings/get via circuit breaker
        cb = get_circuit_breaker()
        try:
            return await cb.call("plaid", self._fetch_holdings, access_token)
        except CircuitOpenError:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Plaid API is temporarily unavailable"
                    " (circuit breaker open). Try again later."
                ),
            )

    async def _fetch_holdings(self, access_token: str) -> Tuple[List[dict], List[dict]]:
        """Execute the actual Plaid holdings HTTP request (called via circuit breaker)."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/investments/holdings/get",
                    json={
                        "client_id": self._client_id,
                        "secret": self._secret,
                        "access_token": access_token,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("holdings", []), data.get("securities", [])
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Plaid investments/holdings/get error: %d %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            raise HTTPException(
                status_code=502, detail="Failed to fetch Plaid investment holdings"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Plaid investments/holdings/get request failed: %s", exc)
            raise HTTPException(status_code=502, detail="Plaid API unavailable") from exc

    async def sync_transactions_real(self, access_token: str) -> List[dict]:
        """Sync transactions using Plaid's /transactions/sync endpoint.

        Uses cursor-based pagination: keeps calling until has_more
        is False. Returns all added/modified transactions in the
        normalised dict format expected by
        PlaidTransactionSyncService.sync_transactions_for_item().
        """
        client = self._get_plaid_api()
        all_added: List[dict] = []
        all_modified: List[dict] = []
        all_removed: List[str] = []
        cursor: str = ""

        try:
            has_more = True
            while has_more:
                kwargs = {"access_token": access_token}
                if cursor:
                    kwargs["cursor"] = cursor
                request = TransactionsSyncRequest(**kwargs)
                response = client.transactions_sync(request)

                all_added.extend(self._normalize_sync_txn(t) for t in (response.added or []))
                all_modified.extend(self._normalize_sync_txn(t) for t in (response.modified or []))
                all_removed.extend(t.transaction_id for t in (response.removed or []))

                has_more = response.has_more
                cursor = response.next_cursor

        except plaid.ApiException as e:
            logger.error(
                "Plaid transactions_sync failed: %s",
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=502,
                detail="Failed to sync transactions from Plaid",
            )

        # Combine added + modified; caller treats them the same
        # (upsert by external_transaction_id).
        combined = all_added + all_modified
        return combined, all_removed

    @staticmethod
    def _normalize_sync_txn(txn) -> dict:
        """Convert a Plaid Transaction object from /transactions/sync
        into the dict format expected by PlaidTransactionSyncService.
        """
        category_list = []
        if hasattr(txn, "category") and txn.category:
            category_list = list(txn.category)

        return {
            "transaction_id": txn.transaction_id,
            "account_id": txn.account_id,
            "date": txn.date.isoformat() if hasattr(txn.date, "isoformat") else str(txn.date),
            "amount": float(txn.amount),
            "name": txn.name or "",
            "merchant_name": getattr(txn, "merchant_name", None) or txn.name or "",
            "category": category_list,
            "pending": getattr(txn, "pending", False),
        }

    async def remove_item(self, access_token: str) -> bool:
        """Call Plaid /item/remove to revoke an access token.

        Returns True on success, raises on failure.
        """
        client = self._get_plaid_api()
        try:
            client.item_remove(ItemRemoveRequest(access_token=access_token))
            return True
        except plaid.ApiException as e:
            logger.error(
                "Plaid item_remove failed: %s",
                e,
                exc_info=True,
            )
            raise

    def _create_dummy_holdings(self) -> Tuple[List[dict], List[dict]]:
        """Create dummy investment holdings for testing."""
        # Securities are the actual stocks/funds
        securities = [
            {
                "security_id": "sec_aapl",
                "ticker_symbol": "AAPL",
                "name": "Apple Inc.",
                "type": "equity",  # equity, derivative, etf, mutual fund, etc.
                "close_price": 185.24,
                "close_price_as_of": utc_now().isoformat(),
            },
            {
                "security_id": "sec_googl",
                "ticker_symbol": "GOOGL",
                "name": "Alphabet Inc.",
                "type": "equity",
                "close_price": 142.65,
                "close_price_as_of": utc_now().isoformat(),
            },
            {
                "security_id": "sec_vtsax",
                "ticker_symbol": "VTSAX",
                "name": "Vanguard Total Stock Market Index Fund",
                "type": "mutual fund",
                "close_price": 118.32,
                "close_price_as_of": utc_now().isoformat(),
            },
            {
                "security_id": "sec_vti",
                "ticker_symbol": "VTI",
                "name": "Vanguard Total Stock Market ETF",
                "type": "etf",
                "close_price": 245.18,
                "close_price_as_of": utc_now().isoformat(),
            },
            {
                "security_id": "sec_msft",
                "ticker_symbol": "MSFT",
                "name": "Microsoft Corporation",
                "type": "equity",
                "close_price": 378.91,
                "close_price_as_of": utc_now().isoformat(),
            },
        ]

        # Holdings link securities to accounts
        holdings = [
            {
                "account_id": "brokerage_acc_id",  # Would match the account_id from exchange
                "security_id": "sec_aapl",
                "quantity": 50.5,
                "cost_basis": 7337.65,  # Total cost
                "institution_price": 185.24,
                "institution_value": 9354.62,
            },
            {
                "account_id": "brokerage_acc_id",
                "security_id": "sec_googl",
                "quantity": 25.0,
                "cost_basis": 3012.50,
                "institution_price": 142.65,
                "institution_value": 3566.25,
            },
            {
                "account_id": "brokerage_acc_id",
                "security_id": "sec_vtsax",
                "quantity": 100.25,
                "cost_basis": 9603.95,
                "institution_price": 118.32,
                "institution_value": 11861.58,
            },
            {
                "account_id": "brokerage_acc_id",
                "security_id": "sec_vti",
                "quantity": 75.0,
                "cost_basis": 15783.75,
                "institution_price": 245.18,
                "institution_value": 18388.50,
            },
            {
                "account_id": "brokerage_acc_id",
                "security_id": "sec_msft",
                "quantity": 30.0,
                "cost_basis": 9456.00,
                "institution_price": 378.91,
                "institution_value": 11367.30,
            },
        ]

        return holdings, securities
