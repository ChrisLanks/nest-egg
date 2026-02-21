"""Plaid API service with test mode for development."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
import uuid
import jwt
from fastapi import HTTPException

from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)


class PlaidService:
    """Service for interacting with Plaid API."""

    def __init__(self):
        """Initialize Plaid service."""

    def is_test_user(self, user: User) -> bool:
        """Check if user is a test user (test@test.com)."""
        return user.email == "test@test.com"

    @staticmethod
    def verify_webhook_signature(
        webhook_verification_header: Optional[str], webhook_body: Dict[str, Any]
    ) -> bool:
        """
        Verify Plaid webhook signature using JWT verification.

        Plaid sends webhooks with a 'Plaid-Verification' header containing a JWT.
        The JWT should be verified using the PLAID_WEBHOOK_SECRET.

        Args:
            webhook_verification_header: Value of 'Plaid-Verification' header
            webhook_body: Webhook request body as dict

        Returns:
            True if signature is valid, raises HTTPException otherwise

        Security Note:
            Webhook signature verification is ALWAYS required for security.
            For development testing, use Plaid's webhook testing tools or set up
            a proper webhook secret even in sandbox mode.
        """
        # Webhook secret is REQUIRED for all webhooks
        if not settings.PLAID_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=500,
                detail="Webhook verification secret not configured. "
                "Set PLAID_WEBHOOK_SECRET even in sandbox mode for security.",
            )

        # Verify webhook signature header is present
        if not webhook_verification_header:
            raise HTTPException(status_code=401, detail="Missing Plaid-Verification header")

        try:
            # Verify JWT signature
            # The JWT contains claims about the webhook (webhook_code, item_id, etc.)
            decoded = jwt.decode(
                webhook_verification_header,
                settings.PLAID_WEBHOOK_SECRET,
                algorithms=["ES256"],  # Plaid uses ES256 (ECDSA with SHA-256)
            )

            # Optional: Verify webhook body matches JWT claims
            # Plaid includes the item_id in the JWT which should match the body
            if decoded.get("request_body_sha256"):
                import hashlib
                import json

                body_str = json.dumps(webhook_body, separators=(",", ":"), sort_keys=True)
                body_hash = hashlib.sha256(body_str.encode()).hexdigest()

                if body_hash != decoded["request_body_sha256"]:
                    raise HTTPException(status_code=401, detail="Webhook body hash mismatch")

            logger.info(f"Webhook signature verified for item: {webhook_body.get('item_id')}")
            return True

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Webhook verification token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid webhook signature: {str(e)}")
        except Exception as e:
            logger.error(f"Webhook verification error: {str(e)}")
            raise HTTPException(status_code=401, detail="Webhook verification failed")

    async def create_link_token(self, user: User) -> Tuple[str, str]:
        """
        Create a Plaid Link token.

        For test@test.com users, returns a dummy token.
        For real users, would call Plaid API.

        Returns:
            Tuple of (link_token, expiration)
        """
        if self.is_test_user(user):
            # Return dummy link token for test user
            dummy_token = f"link-sandbox-{uuid.uuid4()}"
            expiration = (datetime.utcnow() + timedelta(hours=4)).isoformat()
            return dummy_token, expiration

        # TODO: For real users, call Plaid API
        # from plaid import Client
        # client = Client(client_id=..., secret=..., environment='sandbox')
        # response = client.LinkToken.create({...})
        # return response['link_token'], response['expiration']

        raise NotImplementedError("Real Plaid integration not yet implemented")

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
        For real users, would call Plaid API.

        Returns:
            Tuple of (access_token, accounts_list)
        """
        if self.is_test_user(user):
            # Return dummy data for test user
            dummy_access_token = f"access-sandbox-{uuid.uuid4()}"

            # Create dummy accounts based on institution
            dummy_accounts = self._create_dummy_accounts(institution_name or "Test Bank")

            return dummy_access_token, dummy_accounts

        # TODO: For real users, call Plaid API
        # from plaid import Client
        # client = Client(client_id=..., secret=..., environment='sandbox')
        # exchange_response = client.Item.public_token.exchange(public_token)
        # access_token = exchange_response['access_token']
        # item_id = exchange_response['item_id']
        #
        # accounts_response = client.Accounts.get(access_token)
        # accounts = accounts_response['accounts']
        # return access_token, accounts

        raise NotImplementedError("Real Plaid integration not yet implemented")

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

        For test@test.com users, returns cached dummy data.
        For real users, would call Plaid API.
        """
        if self.is_test_user(user):
            # For test users, just return empty list or cached accounts
            return []

        # TODO: For real users, call Plaid API
        # from plaid import Client
        # client = Client(client_id=..., secret=..., environment='sandbox')
        # response = client.Accounts.get(access_token)
        # return response['accounts']

        raise NotImplementedError("Real Plaid integration not yet implemented")

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

        # TODO: For real users, call Plaid API
        # from plaid import Client
        # client = Client(client_id=..., secret=..., environment='sandbox')
        # response = client.InvestmentsHoldings.get(access_token)
        # holdings = response['holdings']
        # securities = response['securities']
        # return holdings, securities

        raise NotImplementedError("Real Plaid holdings integration not yet implemented")

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
                "close_price_as_of": datetime.utcnow().isoformat(),
            },
            {
                "security_id": "sec_googl",
                "ticker_symbol": "GOOGL",
                "name": "Alphabet Inc.",
                "type": "equity",
                "close_price": 142.65,
                "close_price_as_of": datetime.utcnow().isoformat(),
            },
            {
                "security_id": "sec_vtsax",
                "ticker_symbol": "VTSAX",
                "name": "Vanguard Total Stock Market Index Fund",
                "type": "mutual fund",
                "close_price": 118.32,
                "close_price_as_of": datetime.utcnow().isoformat(),
            },
            {
                "security_id": "sec_vti",
                "ticker_symbol": "VTI",
                "name": "Vanguard Total Stock Market ETF",
                "type": "etf",
                "close_price": 245.18,
                "close_price_as_of": datetime.utcnow().isoformat(),
            },
            {
                "security_id": "sec_msft",
                "ticker_symbol": "MSFT",
                "name": "Microsoft Corporation",
                "type": "equity",
                "close_price": 378.91,
                "close_price_as_of": datetime.utcnow().isoformat(),
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
