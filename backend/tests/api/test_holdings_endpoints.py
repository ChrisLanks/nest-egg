"""Tests for holdings API endpoints."""

import pytest
from decimal import Decimal
from uuid import uuid4

from app.models.holding import Holding
from app.models.account import Account, AccountType
from app.models.user import User


class TestHoldingsEndpoints:
    """Test suite for holdings API endpoints."""

    @pytest.mark.asyncio
    async def test_get_portfolio_summary_empty(self, async_client, auth_headers, test_user):
        """Should return empty portfolio when no holdings exist."""
        response = await async_client.get("/api/v1/holdings/portfolio", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_value"] == "0"
        # total_cost_basis is None when there are no holdings (API returns None for 0)
        assert data["total_cost_basis"] is None or data["total_cost_basis"] == "0"
        assert data["holdings_by_ticker"] == []
        assert data["holdings_by_account"] == []

    @pytest.mark.asyncio
    async def test_get_portfolio_summary_with_holdings(self, async_client, auth_headers, test_user, db):
        """Should calculate portfolio summary with holdings."""
        # Create brokerage account
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        # Create holding
        holding = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="AAPL",
            name="Apple Inc.",
            shares=Decimal("10.0"),
            cost_basis_per_share=Decimal("150.00"),
            total_cost_basis=Decimal("1500.00"),
            current_price_per_share=Decimal("180.00"),
            current_total_value=Decimal("1800.00"),
            asset_type="stock",
            sector="Technology",
        )
        db.add(holding)
        await db.commit()

        response = await async_client.get("/api/v1/holdings/portfolio", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert float(data["total_value"]) == 1800.0
        assert float(data["total_cost_basis"]) == 1500.0
        assert float(data["total_gain_loss"]) == 300.0
        assert len(data["holdings_by_ticker"]) == 1
        assert data["holdings_by_ticker"][0]["ticker"] == "AAPL"
        assert len(data["holdings_by_account"]) == 1

    @pytest.mark.asyncio
    async def test_get_portfolio_aggregates_by_ticker(self, async_client, auth_headers, test_user, db):
        """Should aggregate holdings across accounts by ticker."""
        # Create two brokerage accounts
        account1 = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage 1",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        account2 = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage 2",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add_all([account1, account2])
        await db.commit()

        # Create same ticker in both accounts
        holding1 = Holding(
            organization_id=test_user.organization_id,
            account_id=account1.id,
            ticker="VTI",
            name="Vanguard Total Stock Market ETF",
            shares=Decimal("5.0"),
            current_price_per_share=Decimal("200.00"),
            current_total_value=Decimal("1000.00"),
            total_cost_basis=Decimal("900.00"),
            asset_type="etf",
        )
        holding2 = Holding(
            organization_id=test_user.organization_id,
            account_id=account2.id,
            ticker="VTI",
            name="Vanguard Total Stock Market ETF",
            shares=Decimal("3.0"),
            current_price_per_share=Decimal("200.00"),
            current_total_value=Decimal("600.00"),
            total_cost_basis=Decimal("540.00"),
            asset_type="etf",
        )
        db.add_all([holding1, holding2])
        await db.commit()

        response = await async_client.get("/api/v1/holdings/portfolio", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Should aggregate to single ticker entry
        assert len(data["holdings_by_ticker"]) == 1
        ticker_data = data["holdings_by_ticker"][0]
        assert ticker_data["ticker"] == "VTI"
        assert float(ticker_data["total_shares"]) == 8.0  # 5 + 3
        assert float(ticker_data["total_cost_basis"]) == 1440.0  # 900 + 540

    @pytest.mark.asyncio
    async def test_get_portfolio_category_breakdown(self, async_client, auth_headers, test_user, db):
        """Should calculate retirement vs taxable breakdown."""
        # Create retirement account
        retirement = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="401k",
            account_type=AccountType.RETIREMENT_401K,
            is_active=True,
        )
        # Create taxable brokerage
        brokerage = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add_all([retirement, brokerage])
        await db.commit()

        # Holdings in retirement
        ret_holding = Holding(
            organization_id=test_user.organization_id,
            account_id=retirement.id,
            ticker="VTSAX",
            shares=Decimal("100.0"),
            current_price_per_share=Decimal("100.00"),
            current_total_value=Decimal("10000.00"),
            asset_type="mutual_fund",
        )
        # Holdings in taxable
        tax_holding = Holding(
            organization_id=test_user.organization_id,
            account_id=brokerage.id,
            ticker="VOO",
            shares=Decimal("20.0"),
            current_price_per_share=Decimal("400.00"),
            current_total_value=Decimal("8000.00"),
            asset_type="etf",
        )
        db.add_all([ret_holding, tax_holding])
        await db.commit()

        response = await async_client.get("/api/v1/holdings/portfolio", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert float(data["category_breakdown"]["retirement_value"]) == 10000.0
        assert float(data["category_breakdown"]["taxable_value"]) == 8000.0
        # Percentages
        assert abs(float(data["category_breakdown"]["retirement_percent"]) - 55.56) < 0.1
        assert abs(float(data["category_breakdown"]["taxable_percent"]) - 44.44) < 0.1

    @pytest.mark.asyncio
    async def test_get_account_holdings(self, async_client, auth_headers, test_user, db):
        """Should get all holdings for specific account."""
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        # Create multiple holdings
        for ticker in ["AAPL", "MSFT", "GOOGL"]:
            holding = Holding(
                organization_id=test_user.organization_id,
                account_id=account.id,
                ticker=ticker,
                shares=Decimal("10.0"),
                current_price_per_share=Decimal("100.00"),
            )
            db.add(holding)
        await db.commit()

        response = await async_client.get(f"/api/v1/holdings/account/{account.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        tickers = {h["ticker"] for h in data}
        assert tickers == {"AAPL", "MSFT", "GOOGL"}

    @pytest.mark.asyncio
    async def test_get_account_holdings_cross_org_blocked(
        self, async_client, auth_headers, test_user, db, second_organization
    ):
        """Should not allow access to accounts from other orgs."""
        other_account = Account(
            id=uuid4(),
            organization_id=second_organization.id,
            user_id=test_user.id,
            name="Other Account",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(other_account)
        await db.commit()

        response = await async_client.get(
            f"/api/v1/holdings/account/{other_account.id}", headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_holding_success(self, async_client, auth_headers, test_user, db):
        """Should create new holding."""
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        payload = {
            "account_id": str(account.id),
            "ticker": "tsla",  # lowercase to test normalization
            "name": "Tesla Inc.",
            "shares": "5.5",
            "cost_basis_per_share": "200.00",
            "asset_type": "stock",
        }

        response = await async_client.post("/api/v1/holdings/", headers=auth_headers, json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == "TSLA"  # Should be uppercase
        assert float(data["shares"]) == 5.5
        assert float(data["cost_basis_per_share"]) == 200.0
        assert float(data["total_cost_basis"]) == 1100.0  # 5.5 * 200

    @pytest.mark.asyncio
    async def test_create_holding_invalid_account(self, async_client, auth_headers, test_user):
        """Should reject holding for non-existent account."""
        fake_account_id = uuid4()

        payload = {
            "account_id": str(fake_account_id),
            "ticker": "AAPL",
            "shares": "10.0",
        }

        response = await async_client.post("/api/v1/holdings/", headers=auth_headers, json=payload)

        assert response.status_code == 404
        assert "Account not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_holding_non_investment_account(self, async_client, auth_headers, test_user, db):
        """Should reject holding for non-investment account."""
        # Create checking account (not investment type)
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        payload = {
            "account_id": str(account.id),
            "ticker": "AAPL",
            "shares": "10.0",
        }

        response = await async_client.post("/api/v1/holdings/", headers=auth_headers, json=payload)

        assert response.status_code == 400
        assert "investment" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_holding(self, async_client, auth_headers, test_user, db):
        """Should update holding details."""
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        holding = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="AAPL",
            shares=Decimal("10.0"),
            cost_basis_per_share=Decimal("150.00"),
            total_cost_basis=Decimal("1500.00"),
        )
        db.add(holding)
        await db.commit()

        # Update shares and price
        payload = {
            "shares": "15.0",
            "current_price_per_share": "180.00",
        }

        response = await async_client.patch(
            f"/api/v1/holdings/{holding.id}", headers=auth_headers, json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["shares"]) == 15.0
        assert float(data["current_price_per_share"]) == 180.0
        assert float(data["current_total_value"]) == 2700.0  # 15 * 180

    @pytest.mark.asyncio
    async def test_update_holding_recalculates_cost_basis(
        self, async_client, auth_headers, test_user, db
    ):
        """Should recalculate total cost basis when cost per share changes."""
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        holding = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="AAPL",
            shares=Decimal("10.0"),
            cost_basis_per_share=Decimal("150.00"),
            total_cost_basis=Decimal("1500.00"),
        )
        db.add(holding)
        await db.commit()

        # Update cost basis per share
        payload = {
            "cost_basis_per_share": "160.00",
        }

        response = await async_client.patch(
            f"/api/v1/holdings/{holding.id}", headers=auth_headers, json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["cost_basis_per_share"]) == 160.0
        assert float(data["total_cost_basis"]) == 1600.0  # 10 * 160

    @pytest.mark.asyncio
    async def test_update_holding_cross_org_blocked(self, async_client, auth_headers, test_user, db, second_organization):
        """Should not allow updating holdings from other orgs."""
        other_account = Account(
            id=uuid4(),
            organization_id=second_organization.id,
            user_id=test_user.id,
            name="Other Account",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(other_account)
        await db.commit()

        other_holding = Holding(
            organization_id=second_organization.id,
            account_id=other_account.id,
            ticker="AAPL",
            shares=Decimal("10.0"),
        )
        db.add(other_holding)
        await db.commit()

        payload = {"shares": "20.0"}

        response = await async_client.patch(
            f"/api/v1/holdings/{other_holding.id}", headers=auth_headers, json=payload
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_holding(self, async_client, auth_headers, test_user, db):
        """Should delete holding."""
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        holding = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="AAPL",
            shares=Decimal("10.0"),
        )
        db.add(holding)
        await db.commit()
        holding_id = holding.id

        response = await async_client.delete(f"/api/v1/holdings/{holding_id}", headers=auth_headers)

        assert response.status_code == 204

        # Verify deleted
        response = await async_client.get(f"/api/v1/holdings/account/{account.id}", headers=auth_headers)
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_holding_cross_org_blocked(self, async_client, auth_headers, test_user, db, second_organization):
        """Should not allow deleting holdings from other orgs."""
        other_account = Account(
            id=uuid4(),
            organization_id=second_organization.id,
            user_id=test_user.id,
            name="Other Account",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(other_account)
        await db.commit()

        other_holding = Holding(
            organization_id=second_organization.id,
            account_id=other_account.id,
            ticker="AAPL",
            shares=Decimal("10.0"),
        )
        db.add(other_holding)
        await db.commit()

        response = await async_client.delete(f"/api/v1/holdings/{other_holding.id}", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_portfolio_filters_inactive_accounts(self, async_client, auth_headers, test_user, db):
        """Should exclude holdings from inactive accounts."""
        active_account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Active",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        inactive_account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Inactive",
            account_type=AccountType.BROKERAGE,
            is_active=False,
        )
        db.add_all([active_account, inactive_account])
        await db.commit()

        # Holdings in both
        active_holding = Holding(
            organization_id=test_user.organization_id,
            account_id=active_account.id,
            ticker="AAPL",
            shares=Decimal("10.0"),
            current_price_per_share=Decimal("100.00"),
            current_total_value=Decimal("1000.00"),
        )
        inactive_holding = Holding(
            organization_id=test_user.organization_id,
            account_id=inactive_account.id,
            ticker="MSFT",
            shares=Decimal("10.0"),
            current_price_per_share=Decimal("100.00"),
            current_total_value=Decimal("1000.00"),
        )
        db.add_all([active_holding, inactive_holding])
        await db.commit()

        response = await async_client.get("/api/v1/holdings/portfolio", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Should only include active account holding
        assert len(data["holdings_by_ticker"]) == 1
        assert data["holdings_by_ticker"][0]["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_portfolio_user_filter(self, async_client, auth_headers, test_user, db):
        """Should filter portfolio by specific user."""
        # Create another user in same org
        other_user = User(
            id=uuid4(),
            organization_id=test_user.organization_id,
            email="other@example.com",
            password_hash="hashed",
            is_active=True,
        )
        db.add(other_user)
        await db.commit()

        # Account for test_user
        user_account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="User Account",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        # Account for other_user
        other_account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=other_user.id,
            name="Other Account",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add_all([user_account, other_account])
        await db.commit()

        # Holdings
        user_holding = Holding(
            organization_id=test_user.organization_id,
            account_id=user_account.id,
            ticker="AAPL",
            shares=Decimal("10.0"),
            current_price_per_share=Decimal("100.00"),
            current_total_value=Decimal("1000.00"),
        )
        other_holding = Holding(
            organization_id=test_user.organization_id,
            account_id=other_account.id,
            ticker="MSFT",
            shares=Decimal("10.0"),
            current_price_per_share=Decimal("100.00"),
            current_total_value=Decimal("1000.00"),
        )
        db.add_all([user_holding, other_holding])
        await db.commit()

        # Filter by test_user
        response = await async_client.get(
            f"/api/v1/holdings/portfolio?user_id={test_user.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should only include test_user's holdings
        assert len(data["holdings_by_ticker"]) == 1
        assert data["holdings_by_ticker"][0]["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_geographic_breakdown(self, async_client, auth_headers, test_user, db):
        """Should calculate domestic vs international breakdown."""
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        # Domestic stock
        domestic = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="AAPL",
            shares=Decimal("10.0"),
            current_price_per_share=Decimal("180.00"),
            current_total_value=Decimal("1800.00"),
            asset_type="stock",
            asset_class="domestic",
        )
        # International stock
        international = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="VXUS",  # Known international ticker
            shares=Decimal("10.0"),
            current_price_per_share=Decimal("100.00"),
            current_total_value=Decimal("1000.00"),
            asset_type="etf",
            asset_class="international",
        )
        db.add_all([domestic, international])
        await db.commit()

        response = await async_client.get("/api/v1/holdings/portfolio", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        geo = data["geographic_breakdown"]
        assert float(geo["domestic_value"]) > 0
        assert float(geo["international_value"]) > 0

    @pytest.mark.asyncio
    async def test_expense_ratio_aggregation(self, async_client, auth_headers, test_user, db):
        """Should calculate total annual fees from expense ratios."""
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        # Holding with expense ratio
        holding = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="VTSAX",
            shares=Decimal("100.0"),
            current_price_per_share=Decimal("100.00"),
            current_total_value=Decimal("10000.00"),
            expense_ratio=Decimal("0.0003"),  # 0.03%
            asset_type="mutual_fund",
        )
        db.add(holding)
        await db.commit()

        response = await async_client.get("/api/v1/holdings/portfolio", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Annual fee = 10000 * 0.0003 = 3.00
        assert float(data["total_annual_fees"]) == 3.0

    @pytest.mark.asyncio
    async def test_sector_breakdown(self, async_client, auth_headers, test_user, db):
        """Should aggregate holdings by sector."""
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        # Tech sector
        tech1 = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="AAPL",
            shares=Decimal("10.0"),
            current_price_per_share=Decimal("180.00"),
            current_total_value=Decimal("1800.00"),
            sector="Technology",
        )
        tech2 = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="MSFT",
            shares=Decimal("5.0"),
            current_price_per_share=Decimal("400.00"),
            current_total_value=Decimal("2000.00"),
            sector="Technology",
        )
        # Healthcare sector
        healthcare = Holding(
            organization_id=test_user.organization_id,
            account_id=account.id,
            ticker="JNJ",
            shares=Decimal("10.0"),
            current_price_per_share=Decimal("160.00"),
            current_total_value=Decimal("1600.00"),
            sector="Healthcare",
        )
        db.add_all([tech1, tech2, healthcare])
        await db.commit()

        response = await async_client.get("/api/v1/holdings/portfolio", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        sectors = data["sector_breakdown"]
        assert len(sectors) == 2
        # Should be ordered by value descending
        assert sectors[0]["sector"] == "Technology"
        assert float(sectors[0]["value"]) == 3800.0  # 1800 + 2000
        assert sectors[0]["count"] == 2
        assert sectors[1]["sector"] == "Healthcare"
        assert float(sectors[1]["value"]) == 1600.0

    @pytest.mark.asyncio
    async def test_holdings_not_found(self, async_client, auth_headers):
        """Should return 404 for non-existent holding."""
        fake_id = uuid4()

        response = await async_client.patch(
            f"/api/v1/holdings/{fake_id}", headers=auth_headers, json={"shares": "10.0"}
        )

        assert response.status_code == 404

        response = await async_client.delete(f"/api/v1/holdings/{fake_id}", headers=auth_headers)

        assert response.status_code == 404
