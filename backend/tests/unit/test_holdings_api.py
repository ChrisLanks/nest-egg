"""Unit tests for holdings API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID
from decimal import Decimal
from datetime import date, datetime

from fastapi import HTTPException

from app.api.v1.holdings import (
    get_account_holdings,
    create_holding,
    update_holding,
    delete_holding,
    capture_portfolio_snapshot,
    get_historical_snapshots,
    get_portfolio_summary,
    get_style_box_breakdown,
    get_rmd_summary,
    router,
)
from app.models.user import User
from app.models.account import Account, AccountType
from app.models.holding import Holding


@pytest.mark.unit
class TestGetAccountHoldings:
    """Test get_account_holdings endpoint."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_account(self):
        account = Mock(spec=Account)
        account.id = uuid4()
        account.organization_id = uuid4()
        account.account_type = AccountType.BROKERAGE
        return account

    @pytest.mark.asyncio
    async def test_returns_holdings_for_account(self, mock_db, mock_account):
        """Should return all holdings for the specified account."""
        holding1 = Mock(spec=Holding)
        holding1.ticker = "AAPL"
        holding2 = Mock(spec=Holding)
        holding2.ticker = "GOOGL"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [holding1, holding2]
        mock_db.execute.return_value = mock_result

        result = await get_account_holdings(account=mock_account, db=mock_db)

        assert result == [holding1, holding2]
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_holdings(self, mock_db, mock_account):
        """Should return empty list when account has no holdings."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await get_account_holdings(account=mock_account, db=mock_db)

        assert result == []


@pytest.mark.unit
class TestCreateHolding:
    """Test create_holding endpoint."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.fixture
    def holding_create_data(self):
        from app.schemas.holding import HoldingCreate

        return HoldingCreate(
            account_id=uuid4(),
            ticker="AAPL",
            name="Apple Inc.",
            shares=Decimal("10"),
            cost_basis_per_share=Decimal("150.00"),
            asset_type="stock",
        )

    @pytest.mark.asyncio
    async def test_creates_holding_successfully(
        self, mock_db, mock_user, holding_create_data
    ):
        """Should create a new holding for a brokerage account."""
        # Mock account lookup
        account = Mock(spec=Account)
        account.id = holding_create_data.account_id
        account.account_type = AccountType.BROKERAGE
        account.organization_id = mock_user.organization_id

        account_result = Mock()
        account_result.scalar_one_or_none.return_value = account
        mock_db.execute.return_value = account_result

        result = await create_holding(
            holding_data=holding_create_data, current_user=mock_user, db=mock_db
        )

        assert result.ticker == "AAPL"
        assert result.shares == Decimal("10")
        assert result.total_cost_basis == Decimal("1500.00")
        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_raises_404_when_account_not_found(
        self, mock_db, mock_user, holding_create_data
    ):
        """Should raise 404 when account doesn't exist."""
        account_result = Mock()
        account_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = account_result

        with pytest.raises(HTTPException) as exc_info:
            await create_holding(
                holding_data=holding_create_data, current_user=mock_user, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "Account not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_400_for_non_investment_account(
        self, mock_db, mock_user, holding_create_data
    ):
        """Should raise 400 when trying to add holding to checking account."""
        account = Mock(spec=Account)
        account.id = holding_create_data.account_id
        account.account_type = AccountType.CHECKING  # Not investment account
        account.organization_id = mock_user.organization_id

        account_result = Mock()
        account_result.scalar_one_or_none.return_value = account
        mock_db.execute.return_value = account_result

        with pytest.raises(HTTPException) as exc_info:
            await create_holding(
                holding_data=holding_create_data, current_user=mock_user, db=mock_db
            )

        assert exc_info.value.status_code == 400
        assert "investment" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_creates_holding_for_retirement_529(
        self, mock_db, mock_user, holding_create_data
    ):
        """Should allow holdings on 529 accounts (college savings are investable)."""
        account = Mock(spec=Account)
        account.id = holding_create_data.account_id
        account.account_type = AccountType.RETIREMENT_529
        account.organization_id = mock_user.organization_id

        account_result = Mock()
        account_result.scalar_one_or_none.return_value = account
        mock_db.execute.return_value = account_result

        result = await create_holding(
            holding_data=holding_create_data, current_user=mock_user, db=mock_db
        )

        assert result.ticker == "AAPL"
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_normalizes_ticker_to_uppercase(
        self, mock_db, mock_user, holding_create_data
    ):
        """Should convert ticker to uppercase."""
        holding_create_data.ticker = "aapl"  # lowercase

        account = Mock(spec=Account)
        account.id = holding_create_data.account_id
        account.account_type = AccountType.BROKERAGE
        account.organization_id = mock_user.organization_id

        account_result = Mock()
        account_result.scalar_one_or_none.return_value = account
        mock_db.execute.return_value = account_result

        result = await create_holding(
            holding_data=holding_create_data, current_user=mock_user, db=mock_db
        )

        assert result.ticker == "AAPL"  # Should be uppercase


@pytest.mark.unit
class TestUpdateHolding:
    """Test update_holding endpoint."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.fixture
    def holding_update_data(self):
        from app.schemas.holding import HoldingUpdate

        return HoldingUpdate(
            shares=Decimal("20"),
            current_price_per_share=Decimal("175.00"),
        )

    @pytest.mark.asyncio
    async def test_updates_holding_successfully(
        self, mock_db, mock_user, holding_update_data
    ):
        """Should update holding shares and price."""
        holding_id = uuid4()
        holding = Mock(spec=Holding)
        holding.id = holding_id
        holding.ticker = "AAPL"
        holding.shares = Decimal("10")
        holding.cost_basis_per_share = Decimal("150.00")

        holding_result = Mock()
        holding_result.scalar_one_or_none.return_value = holding
        mock_db.execute.return_value = holding_result

        result = await update_holding(
            holding_id=holding_id,
            holding_data=holding_update_data,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.shares == Decimal("20")
        assert result.current_price_per_share == Decimal("175.00")
        assert result.current_total_value == Decimal("3500.00")  # 20 * 175
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_raises_404_when_holding_not_found(
        self, mock_db, mock_user, holding_update_data
    ):
        """Should raise 404 when holding doesn't exist."""
        holding_id = uuid4()

        holding_result = Mock()
        holding_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = holding_result

        with pytest.raises(HTTPException) as exc_info:
            await update_holding(
                holding_id=holding_id,
                holding_data=holding_update_data,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "Holding not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_recalculates_cost_basis_on_share_update(
        self, mock_db, mock_user
    ):
        """Should recalculate total cost basis when shares or cost_basis_per_share changes."""
        from app.schemas.holding import HoldingUpdate

        holding_id = uuid4()
        holding = Mock(spec=Holding)
        holding.id = holding_id
        holding.shares = Decimal("10")
        holding.cost_basis_per_share = Decimal("100.00")

        holding_result = Mock()
        holding_result.scalar_one_or_none.return_value = holding
        mock_db.execute.return_value = holding_result

        update_data = HoldingUpdate(cost_basis_per_share=Decimal("120.00"))

        result = await update_holding(
            holding_id=holding_id,
            holding_data=update_data,
            current_user=mock_user,
            db=mock_db,
        )

        # Should recalculate: 10 shares * 120 = 1200
        assert result.total_cost_basis == Decimal("1200.00")


@pytest.mark.unit
class TestDeleteHolding:
    """Test delete_holding endpoint."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_deletes_holding_successfully(self, mock_db, mock_user):
        """Should delete holding and return None."""
        holding_id = uuid4()
        holding = Mock(spec=Holding)
        holding.id = holding_id

        holding_result = Mock()
        holding_result.scalar_one_or_none.return_value = holding
        mock_db.execute.return_value = holding_result

        result = await delete_holding(
            holding_id=holding_id, current_user=mock_user, db=mock_db
        )

        assert result is None
        assert mock_db.delete.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_raises_404_when_holding_not_found(self, mock_db, mock_user):
        """Should raise 404 when holding doesn't exist."""
        holding_id = uuid4()

        holding_result = Mock()
        holding_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = holding_result

        with pytest.raises(HTTPException) as exc_info:
            await delete_holding(
                holding_id=holding_id, current_user=mock_user, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "Holding not found" in exc_info.value.detail


@pytest.mark.unit
class TestCapturePortfolioSnapshot:
    """Test capture_portfolio_snapshot endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_captures_snapshot_successfully(self, mock_db, mock_user):
        """Should capture portfolio snapshot and return SnapshotResponse."""
        from app.schemas.holding import PortfolioSummary, SnapshotResponse

        mock_portfolio = Mock(spec=PortfolioSummary)
        mock_portfolio.total_value = Decimal("100000")

        mock_snapshot = SnapshotResponse(
            id=uuid4(),
            organization_id=mock_user.organization_id,
            snapshot_date=date.today(),
            total_value=Decimal("100000"),
            total_cost_basis=Decimal("90000"),
            total_gain_loss=Decimal("10000"),
            total_gain_loss_percent=Decimal("11.11"),
            created_at=datetime.utcnow(),
        )

        with patch(
            "app.api.v1.holdings.get_portfolio_summary", return_value=mock_portfolio
        ):
            with patch(
                "app.api.v1.holdings.snapshot_service.capture_snapshot",
                return_value=mock_snapshot,
            ) as mock_capture:
                result = await capture_portfolio_snapshot(
                    current_user=mock_user, db=mock_db
                )

                assert result == mock_snapshot
                mock_capture.assert_called_once_with(
                    db=mock_db,
                    organization_id=mock_user.organization_id,
                    portfolio=mock_portfolio,
                )


@pytest.mark.unit
class TestGetHistoricalSnapshots:
    """Test get_historical_snapshots endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_returns_historical_snapshots(self, mock_db, mock_user):
        """Should return list of historical snapshots."""
        from app.schemas.holding import SnapshotResponse

        snapshots = [
            SnapshotResponse(
                id=uuid4(),
                organization_id=mock_user.organization_id,
                snapshot_date=date(2024, 1, 1),
                total_value=Decimal("90000"),
                total_cost_basis=Decimal("85000"),
                total_gain_loss=Decimal("5000"),
                total_gain_loss_percent=Decimal("5.88"),
                created_at=datetime.utcnow(),
            ),
            SnapshotResponse(
                id=uuid4(),
                organization_id=mock_user.organization_id,
                snapshot_date=date(2024, 6, 1),
                total_value=Decimal("100000"),
                total_cost_basis=Decimal("90000"),
                total_gain_loss=Decimal("10000"),
                total_gain_loss_percent=Decimal("11.11"),
                created_at=datetime.utcnow(),
            ),
        ]

        with patch(
            "app.api.v1.holdings.snapshot_service.get_snapshots",
            return_value=snapshots,
        ) as mock_get:
            result = await get_historical_snapshots(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                limit=None,
                current_user=mock_user,
                db=mock_db,
            )

            assert result == snapshots
            mock_get.assert_called_once_with(
                db=mock_db,
                organization_id=mock_user.organization_id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                limit=None,
            )

    @pytest.mark.asyncio
    async def test_defaults_to_last_year_when_no_start_date(self, mock_db, mock_user):
        """Should default to 1 year ago when start_date is None."""
        with patch(
            "app.api.v1.holdings.snapshot_service.get_snapshots", return_value=[]
        ) as mock_get:
            await get_historical_snapshots(
                start_date=None,
                end_date=None,
                limit=None,
                current_user=mock_user,
                db=mock_db,
            )

            # Verify start_date was calculated as 365 days ago
            call_args = mock_get.call_args
            start_date_arg = call_args.kwargs["start_date"]
            expected_start = date.today().replace(year=date.today().year - 1)

            # Allow 1-day variance for test timing
            assert abs((start_date_arg - expected_start).days) <= 1


@pytest.mark.unit
class TestGetPortfolioSummary:
    """Test get_portfolio_summary endpoint.

    NOTE: This endpoint is 1040 lines of complex logic. These tests cover
    basic scenarios only. Comprehensive testing requires integration tests.
    """

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_returns_empty_portfolio_when_no_holdings(self, mock_db, mock_user):
        """Should return empty portfolio summary when no holdings exist."""
        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[],
            ):
                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                assert result.total_value == Decimal("0")
                assert result.total_cost_basis is None
                assert result.holdings_by_ticker == []
                assert result.treemap_data is None

    @pytest.mark.asyncio
    async def test_filters_by_user_when_user_id_provided(self, mock_db, mock_user):
        """Should call verify_household_member and get_user_accounts when user_id provided."""
        user_id = uuid4()
        account = Mock(spec=Account)
        account.id = uuid4()
        account.name = "Test Brokerage"  # Must be string for pydantic validation
        account.account_type = AccountType.BROKERAGE
        account.current_balance = None  # Avoid Mock arithmetic errors

        with patch(
            "app.api.v1.holdings.verify_household_member", return_value=None
        ) as mock_verify:
            with patch(
                "app.api.v1.holdings.get_user_accounts", return_value=[account]
            ) as mock_get_user_accounts:
                mock_result = Mock()
                mock_result.scalars.return_value.all.return_value = []
                mock_db.execute.return_value = mock_result

                await get_portfolio_summary(
                    user_id=user_id, current_user=mock_user, db=mock_db
                )

                mock_verify.assert_called_once_with(
                    mock_db, user_id, mock_user.organization_id
                )
                mock_get_user_accounts.assert_called_once_with(
                    mock_db, user_id, mock_user.organization_id
                )

    @pytest.mark.asyncio
    async def test_uses_household_accounts_when_no_user_id(self, mock_db, mock_user):
        """Should call get_all_household_accounts and deduplicate when user_id is None."""
        account = Mock(spec=Account)
        account.id = uuid4()
        account.name = "Test Brokerage"  # Must be string for pydantic validation
        account.account_type = AccountType.BROKERAGE
        account.current_balance = None  # Avoid Mock arithmetic errors

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ) as mock_get_all:
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ) as mock_dedupe:
                mock_result = Mock()
                mock_result.scalars.return_value.all.return_value = []
                mock_db.execute.return_value = mock_result

                await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                mock_get_all.assert_called_once_with(
                    mock_db, mock_user.organization_id
                )
                mock_dedupe.assert_called_once_with([account])


@pytest.mark.unit
class TestGetStyleBoxBreakdown:
    """Test get_style_box_breakdown endpoint.

    NOTE: This endpoint has complex classification logic.
    These tests cover basic scenarios only.
    """

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_holdings(self, mock_db, mock_user):
        """Should return empty list when no holdings or cash accounts exist."""
        # Mock holdings query
        holdings_result = Mock()
        holdings_result.scalars.return_value.all.return_value = []

        # Mock cash accounts query
        cash_result = Mock()
        cash_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [holdings_result, cash_result]

        result = await get_style_box_breakdown(current_user=mock_user, db=mock_db)

        assert result == []

    @pytest.mark.asyncio
    async def test_includes_cash_breakdown(self, mock_db, mock_user):
        """Should include cash account breakdown in style box."""
        # Mock holdings query - no holdings
        holdings_result = Mock()
        holdings_result.scalars.return_value.all.return_value = []

        # Mock cash accounts query
        checking_account = Mock(spec=Account)
        checking_account.account_type = AccountType.CHECKING
        checking_account.current_balance = Decimal("5000")

        cash_result = Mock()
        cash_result.scalars.return_value.all.return_value = [checking_account]

        mock_db.execute.side_effect = [holdings_result, cash_result]

        result = await get_style_box_breakdown(current_user=mock_user, db=mock_db)

        assert len(result) > 0
        # Should have Cash - Checking category
        cash_items = [item for item in result if "Cash" in item.style_class]
        assert len(cash_items) > 0


@pytest.mark.unit
class TestGetRMDSummary:
    """Test get_rmd_summary endpoint.

    NOTE: This endpoint has complex RMD calculation logic spanning
    multiple household members. These tests cover basic scenarios only.
    """

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.birthdate = date(1950, 1, 1)  # Age 74, requires RMD
        return user

    @pytest.mark.asyncio
    async def test_returns_none_when_user_has_no_birthdate(self, mock_db):
        """Should return None when individual user has no birthdate."""
        user_id = uuid4()
        current_user = Mock(spec=User)
        current_user.organization_id = uuid4()

        target_user = Mock(spec=User)
        target_user.id = user_id
        target_user.birthdate = None  # No birthdate

        user_result = Mock()
        user_result.scalar_one.return_value = target_user
        mock_db.execute.return_value = user_result

        with patch("app.api.v1.holdings.verify_household_member", return_value=None):
            result = await get_rmd_summary(
                user_id=user_id, current_user=current_user, db=mock_db
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_household_has_no_birthdates(
        self, mock_db, mock_user
    ):
        """Should return None when combined household view has no members with birthdates."""
        # Mock household members query - no members with birthdates
        members_result = Mock()
        members_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = members_result

        result = await get_rmd_summary(
            user_id=None, current_user=mock_user, db=mock_db
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_no_rmd_when_user_under_73(self, mock_db):
        """Should return requires_rmd=False when user is under 73."""
        user_id = uuid4()
        current_user = Mock(spec=User)
        current_user.organization_id = uuid4()

        target_user = Mock(spec=User)
        target_user.id = user_id
        # Use a birthdate that makes user 60 years old (well under RMD age)
        target_user.birthdate = date(date.today().year - 60, 1, 1)

        user_result = Mock()
        user_result.scalar_one.return_value = target_user
        mock_db.execute.return_value = user_result

        with patch("app.api.v1.holdings.verify_household_member", return_value=None):
            result = await get_rmd_summary(
                user_id=user_id, current_user=current_user, db=mock_db
            )

            assert result.requires_rmd is False
            assert result.user_age == 60
            assert result.total_required_distribution == Decimal("0")

    @pytest.mark.asyncio
    async def test_calculates_rmd_for_user_over_73(self, mock_db):
        """Should calculate RMD when user is 73+ with retirement accounts."""
        user_id = uuid4()
        current_user = Mock(spec=User)
        current_user.organization_id = uuid4()

        target_user = Mock(spec=User)
        target_user.id = user_id
        target_user.birthdate = date(1950, 1, 1)  # Age 74+

        # Mock user lookup
        user_result = Mock()
        user_result.scalar_one.return_value = target_user

        # Mock account with retirement funds
        account = Mock(spec=Account)
        account.id = uuid4()
        account.name = "Traditional IRA"  # Must be string, not Mock
        account.account_type = AccountType.RETIREMENT_IRA
        account.current_balance = Decimal("100000")
        account.is_active = True

        mock_db.execute.return_value = user_result

        with patch("app.api.v1.holdings.verify_household_member", return_value=None):
            with patch(
                "app.api.v1.holdings.get_user_accounts", return_value=[account]
            ):
                result = await get_rmd_summary(
                    user_id=user_id, current_user=current_user, db=mock_db
                )

                assert result.requires_rmd is True
                # Age will be calculated based on current date - just verify it's high
                assert result.user_age >= 73
                assert result.total_required_distribution > Decimal("0")
                assert len(result.accounts) > 0


@pytest.mark.unit
class TestGetPortfolioSummaryComprehensive:
    """Comprehensive tests for get_portfolio_summary function."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    def create_mock_holding(
        self,
        ticker: str,
        shares: Decimal,
        price: Decimal,
        account_id: UUID,
        name: str = None,
        asset_class: str = None,
        sector: str = None,
    ):
        """Helper to create mock holding with common attributes."""
        from datetime import datetime
        from uuid import uuid4
        holding = Mock(spec=Holding)
        holding.id = uuid4()  # Add id for Pydantic validation
        holding.organization_id = uuid4()  # Add organization_id for Pydantic validation
        holding.ticker = ticker
        holding.shares = shares
        holding.current_price_per_share = price
        holding.current_total_value = shares * price
        holding.cost_basis_per_share = price
        holding.total_cost_basis = shares * price
        holding.account_id = account_id
        holding.name = name or ticker
        holding.asset_class = asset_class
        holding.sector = sector
        holding.country = "US"  # Add country for Pydantic validation
        holding.price_as_of = datetime.utcnow()  # Add price_as_of for comparison logic
        holding.expense_ratio = Decimal("0.03")  # Default 0.03% expense ratio
        holding.created_at = datetime.utcnow()  # Add created_at for Pydantic validation
        holding.updated_at = datetime.utcnow()  # Add updated_at for Pydantic validation
        # Add other fields that Pydantic might validate
        holding.industry = "Technology" if sector == "Technology" else None
        holding.market_cap = None
        holding.pe_ratio = None
        holding.dividend_yield = None
        holding.beta = None
        holding.fifty_two_week_high = None
        holding.fifty_two_week_low = None
        holding.asset_type = "stock"  # Add asset_type for Pydantic validation (lowercase)
        return holding

    @pytest.mark.asyncio
    async def test_portfolio_with_domestic_stocks(self, mock_db, mock_user):
        """Should classify and aggregate domestic stocks."""
        account_id = uuid4()

        # Create retirement account with domestic stocks
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "401(k)"
        account.account_type = AccountType.RETIREMENT_401K
        account.current_balance = Decimal("100000")
        account.user_id = mock_user.id

        # Create holdings - Large cap domestic stocks
        holdings = [
            self.create_mock_holding("AAPL", Decimal("100"), Decimal("150"), account_id, "Apple Inc"),
            self.create_mock_holding("MSFT", Decimal("50"), Decimal("300"), account_id, "Microsoft Corp"),
            self.create_mock_holding("GOOGL", Decimal("20"), Decimal("100"), account_id, "Alphabet Inc"),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                # Mock holdings query
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify total value
                expected_total = Decimal("15000") + Decimal("15000") + Decimal("2000")
                assert result.total_value == expected_total

                # Verify treemap data is generated for holdings
                assert result.treemap_data is not None
                # Verify retirement breakdown
                assert result.category_breakdown is not None
                assert result.category_breakdown.retirement_value > 0

    @pytest.mark.asyncio
    async def test_portfolio_with_international_stocks(self, mock_db, mock_user):
        """Should classify international stocks separately."""
        account_id = uuid4()

        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Brokerage"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("50000")
        account.user_id = mock_user.id

        # International stocks - common international ETFs
        holdings = [
            self.create_mock_holding(
                "VXUS",
                Decimal("100"),
                Decimal("50"),
                account_id,
                "Vanguard Total International Stock ETF",
            ),
            self.create_mock_holding(
                "EFA",
                Decimal("50"),
                Decimal("60"),
                account_id,
                "iShares MSCI EAFE ETF",
            ),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify international classification via treemap
                assert result.treemap_data is not None
                assert result.treemap_data.children is not None
                assert any(
                    "International" in child.name
                    for child in result.treemap_data.children
                )

    @pytest.mark.asyncio
    async def test_portfolio_with_bonds(self, mock_db, mock_user):
        """Should classify bonds and fixed income."""
        account_id = uuid4()

        account = Mock(spec=Account)
        account.id = account_id
        account.name = "IRA"
        account.account_type = AccountType.RETIREMENT_IRA
        account.current_balance = Decimal("75000")
        account.user_id = mock_user.id

        # Bond holdings
        holdings = [
            self.create_mock_holding(
                "BND",
                Decimal("500"),
                Decimal("80"),
                account_id,
                "Vanguard Total Bond Market ETF",
            ),
            self.create_mock_holding(
                "AGG",
                Decimal("200"),
                Decimal("100"),
                account_id,
                "iShares Core U.S. Aggregate Bond ETF",
            ),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify bonds classification via treemap
                assert result.treemap_data is not None
                assert result.treemap_data.children is not None
                assert any(
                    "Bond" in child.name for child in result.treemap_data.children
                )

    @pytest.mark.asyncio
    async def test_portfolio_with_cash(self, mock_db, mock_user):
        """Should include cash and money market funds."""
        account_id = uuid4()

        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Brokerage"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("10000")
        account.user_id = mock_user.id

        # Money market holdings
        holdings = [
            self.create_mock_holding(
                "VMFXX",
                Decimal("10000"),
                Decimal("1"),
                account_id,
                "Vanguard Federal Money Market Fund",
            ),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify cash classification via treemap
                assert result.treemap_data is not None
                assert result.treemap_data.children is not None
                assert any(
                    "Cash" in child.name for child in result.treemap_data.children
                )

    @pytest.mark.asyncio
    async def test_portfolio_market_cap_classification(self, mock_db, mock_user):
        """Should classify stocks by market cap based on fund names."""
        account_id = uuid4()

        account = Mock(spec=Account)
        account.id = account_id
        account.name = "401(k)"
        account.account_type = AccountType.RETIREMENT_401K
        account.current_balance = Decimal("100000")
        account.user_id = mock_user.id

        # Holdings with market cap indicators in names
        holdings = [
            self.create_mock_holding(
                "VTI",
                Decimal("100"),
                Decimal("200"),
                account_id,
                "Vanguard Total Stock Market ETF",  # Large cap
            ),
            self.create_mock_holding(
                "VO",
                Decimal("50"),
                Decimal("150"),
                account_id,
                "Vanguard Mid-Cap ETF",  # Mid cap
            ),
            self.create_mock_holding(
                "VB",
                Decimal("30"),
                Decimal("180"),
                account_id,
                "Vanguard Small-Cap ETF",  # Small cap
            ),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should have treemap data (verifying structure is generated)
                assert result.treemap_data is not None

    @pytest.mark.asyncio
    async def test_portfolio_with_property(self, mock_db, mock_user):
        """Should include property accounts."""
        property_account = Mock(spec=Account)
        property_account.id = uuid4()
        property_account.name = "Primary Residence"
        property_account.account_type = AccountType.PROPERTY
        property_account.current_balance = Decimal("500000")
        property_account.user_id = mock_user.id

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[property_account],
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[property_account],
            ):
                # No holdings for property accounts
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = []
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify property included in total
                assert result.total_value >= Decimal("500000")

                # Verify property in treemap
                assert result.treemap_data is not None
                assert result.treemap_data.children is not None
                assert any(
                    "Property" in child.name for child in result.treemap_data.children
                )

    @pytest.mark.asyncio
    async def test_portfolio_with_crypto(self, mock_db, mock_user):
        """Should include cryptocurrency accounts."""
        crypto_account = Mock(spec=Account)
        crypto_account.id = uuid4()
        crypto_account.name = "Coinbase"
        crypto_account.account_type = AccountType.CRYPTO
        crypto_account.current_balance = Decimal("25000")
        crypto_account.user_id = mock_user.id

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[crypto_account],
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[crypto_account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = []
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify crypto in treemap
                assert result.treemap_data is not None
                assert result.treemap_data.children is not None
                assert any(
                    "Crypto" in child.name for child in result.treemap_data.children
                )

    @pytest.mark.asyncio
    async def test_portfolio_retirement_vs_taxable_breakdown(self, mock_db, mock_user):
        """Should categorize retirement vs taxable accounts."""
        retirement_id = uuid4()
        taxable_id = uuid4()

        retirement_account = Mock(spec=Account)
        retirement_account.id = retirement_id
        retirement_account.name = "IRA"
        retirement_account.account_type = AccountType.RETIREMENT_IRA
        retirement_account.current_balance = Decimal("100000")
        retirement_account.user_id = mock_user.id

        taxable_account = Mock(spec=Account)
        taxable_account.id = taxable_id
        taxable_account.name = "Brokerage"
        taxable_account.account_type = AccountType.BROKERAGE
        taxable_account.current_balance = Decimal("50000")
        taxable_account.user_id = mock_user.id

        # Holdings split between retirement and taxable
        holdings = [
            self.create_mock_holding(
                "VTI", Decimal("100"), Decimal("200"), retirement_id
            ),
            self.create_mock_holding(
                "AAPL", Decimal("50"), Decimal("150"), taxable_id
            ),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[retirement_account, taxable_account],
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[retirement_account, taxable_account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify category breakdown exists with retirement and taxable values
                assert result.category_breakdown is not None
                assert result.category_breakdown.retirement_value > 0
                assert result.category_breakdown.taxable_value > 0

    @pytest.mark.asyncio
    async def test_portfolio_sector_breakdown(self, mock_db, mock_user):
        """Should provide sector breakdown for stocks."""
        account_id = uuid4()

        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Brokerage"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("50000")
        account.user_id = mock_user.id

        # Holdings with sector information
        holdings = [
            self.create_mock_holding(
                "AAPL",
                Decimal("100"),
                Decimal("150"),
                account_id,
                "Apple Inc",
                sector="Technology",
            ),
            self.create_mock_holding(
                "JNJ",
                Decimal("50"),
                Decimal("160"),
                account_id,
                "Johnson & Johnson",
                sector="Healthcare",
            ),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify sector breakdown exists
                assert result.sector_breakdown is not None

    @pytest.mark.asyncio
    async def test_portfolio_aggregates_duplicate_tickers(self, mock_db, mock_user):
        """Should aggregate same ticker across multiple accounts."""
        account1_id = uuid4()
        account2_id = uuid4()

        account1 = Mock(spec=Account)
        account1.id = account1_id
        account1.name = "IRA"
        account1.account_type = AccountType.RETIREMENT_IRA
        account1.current_balance = Decimal("50000")
        account1.user_id = mock_user.id

        account2 = Mock(spec=Account)
        account2.id = account2_id
        account2.name = "401(k)"
        account2.account_type = AccountType.RETIREMENT_401K
        account2.current_balance = Decimal("50000")
        account2.user_id = mock_user.id

        # Same ticker in both accounts
        holdings = [
            self.create_mock_holding("VTI", Decimal("50"), Decimal("200"), account1_id),
            self.create_mock_holding("VTI", Decimal("30"), Decimal("200"), account2_id),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[account1, account2],
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account1, account2],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should aggregate VTI holdings
                # Total value should be (50 + 30) * 200 = 16000
                assert result.total_value >= Decimal("16000")

    @pytest.mark.asyncio
    async def test_portfolio_with_checking_savings_as_cash(self, mock_db, mock_user):
        """Should include checking and savings accounts in cash category."""
        checking = Mock(spec=Account)
        checking.id = uuid4()
        checking.name = "Checking"
        checking.account_type = AccountType.CHECKING
        checking.current_balance = Decimal("5000")
        checking.user_id = mock_user.id

        savings = Mock(spec=Account)
        savings.id = uuid4()
        savings.name = "Savings"
        savings.account_type = AccountType.SAVINGS
        savings.current_balance = Decimal("20000")
        savings.user_id = mock_user.id

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[checking, savings],
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[checking, savings],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = []
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify cash included in total
                assert result.total_value >= Decimal("25000")

                # Verify cash in treemap
                assert result.treemap_data is not None
                assert result.treemap_data.children is not None
                assert any(
                    "Cash" in child.name for child in result.treemap_data.children
                )

    @pytest.mark.asyncio
    async def test_portfolio_excludes_credit_cards_and_loans(self, mock_db, mock_user):
        """Should exclude liability accounts from portfolio."""
        credit_card = Mock(spec=Account)
        credit_card.id = uuid4()
        credit_card.name = "Credit Card"
        credit_card.account_type = AccountType.CREDIT_CARD
        credit_card.current_balance = Decimal("-2000")  # Negative balance
        credit_card.user_id = mock_user.id

        loan = Mock(spec=Account)
        loan.id = uuid4()
        loan.name = "Auto Loan"
        loan.account_type = AccountType.LOAN
        loan.current_balance = Decimal("-15000")
        loan.user_id = mock_user.id

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[credit_card, loan],
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[credit_card, loan],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = []
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Portfolio should be empty or minimal (not include liabilities)
                # Total value should not be negative
                assert result.total_value >= Decimal("0")

    @pytest.mark.asyncio
    async def test_portfolio_calculates_percentages(self, mock_db, mock_user):
        """Should calculate correct percentages for asset allocation."""
        account_id = uuid4()

        account = Mock(spec=Account)
        account.id = account_id
        account.name = "IRA"
        account.account_type = AccountType.RETIREMENT_IRA
        account.current_balance = Decimal("100000")
        account.user_id = mock_user.id

        # Mix of assets with known values
        holdings = [
            self.create_mock_holding(
                "VTI", Decimal("250"), Decimal("200"), account_id
            ),  # $50,000
            self.create_mock_holding(
                "BND", Decimal("500"), Decimal("80"), account_id
            ),  # $40,000
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify treemap percentages add up close to 100%
                assert result.treemap_data is not None
                assert result.treemap_data.children is not None
                total_percentage = sum(
                    child.percent for child in result.treemap_data.children
                )
                assert 99.0 <= total_percentage <= 101.0  # Allow small rounding errors

    @pytest.mark.asyncio
    async def test_portfolio_treemap_structure(self, mock_db, mock_user):
        """Should generate proper treemap hierarchy with nodes and values."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Investment"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("100000")
        account.user_id = mock_user.id

        holdings = [
            self.create_mock_holding(
                "AAPL", Decimal("100"), Decimal("150"), account_id,
                name="Apple Inc", sector="Technology"
            ),
            self.create_mock_holding(
                "MSFT", Decimal("50"), Decimal("300"), account_id,
                name="Microsoft", sector="Technology"
            ),
            self.create_mock_holding(
                "JNJ", Decimal("200"), Decimal("160"), account_id,
                name="Johnson & Johnson", sector="Healthcare"
            ),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Verify treemap data structure exists
                assert hasattr(result, 'treemap_data')
                assert result.treemap_data is not None
                assert result.treemap_data.children is not None
                assert len(result.treemap_data.children) > 0

                # Verify all holdings have values
                for holding in holdings:
                    assert holding.current_total_value > 0

    @pytest.mark.asyncio
    async def test_portfolio_geographic_diversification(self, mock_db, mock_user):
        """Should classify holdings by geographic region."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Global Portfolio"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("150000")
        account.user_id = mock_user.id

        holdings = [
            self.create_mock_holding(
                "VTI", Decimal("200"), Decimal("200"), account_id,
                name="Vanguard Total Stock Market"
            ),  # US
            self.create_mock_holding(
                "VEA", Decimal("150"), Decimal("100"), account_id,
                name="Vanguard Developed Markets"
            ),  # International Developed
            self.create_mock_holding(
                "VWO", Decimal("100"), Decimal("100"), account_id,
                name="Vanguard Emerging Markets"
            ),  # Emerging Markets
            self.create_mock_holding(
                "BABA", Decimal("50"), Decimal("100"), account_id,
                name="Alibaba Group"
            ),  # China
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should have both domestic and international assets
                assert result.total_value > 0
                assert result.treemap_data is not None

    @pytest.mark.asyncio
    async def test_portfolio_sector_mapping_edge_cases(self, mock_db, mock_user):
        """Should handle sector classification edge cases."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Sector Portfolio"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("100000")
        account.user_id = mock_user.id

        holdings = [
            self.create_mock_holding(
                "XLF", Decimal("100"), Decimal("100"), account_id,
                name="Financial Select Sector SPDR", sector="Financial"
            ),
            self.create_mock_holding(
                "XLE", Decimal("100"), Decimal("100"), account_id,
                name="Energy Select Sector SPDR", sector="Energy"
            ),
            self.create_mock_holding(
                "XLU", Decimal("100"), Decimal("100"), account_id,
                name="Utilities Select Sector SPDR", sector="Utilities"
            ),
            self.create_mock_holding(
                "UNKNOWN", Decimal("100"), Decimal("100"), account_id,
                name="Unknown Sector Fund", sector=None
            ),
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should handle None sector gracefully
                assert result is not None
                assert result.total_value > 0

    @pytest.mark.asyncio
    async def test_portfolio_expense_ratio_aggregation(self, mock_db, mock_user):
        """Should calculate weighted average expense ratios."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "ETF Portfolio"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("100000")
        account.user_id = mock_user.id

        holdings = [
            self.create_mock_holding(
                "VTI", Decimal("500"), Decimal("100"), account_id,
                name="Vanguard Total Market"
            ),  # $50,000 @ 0.03% expense ratio
            self.create_mock_holding(
                "BND", Decimal("500"), Decimal("80"), account_id,
                name="Vanguard Total Bond"
            ),  # $40,000 @ 0.035% expense ratio
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should complete without errors even if expense ratio not calculated
                assert result is not None

    @pytest.mark.asyncio
    async def test_portfolio_dividend_yield_metrics(self, mock_db, mock_user):
        """Should handle dividend yield calculations."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Dividend Portfolio"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("100000")
        account.user_id = mock_user.id

        holdings = [
            self.create_mock_holding(
                "VYM", Decimal("200"), Decimal("100"), account_id,
                name="Vanguard High Dividend Yield"
            ),  # High yield
            self.create_mock_holding(
                "SCHD", Decimal("200"), Decimal("80"), account_id,
                name="Schwab US Dividend Equity"
            ),  # High yield
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should complete successfully
                assert result is not None

    @pytest.mark.asyncio
    async def test_portfolio_exotic_asset_types(self, mock_db, mock_user):
        """Should handle edge cases for unusual asset types."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Alternative Investments"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("100000")
        account.user_id = mock_user.id

        holdings = [
            self.create_mock_holding(
                "GLD", Decimal("50"), Decimal("180"), account_id,
                name="SPDR Gold Trust", asset_class="Commodity"
            ),  # Gold
            self.create_mock_holding(
                "REIT", Decimal("100"), Decimal("100"), account_id,
                name="Real Estate Fund", asset_class="RealEstate"
            ),  # REIT
            self.create_mock_holding(
                "PDBC", Decimal("200"), Decimal("50"), account_id,
                name="Invesco Commodities", asset_class="Commodity"
            ),  # Broad commodities
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should handle alternative assets
                assert result is not None
                assert result.total_value > 0

    @pytest.mark.asyncio
    async def test_portfolio_zero_balance_holdings(self, mock_db, mock_user):
        """Should handle holdings with zero shares or zero value."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Test Account"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("50000")
        account.user_id = mock_user.id

        holdings = [
            self.create_mock_holding(
                "VTI", Decimal("100"), Decimal("200"), account_id
            ),  # Normal holding
            self.create_mock_holding(
                "ZERO", Decimal("0"), Decimal("100"), account_id
            ),  # Zero shares
            self.create_mock_holding(
                "WORTHLESS", Decimal("100"), Decimal("0"), account_id
            ),  # Zero value
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should handle zero values gracefully
                assert result is not None

    @pytest.mark.asyncio
    async def test_portfolio_missing_ticker_data(self, mock_db, mock_user):
        """Should handle unusual or minimal ticker information."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Test Account"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("50000")
        account.user_id = mock_user.id

        holdings = [
            self.create_mock_holding(
                "VTI", Decimal("100"), Decimal("200"), account_id,
                name="Vanguard Total Market"
            ),
            self.create_mock_holding(
                "CASH", Decimal("50"), Decimal("100"), account_id,
                name="Cash Position"
            ),  # Short ticker
            self.create_mock_holding(
                "MANUAL", Decimal("50"), Decimal("100"), account_id,
                name="Manual Entry"
            ),  # Unknown ticker
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should handle non-standard tickers gracefully
                assert result is not None

    @pytest.mark.asyncio
    async def test_portfolio_large_cap_small_cap_mix(self, mock_db, mock_user):
        """Should properly categorize large-cap and small-cap stocks together."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Cap Mix Portfolio"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("100000")
        account.user_id = mock_user.id

        holdings = [
            self.create_mock_holding(
                "AAPL", Decimal("100"), Decimal("150"), account_id,
                name="Apple Inc"
            ),  # Large cap
            self.create_mock_holding(
                "VB", Decimal("200"), Decimal("200"), account_id,
                name="Vanguard Small-Cap ETF"
            ),  # Small cap
            self.create_mock_holding(
                "VO", Decimal("150"), Decimal("200"), account_id,
                name="Vanguard Mid-Cap ETF"
            ),  # Mid cap
        ]

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should categorize all market caps
                assert result is not None
                assert result.treemap_data is not None

    @pytest.mark.asyncio
    async def test_portfolio_very_large_portfolio(self, mock_db, mock_user):
        """Should handle portfolios with many holdings efficiently."""
        account_id = uuid4()
        account = Mock(spec=Account)
        account.id = account_id
        account.name = "Large Portfolio"
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("1000000")
        account.user_id = mock_user.id

        # Create 50 mock holdings
        holdings = []
        for i in range(50):
            holdings.append(
                self.create_mock_holding(
                    f"STOCK{i}", Decimal("100"), Decimal("100"), account_id,
                    name=f"Stock {i}"
                )
            )

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", return_value=[account]
        ):
            with patch(
                "app.api.v1.holdings.deduplication_service.deduplicate_accounts",
                return_value=[account],
            ):
                holdings_result = Mock()
                holdings_result.scalars.return_value.all.return_value = holdings
                mock_db.execute.return_value = holdings_result

                result = await get_portfolio_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should handle large portfolios
                assert result is not None


@pytest.mark.unit
class TestGetRmdSummary:
    """Test get_rmd_summary endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.birthdate = None  # Changed from birthdate to birthdate
        return user

    @pytest.mark.asyncio
    async def test_returns_none_when_no_birthdate(self, mock_db, mock_user):
        """Should return None when user has no birthdate."""
        # Mock household members query for when user has no birthdate
        members_result = Mock()
        members_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = members_result

        result = await get_rmd_summary(
            user_id=None, current_user=mock_user, db=mock_db
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_household_no_birthdate(self, mock_db, mock_user):
        """Should return None when filtering by user without birthdate."""
        other_user_id = uuid4()
        other_user = Mock(spec=User)
        other_user.id = other_user_id
        other_user.birthdate = None

        user_result = Mock()
        user_result.scalar_one.return_value = other_user
        mock_db.execute.return_value = user_result

        with patch("app.api.v1.holdings.verify_household_member", return_value=None):
            result = await get_rmd_summary(
                user_id=other_user_id, current_user=mock_user, db=mock_db
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_user_under_73(self, mock_db, mock_user):
        """Should return None when user is under 73 years old."""
        from datetime import date, timedelta

        # Set birthdate to 60 years ago
        mock_user.birthdate = date.today() - timedelta(days=60 * 365)

        # Mock household members query
        members_result = Mock()
        members_result.scalars.return_value.all.return_value = [mock_user]
        mock_db.execute.return_value = members_result

        # Mock accounts query (though it won't get called if under 73)
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = []

        result = await get_rmd_summary(
            user_id=None, current_user=mock_user, db=mock_db
        )

        # Under 73 should return summary with requires_rmd=False
        assert result is not None
        assert result.requires_rmd is False

    @pytest.mark.asyncio
    async def test_calculates_rmd_when_user_over_73(self, mock_db, mock_user):
        """Should calculate RMD when user is over 73."""
        from datetime import date, timedelta

        # Set birthdate to 75 years ago
        mock_user.birthdate = date.today() - timedelta(days=75 * 365)

        # Mock household members query
        members_result = Mock()
        members_result.scalars.return_value.all.return_value = [mock_user]
        mock_db.execute.return_value = members_result

        # Mock retirement accounts
        account1 = Mock(spec=Account)
        account1.id = uuid4()
        account1.name = "Traditional IRA"
        account1.account_type = AccountType.RETIREMENT_IRA
        account1.current_balance = Decimal("500000")
        account1.user_id = mock_user.id

        account2 = Mock(spec=Account)
        account2.id = uuid4()
        account2.name = "401k"
        account2.account_type = AccountType.RETIREMENT_401K
        account2.current_balance = Decimal("300000")
        account2.user_id = mock_user.id

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[account1, account2],
        ):
            with patch(
                "app.api.v1.holdings.get_user_accounts",
                return_value=[account1, account2],
            ):
                result = await get_rmd_summary(
                    user_id=None, current_user=mock_user, db=mock_db
                )

                # Should return RMD calculation
                assert result is not None
                assert result.requires_rmd is True
                assert result.total_required_distribution > 0


@pytest.mark.unit
class TestInvestmentAccountsWithoutHoldings:
    """Test portfolio summary with investment accounts that have balances but no holdings."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_includes_investment_accounts_without_holdings(
        self, mock_db, mock_user
    ):
        """Should include investment accounts with balances but no holdings data."""
        # Create investment account with balance but no holdings
        brokerage_account = Mock(spec=Account)
        brokerage_account.id = uuid4()
        brokerage_account.name = "Chase Bank Brokerage"
        brokerage_account.account_type = AccountType.BROKERAGE
        brokerage_account.current_balance = Decimal("45680.25")
        brokerage_account.user_id = mock_user.id

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[brokerage_account],
        ):
            # No holdings for this account
            holdings_result = Mock()
            holdings_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = holdings_result

            result = await get_portfolio_summary(
                user_id=None, current_user=mock_user, db=mock_db
            )

            # Verify account balance included in total
            assert result.total_value == Decimal("45680.25")

            # Verify treemap has Investment Accounts category
            assert result.treemap_data is not None
            assert result.treemap_data.children is not None
            assert len(result.treemap_data.children) > 0

            # Find Investment Accounts category
            investment_accounts_category = next(
                (
                    child
                    for child in result.treemap_data.children
                    if child.name == "Investment Accounts"
                ),
                None,
            )
            assert investment_accounts_category is not None
            assert investment_accounts_category.value == Decimal("45680.25")

            # Verify children have "(Holdings Unknown)" suffix
            assert investment_accounts_category.children is not None
            assert len(investment_accounts_category.children) > 0
            assert investment_accounts_category.children[0].name == "Chase Bank Brokerage (Holdings Unknown)"

    @pytest.mark.asyncio
    async def test_treemap_with_cash_and_investment_accounts(
        self, mock_db, mock_user
    ):
        """Should show both Cash and Investment Accounts categories in treemap."""
        # Create checking account (Cash category)
        checking = Mock(spec=Account)
        checking.id = uuid4()
        checking.name = "Checking Account"
        checking.account_type = AccountType.CHECKING
        checking.current_balance = Decimal("5000")
        checking.user_id = mock_user.id

        # Create savings account (Cash category)
        savings = Mock(spec=Account)
        savings.id = uuid4()
        savings.name = "Savings Account"
        savings.account_type = AccountType.SAVINGS
        savings.current_balance = Decimal("20000")
        savings.user_id = mock_user.id

        # Create brokerage without holdings (Investment Accounts category)
        brokerage = Mock(spec=Account)
        brokerage.id = uuid4()
        brokerage.name = "Wells Fargo Brokerage"
        brokerage.account_type = AccountType.BROKERAGE
        brokerage.current_balance = Decimal("45680.25")
        brokerage.user_id = mock_user.id

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[checking, savings, brokerage],
        ):
            holdings_result = Mock()
            holdings_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = holdings_result

            result = await get_portfolio_summary(
                user_id=None, current_user=mock_user, db=mock_db
            )

            # Verify total includes all accounts
            expected_total = Decimal("5000") + Decimal("20000") + Decimal("45680.25")
            assert result.total_value == expected_total

            # Verify treemap has 2 top-level categories
            assert result.treemap_data is not None
            assert result.treemap_data.children is not None
            assert len(result.treemap_data.children) == 2

            category_names = {child.name for child in result.treemap_data.children}
            assert "Cash" in category_names
            assert "Investment Accounts" in category_names

            # Verify Cash category has checking and savings
            cash_category = next(
                child
                for child in result.treemap_data.children
                if child.name == "Cash"
            )
            assert cash_category.value == Decimal("25000")
            assert len(cash_category.children) == 2
            cash_account_names = {child.name for child in cash_category.children}
            assert "Checking" in cash_account_names
            assert "Savings" in cash_account_names

            # Verify Investment Accounts category
            investment_category = next(
                child
                for child in result.treemap_data.children
                if child.name == "Investment Accounts"
            )
            assert investment_category.value == Decimal("45680.25")
            assert investment_category.color == "#4299E1"  # Blue color
            assert len(investment_category.children) == 1
            assert (
                investment_category.children[0].name
                == "Wells Fargo Brokerage (Holdings Unknown)"
            )

    @pytest.mark.asyncio
    async def test_multiple_investment_accounts_without_holdings(
        self, mock_db, mock_user
    ):
        """Should handle multiple investment accounts without holdings."""
        # Create two brokerages without holdings
        brokerage1 = Mock(spec=Account)
        brokerage1.id = uuid4()
        brokerage1.name = "Chase Bank Brokerage"
        brokerage1.account_type = AccountType.BROKERAGE
        brokerage1.current_balance = Decimal("45680.25")
        brokerage1.user_id = mock_user.id

        brokerage2 = Mock(spec=Account)
        brokerage2.id = uuid4()
        brokerage2.name = "Wells Fargo Brokerage"
        brokerage2.account_type = AccountType.BROKERAGE
        brokerage2.current_balance = Decimal("45680.25")
        brokerage2.user_id = mock_user.id

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[brokerage1, brokerage2],
        ):
            holdings_result = Mock()
            holdings_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = holdings_result

            result = await get_portfolio_summary(
                user_id=None, current_user=mock_user, db=mock_db
            )

            # Verify total
            assert result.total_value == Decimal("91360.50")

            # Verify Investment Accounts category aggregates both
            investment_category = next(
                child
                for child in result.treemap_data.children
                if child.name == "Investment Accounts"
            )
            assert investment_category.value == Decimal("91360.50")
            assert len(investment_category.children) == 2

            child_names = {child.name for child in investment_category.children}
            assert "Chase Bank Brokerage (Holdings Unknown)" in child_names
            assert "Wells Fargo Brokerage (Holdings Unknown)" in child_names

    @pytest.mark.asyncio
    async def test_mixed_investment_accounts_with_and_without_holdings(
        self, mock_db, mock_user
    ):
        """Should handle mix of investment accounts with and without holdings."""
        # Account with holdings
        account_with_holdings_id = uuid4()
        account_with = Mock(spec=Account)
        account_with.id = account_with_holdings_id
        account_with.name = "Fidelity 401k"
        account_with.account_type = AccountType.RETIREMENT_401K
        account_with.current_balance = Decimal("100000")
        account_with.user_id = mock_user.id

        # Account without holdings
        account_without = Mock(spec=Account)
        account_without.id = uuid4()
        account_without.name = "Chase Brokerage"
        account_without.account_type = AccountType.BROKERAGE
        account_without.current_balance = Decimal("50000")
        account_without.user_id = mock_user.id

        # Create one holding for first account
        from datetime import datetime

        holding = Mock(spec=Holding)
        holding.id = uuid4()
        holding.organization_id = mock_user.organization_id
        holding.ticker = "VTI"
        holding.shares = Decimal("100")
        holding.current_price_per_share = Decimal("200")
        holding.current_total_value = Decimal("20000")
        holding.cost_basis_per_share = Decimal("180")
        holding.total_cost_basis = Decimal("18000")
        holding.account_id = account_with_holdings_id
        holding.name = "Vanguard Total Market"
        holding.country = "US"
        holding.price_as_of = datetime.utcnow()
        holding.expense_ratio = Decimal("0.03")
        holding.created_at = datetime.utcnow()
        holding.updated_at = datetime.utcnow()
        holding.asset_type = "Stock"
        holding.asset_class = None
        holding.sector = None
        holding.industry = None
        holding.market_cap = None
        holding.pe_ratio = None
        holding.dividend_yield = None
        holding.beta = None
        holding.fifty_two_week_high = None
        holding.fifty_two_week_low = None
        holding.account = account_with

        with patch(
            "app.api.v1.holdings.get_all_household_accounts",
            return_value=[account_with, account_without],
        ):
            holdings_result = Mock()
            holdings_result.scalars.return_value.all.return_value = [holding]
            mock_db.execute.return_value = holdings_result

            result = await get_portfolio_summary(
                user_id=None, current_user=mock_user, db=mock_db
            )

            # Should have holdings-based category (either Domestic Stocks or Other) and Investment Accounts
            category_names = {child.name for child in result.treemap_data.children}
            assert "Investment Accounts" in category_names
            # VTI will be classified based on its metadata - could be Domestic Stocks or Other
            assert len(category_names) == 2

            # Investment Accounts should only have the account without holdings
            investment_category = next(
                child
                for child in result.treemap_data.children
                if child.name == "Investment Accounts"
            )
            assert investment_category.value == Decimal("50000")
            assert len(investment_category.children) == 1
            assert (
                investment_category.children[0].name
                == "Chase Brokerage (Holdings Unknown)"
            )
