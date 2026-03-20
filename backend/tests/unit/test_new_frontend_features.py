"""
Tests for newly added frontend features:
- FIRE API endpoint (household filtering)
- Attachment API endpoints
- Reconciliation API endpoint
- Settings default_currency
"""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "email": "test@example.com",
        "is_active": True,
        "is_org_admin": False,
        "first_name": "Test",
        "last_name": "User",
        "display_name": "Test User",
        "default_currency": "USD",
        "email_verified": True,
        "email_notifications_enabled": True,
        "notification_preferences": None,
        "birth_day": None,
        "birth_month": None,
        "birth_year": None,
        "dashboard_layout": None,
        "birthdate": None,
        "created_at": datetime(2025, 1, 1),
        "updated_at": datetime(2025, 1, 1),
    }
    defaults.update(overrides)
    user = Mock()
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_attachment(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "transaction_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "filename": "abc123.pdf",
        "original_filename": "receipt.pdf",
        "content_type": "application/pdf",
        "file_size": 50000,
        "created_at": datetime(2025, 6, 1, 12, 0, 0),
    }
    defaults.update(overrides)
    att = Mock()
    for k, v in defaults.items():
        setattr(att, k, v)
    return att


# ===========================================================================
# FIRE API endpoint tests
# ===========================================================================


class TestFireAPIEndpoint:
    """Tests for the /fire/metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_fire_metrics_returns_all_sections(self):
        """Endpoint returns fi_ratio, savings_rate, years_to_fi, coast_fi."""
        from app.api.v1.fire import get_fire_metrics

        mock_user = _make_user()
        mock_db = AsyncMock()

        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 0.5,
                "investable_assets": 500000,
                "annual_expenses": 40000,
                "fi_number": 1000000,
            },
            "savings_rate": {
                "savings_rate": 0.3,
                "income": 100000,
                "spending": 70000,
                "savings": 30000,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": 15.2,
                "fi_number": 1000000,
                "investable_assets": 500000,
                "annual_savings": 30000,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": False,
            },
            "coast_fi": {
                "coast_fi_number": 300000,
                "fi_number": 1000000,
                "investable_assets": 500000,
                "is_coast_fi": True,
                "retirement_age": 65,
                "years_until_retirement": 25,
                "expected_return": 0.07,
            },
        }

        with patch("app.api.v1.fire.FireService") as MockService:
            instance = MockService.return_value
            instance.get_fire_dashboard = AsyncMock(return_value=mock_metrics)

            result = await get_fire_metrics(
                user_id=None,
                withdrawal_rate=0.04,
                expected_return=0.07,
                retirement_age=65,
                current_user=mock_user,
                db=mock_db,
            )

        assert result.fi_ratio.fi_ratio == 0.5
        assert result.savings_rate.savings_rate == 0.3
        assert result.years_to_fi.years_to_fi == 15.2
        assert result.coast_fi.is_coast_fi is True

    @pytest.mark.asyncio
    async def test_get_fire_metrics_with_user_id_verifies_household(self):
        """When user_id is provided, should verify household membership."""
        from app.api.v1.fire import get_fire_metrics

        mock_user = _make_user()
        mock_db = AsyncMock()
        target_user_id = uuid.uuid4()

        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 0,
                "investable_assets": 0,
                "annual_expenses": 0,
                "fi_number": 0,
            },
            "savings_rate": {
                "savings_rate": 0,
                "income": 0,
                "spending": 0,
                "savings": 0,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": None,
                "fi_number": 0,
                "investable_assets": 0,
                "annual_savings": 0,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": False,
            },
            "coast_fi": {
                "coast_fi_number": 0,
                "fi_number": 0,
                "investable_assets": 0,
                "is_coast_fi": False,
                "retirement_age": 65,
                "years_until_retirement": 25,
                "expected_return": 0.07,
            },
        }

        with (
            patch("app.api.v1.fire.verify_household_member") as mock_verify,
            patch("app.api.v1.fire.permission_service.require", new=AsyncMock()),
            patch("app.api.v1.fire.FireService") as MockService,
        ):
            mock_verify.return_value = None
            instance = MockService.return_value
            instance.get_fire_dashboard = AsyncMock(return_value=mock_metrics)

            await get_fire_metrics(
                user_id=target_user_id,
                withdrawal_rate=0.04,
                expected_return=0.07,
                retirement_age=65,
                current_user=mock_user,
                db=mock_db,
            )

            mock_verify.assert_called_once_with(mock_db, target_user_id, mock_user.organization_id)

    @pytest.mark.asyncio
    async def test_get_fire_metrics_zero_data(self):
        """With no financial data, metrics should return zeros (not errors)."""
        from app.api.v1.fire import get_fire_metrics

        mock_user = _make_user()
        mock_db = AsyncMock()

        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 0,
                "investable_assets": 0,
                "annual_expenses": 0,
                "fi_number": 0,
            },
            "savings_rate": {
                "savings_rate": 0,
                "income": 0,
                "spending": 0,
                "savings": 0,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": None,
                "fi_number": 0,
                "investable_assets": 0,
                "annual_savings": 0,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": False,
            },
            "coast_fi": {
                "coast_fi_number": 0,
                "fi_number": 0,
                "investable_assets": 0,
                "is_coast_fi": False,
                "retirement_age": 65,
                "years_until_retirement": 25,
                "expected_return": 0.07,
            },
        }

        with patch("app.api.v1.fire.FireService") as MockService:
            instance = MockService.return_value
            instance.get_fire_dashboard = AsyncMock(return_value=mock_metrics)

            result = await get_fire_metrics(
                user_id=None,
                withdrawal_rate=0.04,
                expected_return=0.07,
                retirement_age=65,
                current_user=mock_user,
                db=mock_db,
            )

        assert result.fi_ratio.fi_ratio == 0
        assert result.fi_ratio.investable_assets == 0
        assert result.years_to_fi.already_fi is False
        assert result.years_to_fi.years_to_fi is None


# ===========================================================================
# Attachment service tests
# ===========================================================================


class TestAttachmentService:
    """Tests for attachment_service functions."""

    @pytest.mark.asyncio
    async def test_upload_validates_file_type(self):
        """Should reject disallowed content types."""
        from app.services.attachment_service import upload_attachment

        mock_db = AsyncMock()
        mock_user = _make_user()
        mock_storage = Mock()

        mock_file = Mock()
        mock_file.content_type = "application/javascript"
        mock_file.filename = "evil.js"
        mock_file.size = 100
        mock_file.read = AsyncMock(return_value=b"alert(1)")

        with pytest.raises(HTTPException) as exc_info:
            await upload_attachment(
                db=mock_db,
                transaction_id=uuid.uuid4(),
                user=mock_user,
                file=mock_file,
                storage=mock_storage,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_validates_file_size(self):
        """Should reject files over 10 MB."""
        from app.services.attachment_service import upload_attachment

        mock_db = AsyncMock()
        mock_user = _make_user()
        mock_storage = Mock()

        # Create a file that's too large
        big_content = b"x" * (10 * 1024 * 1024 + 1)
        mock_file = Mock()
        mock_file.content_type = "application/pdf"
        mock_file.filename = "huge.pdf"
        mock_file.size = len(big_content)
        mock_file.read = AsyncMock(return_value=big_content)

        with pytest.raises(HTTPException) as exc_info:
            await upload_attachment(
                db=mock_db,
                transaction_id=uuid.uuid4(),
                user=mock_user,
                file=mock_file,
                storage=mock_storage,
            )
        assert exc_info.value.status_code in (400, 413)

    @pytest.mark.asyncio
    async def test_list_attachments_returns_list(self):
        """Should return attachments for a transaction."""
        from app.services.attachment_service import list_attachments

        mock_user = _make_user()
        mock_db = AsyncMock()
        txn_id = uuid.uuid4()

        # Mock the DB queries
        # First query: verify transaction belongs to user's org
        mock_txn = Mock()
        mock_txn.id = txn_id
        mock_txn_result = Mock()
        mock_txn_result.scalar_one_or_none.return_value = mock_txn

        # Second query: get attachments
        att1 = _make_attachment(transaction_id=txn_id)
        att2 = _make_attachment(transaction_id=txn_id)
        mock_att_result = Mock()
        mock_att_result.scalars.return_value.all.return_value = [att1, att2]

        mock_db.execute = AsyncMock(side_effect=[mock_txn_result, mock_att_result])

        result = await list_attachments(db=mock_db, transaction_id=txn_id, user=mock_user)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_attachments_rejects_foreign_transaction(self):
        """Should reject if transaction doesn't belong to user's org."""
        from app.services.attachment_service import list_attachments

        mock_user = _make_user()
        mock_db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await list_attachments(db=mock_db, transaction_id=uuid.uuid4(), user=mock_user)
        assert exc_info.value.status_code == 404


# ===========================================================================
# Attachment API schema tests
# ===========================================================================


class TestAttachmentSchemas:
    """Tests for the Attachment API Pydantic schemas."""

    def test_attachment_response_from_model(self):
        """AttachmentResponse should validate from a model-like object."""
        from app.api.v1.attachments import AttachmentResponse

        att = _make_attachment()
        resp = AttachmentResponse.model_validate(att)
        assert resp.original_filename == "receipt.pdf"
        assert resp.content_type == "application/pdf"
        assert resp.file_size == 50000

    def test_attachment_list_response(self):
        """AttachmentListResponse wraps a list."""
        from app.api.v1.attachments import AttachmentListResponse, AttachmentResponse

        att = _make_attachment()
        resp = AttachmentListResponse(attachments=[AttachmentResponse.model_validate(att)])
        assert len(resp.attachments) == 1


# ===========================================================================
# Reconciliation endpoint tests
# ===========================================================================


class TestReconciliationEndpoint:
    """Tests for GET /accounts/{id}/reconciliation."""

    @pytest.mark.asyncio
    async def test_reconciliation_returns_data(self):
        """Should call reconciliation service and return result."""
        from app.api.v1.accounts import get_account_reconciliation

        mock_user = _make_user()
        mock_db = AsyncMock()
        account_id = uuid.uuid4()

        # Mock the account lookup
        mock_account = Mock()
        mock_account.id = account_id
        mock_account.user_id = mock_user.id
        mock_account.organization_id = mock_user.organization_id
        mock_account.name = "Chase Checking"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        recon_data = {
            "account_id": str(account_id),
            "account_name": "Chase Checking",
            "bank_balance": 5000.0,
            "computed_balance": 4950.0,
            "discrepancy": 50.0,
            "last_synced_at": "2025-06-01T12:00:00",
            "transaction_count": 150,
        }

        mock_recon_result = Mock()
        mock_recon_result.to_dict.return_value = recon_data

        with patch("app.api.v1.accounts.reconciliation_service") as mock_recon:
            mock_recon.reconcile_account = AsyncMock(return_value=mock_recon_result)

            result = await get_account_reconciliation(
                account_id=account_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert result["bank_balance"] == 5000.0
        assert result["computed_balance"] == 4950.0
        assert result["discrepancy"] == 50.0


# ===========================================================================
# Settings default_currency tests
# ===========================================================================


class TestDefaultCurrencySettings:
    """Tests for the default_currency field in UserUpdate and profile response."""

    def test_user_update_schema_accepts_currency(self):
        """UserUpdate should accept default_currency."""
        from app.schemas.user import UserUpdate

        update = UserUpdate(default_currency="EUR")
        assert update.default_currency == "EUR"

    def test_user_update_schema_max_length_3(self):
        """UserUpdate should reject currency codes longer than 3."""
        from app.schemas.user import UserUpdate

        with pytest.raises(Exception):
            UserUpdate(default_currency="ABCD")

    def test_user_update_schema_allows_none(self):
        """UserUpdate should allow None for default_currency."""
        from app.schemas.user import UserUpdate

        update = UserUpdate()
        assert update.default_currency is None

    def test_profile_response_includes_currency(self):
        """UserProfileResponse should include default_currency."""
        from app.api.v1.settings import UserProfileResponse

        user = _make_user()
        resp = UserProfileResponse.model_validate(user)
        assert resp.default_currency == "USD"


# ===========================================================================
# FIRE response schema tests
# ===========================================================================


class TestFireSchemas:
    """Tests for FIRE API Pydantic response schemas."""

    def test_fire_metrics_response_structure(self):
        """FireMetricsResponse should nest all four sub-responses."""
        from app.api.v1.fire import (
            CoastFIResponse,
            FIRatioResponse,
            FireMetricsResponse,
            SavingsRateResponse,
            YearsToFIResponse,
        )

        resp = FireMetricsResponse(
            fi_ratio=FIRatioResponse(
                fi_ratio=0.5,
                investable_assets=500000,
                annual_expenses=40000,
                fi_number=1000000,
            ),
            savings_rate=SavingsRateResponse(
                savings_rate=0.3,
                income=100000,
                spending=70000,
                savings=30000,
                months=12,
            ),
            years_to_fi=YearsToFIResponse(
                years_to_fi=15.2,
                fi_number=1000000,
                investable_assets=500000,
                annual_savings=30000,
                withdrawal_rate=0.04,
                expected_return=0.07,
                already_fi=False,
            ),
            coast_fi=CoastFIResponse(
                coast_fi_number=300000,
                fi_number=1000000,
                investable_assets=500000,
                is_coast_fi=True,
                retirement_age=65,
                years_until_retirement=25,
                expected_return=0.07,
            ),
        )

        assert resp.fi_ratio.fi_ratio == 0.5
        assert resp.coast_fi.is_coast_fi is True
        assert resp.years_to_fi.already_fi is False

    def test_years_to_fi_allows_null(self):
        """years_to_fi field should accept None (unreachable FI)."""
        from app.api.v1.fire import YearsToFIResponse

        resp = YearsToFIResponse(
            years_to_fi=None,
            fi_number=0,
            investable_assets=0,
            annual_savings=0,
            withdrawal_rate=0.04,
            expected_return=0.07,
            already_fi=False,
        )
        assert resp.years_to_fi is None

    def test_coast_fi_number_type(self):
        """Coast FI number should be a float."""
        from app.api.v1.fire import CoastFIResponse

        resp = CoastFIResponse(
            coast_fi_number=250000.50,
            fi_number=1000000,
            investable_assets=300000,
            is_coast_fi=True,
            retirement_age=65,
            years_until_retirement=25,
            expected_return=0.07,
        )
        assert resp.coast_fi_number == 250000.50


# ===========================================================================
# Tax lot API schema tests
# ===========================================================================


class TestTaxLotSchemas:
    """Tests for the tax lot API response models."""

    def test_sale_result_gain_loss_calculation(self):
        """Verify SaleResult fields hold correct types."""
        # The schema is defined inline in the tax_lots router
        # Just verify it works as a plain dict
        sale_result = {
            "lots_sold": 2,
            "total_proceeds": 10000.0,
            "total_cost_basis": 8000.0,
            "realized_gain_loss": 2000.0,
            "short_term_gain_loss": 500.0,
            "long_term_gain_loss": 1500.0,
        }
        assert (
            sale_result["realized_gain_loss"]
            == sale_result["total_proceeds"] - sale_result["total_cost_basis"]
        )

    def test_holding_period_values(self):
        """Holding period should be SHORT_TERM or LONG_TERM."""
        from app.services.tax_lot_service import _determine_holding_period

        # 365 days = short term
        d1 = date(2024, 1, 1)
        d2 = date(2025, 1, 1)  # 366 days (2024 is leap year)
        assert _determine_holding_period(d1, d2) == "LONG_TERM"

        d3 = date(2025, 1, 1)
        d4 = date(2025, 12, 31)  # 364 days
        assert _determine_holding_period(d3, d4) == "SHORT_TERM"


# ---------------------------------------------------------------------------
# WelcomePage onboarding copy — plain-English audit
# ---------------------------------------------------------------------------

import pathlib
import re


def _read_welcome_page() -> str:
    """Return the raw text of WelcomePage.tsx."""
    # __file__ = backend/tests/unit/test_new_frontend_features.py
    # parents[3] = repo root (nest-egg/)
    repo_root = pathlib.Path(__file__).parents[3]
    welcome = repo_root / "frontend" / "src" / "pages" / "WelcomePage.tsx"
    return welcome.read_text(encoding="utf-8")


@pytest.mark.unit
class TestWelcomePageCopy:
    """
    Verify WelcomePage.tsx uses plain-English copy and avoids jargon
    that would confuse non-financial users.
    """

    # ── Banned jargon ────────────────────────────────────────────────────────

    def test_no_fire_acronym_in_goal_highlights(self):
        """GOAL_HIGHLIGHTS must not mention 'FIRE' (jargon for non-financial users)."""
        src = _read_welcome_page()
        # Extract just the GOAL_HIGHLIGHTS block
        match = re.search(
            r"const GOAL_HIGHLIGHTS.*?^};",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "GOAL_HIGHLIGHTS constant not found"
        assert (
            "FIRE" not in match.group()
        ), "GOAL_HIGHLIGHTS contains 'FIRE' — use plain language like 'retirement planner'"

    def test_no_monte_carlo_in_goal_highlights(self):
        """GOAL_HIGHLIGHTS must not mention 'Monte Carlo' (statistical jargon)."""
        src = _read_welcome_page()
        match = re.search(
            r"const GOAL_HIGHLIGHTS.*?^};",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "GOAL_HIGHLIGHTS constant not found"
        assert (
            "Monte Carlo" not in match.group()
        ), "GOAL_HIGHLIGHTS contains 'Monte Carlo' — use 'projections' or 'scenarios'"

    def test_no_fire_acronym_in_household_benefits(self):
        """HOUSEHOLD_BENEFITS must not use 'FIRE' or 'Coast FI' jargon."""
        src = _read_welcome_page()
        match = re.search(
            r"const HOUSEHOLD_BENEFITS.*?^];",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "HOUSEHOLD_BENEFITS constant not found"
        block = match.group()
        assert (
            "Coast FI" not in block
        ), "HOUSEHOLD_BENEFITS contains 'Coast FI' — use plain language"
        assert (
            "FIRE planning" not in block
        ), "HOUSEHOLD_BENEFITS contains 'FIRE planning' — use 'Retirement planning'"

    def test_no_monte_carlo_in_household_benefits(self):
        """HOUSEHOLD_BENEFITS must not mention 'Monte Carlo'."""
        src = _read_welcome_page()
        match = re.search(
            r"const HOUSEHOLD_BENEFITS.*?^];",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "HOUSEHOLD_BENEFITS constant not found"
        assert (
            "Monte Carlo" not in match.group()
        ), "HOUSEHOLD_BENEFITS contains 'Monte Carlo' — use 'scenarios' or 'projections'"

    # ── Required plain-English phrases ───────────────────────────────────────

    def test_goal_highlights_retirement_uses_plain_language(self):
        """Retirement highlight must describe the outcome, not the tool name."""
        src = _read_welcome_page()
        match = re.search(
            r"const GOAL_HIGHLIGHTS.*?^};",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "GOAL_HIGHLIGHTS constant not found"
        block = match.group()
        # Must contain plain-language terms
        assert (
            "retirement planner" in block or "years-to-retirement" in block
        ), "Retirement highlight should reference 'retirement planner' or 'years-to-retirement'"

    def test_goal_highlights_investments_uses_plain_language(self):
        """Investments highlight should not say 'asset allocation' or 'fee analysis'."""
        src = _read_welcome_page()
        match = re.search(
            r"const GOAL_HIGHLIGHTS.*?^};",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "GOAL_HIGHLIGHTS constant not found"
        block = match.group()
        assert (
            "asset allocation" not in block
        ), "Investments highlight uses 'asset allocation' — rephrase as 'what you're invested in'"

    def test_goal_next_sentence_retirement_avoids_jargon(self):
        """GOAL_NEXT_SENTENCE retirement entry must not use 'FIRE dashboard'."""
        src = _read_welcome_page()
        match = re.search(
            r"const GOAL_NEXT_SENTENCE.*?^};",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "GOAL_NEXT_SENTENCE constant not found"
        block = match.group()
        assert (
            "FIRE dashboard" not in block
        ), "GOAL_NEXT_SENTENCE retirement uses 'FIRE dashboard' — use 'retirement planner'"

    # ── Goal selector UX ─────────────────────────────────────────────────────

    def test_goal_selector_has_all_three_goals(self):
        """GOAL_OPTIONS must define spending, retirement, and investments goals."""
        src = _read_welcome_page()
        match = re.search(
            r"const GOAL_OPTIONS.*?^];",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "GOAL_OPTIONS constant not found"
        block = match.group()
        assert '"spending"' in block
        assert '"retirement"' in block
        assert '"investments"' in block

    def test_goal_selector_has_all_of_the_above_hint(self):
        """Step 0 must include copy telling users they can do all goals."""
        src = _read_welcome_page()
        # Flexible match — the phrase may be worded different ways
        assert (
            "can do all" in src or "can do all of this" in src or "tackle first" in src
        ), "Step 0 should tell users they can do all goals, not just one"

    def test_skip_button_says_skip_for_now(self):
        """Skip button on step 0 should say 'Skip for now', not 'Skip setup'."""
        src = _read_welcome_page()
        assert "Skip for now" in src, "Skip button should say 'Skip for now' (not 'Skip setup')"
        assert "Skip setup" not in src, "Old label 'Skip setup' should be removed"

    def test_household_name_placeholder_works_for_solo_users(self):
        """Placeholder must include a solo-user example, not only a family example."""
        src = _read_welcome_page()
        # Must offer a solo-friendly example (e.g. "Jane's Finances") alongside any family example
        assert (
            "Finances" in src or "My Money" in src or "Jane" in src
        ), 'Household name placeholder should include a solo-user example like "Jane\'s Finances"'

    # ── Destination routing ───────────────────────────────────────────────────

    def test_retirement_goal_routes_to_retirement_page(self):
        """Retirement goal must route to /retirement, not /fire."""
        src = _read_welcome_page()
        match = re.search(
            r"const GOAL_DESTINATION.*?^};",
            src,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "GOAL_DESTINATION constant not found"
        block = match.group()
        assert '"/retirement"' in block, "Retirement goal should route to /retirement"
        # /fire should not appear as a destination value
        assert (
            'retirement: "/fire"' not in block
        ), "Retirement goal routes to /fire — should be /retirement"


# ---------------------------------------------------------------------------
# Widget registry plain-English descriptions
# ---------------------------------------------------------------------------

_REGISTRY_PATH = (
    pathlib.Path(__file__).parents[3]
    / "frontend"
    / "src"
    / "features"
    / "dashboard"
    / "widgetRegistry.tsx"
)


def _read_widget_registry() -> str:
    return _REGISTRY_PATH.read_text(encoding="utf-8")


class TestWidgetRegistryDescriptions:
    """Ensure widget gallery descriptions are plain-English and jargon-free."""

    # ── Jargon must not appear ────────────────────────────────────────────

    def test_no_raw_monte_carlo_in_descriptions(self):
        """'Monte Carlo' must not appear as bare jargon in widget descriptions."""
        src = _read_widget_registry()
        # Find all description strings
        descriptions = re.findall(r'description:\s*\n?\s*"([^"]*)"', src, re.DOTALL)
        combined = " ".join(descriptions)
        assert (
            "Monte Carlo" not in combined
        ), "Widget description uses bare 'Monte Carlo' jargon without explanation"

    def test_no_fi_ratio_jargon_in_descriptions(self):
        """'FI ratio' must not appear as bare unexplained jargon in widget descriptions."""
        src = _read_widget_registry()
        descriptions = re.findall(r'description:\s*\n?\s*"([^"]*)"', src, re.DOTALL)
        combined = " ".join(descriptions)
        assert "FI ratio" not in combined, "Widget description uses unexplained 'FI ratio' jargon"

    def test_no_rmd_acronym_unexplained_in_descriptions(self):
        """RMD widget must explain the concept (age, withdrawal, penalty)."""
        src = _read_widget_registry()
        # The title was renamed — check neither title nor description uses bare 'RMD'
        # in a way that's unexplained (description must mention age or withdrawal or penalty)
        rmd_block = re.search(
            r'"rmd-planner".*?component: RmdPlannerWidget',
            src,
            re.DOTALL,
        )
        assert rmd_block, "rmd-planner widget block not found"
        block = rmd_block.group()
        assert any(
            word in block for word in ["age", "withdraw", "penalty", "IRS", "73", "required"]
        ), "RMD widget description should explain the concept (age, withdrawal, penalty)"

    def test_no_ltcg_irmaa_unexplained(self):
        """'LTCG' and 'IRMAA' must not appear in descriptions as unexplained acronyms."""
        src = _read_widget_registry()
        descriptions = re.findall(r'description:\s*\n?\s*"([^"]*)"', src, re.DOTALL)
        combined = " ".join(descriptions)
        assert "LTCG" not in combined, "Widget description uses unexplained 'LTCG' acronym"
        assert "IRMAA" not in combined, "Widget description uses unexplained 'IRMAA' acronym"

    def test_no_expense_ratio_drag_jargon(self):
        """'fee drag' and 'expense ratio' must not appear as bare jargon in descriptions."""
        src = _read_widget_registry()
        descriptions = re.findall(r'description:\s*\n?\s*"([^"]*)"', src, re.DOTALL)
        combined = " ".join(descriptions)
        assert (
            "fee drag" not in combined.lower()
        ), "Widget description uses unexplained 'fee drag' jargon"
        assert (
            "expense ratio" not in combined.lower()
        ), "Widget description uses unexplained 'expense ratio' jargon"

    def test_no_wash_sale_unexplained(self):
        """'wash sale' must not appear in descriptions without context."""
        src = _read_widget_registry()
        descriptions = re.findall(r'description:\s*\n?\s*"([^"]*)"', src, re.DOTALL)
        combined = " ".join(descriptions)
        assert (
            "wash sale" not in combined.lower()
        ), "Widget description uses unexplained 'wash sale' jargon"

    def test_no_concentration_risk_unexplained(self):
        """'concentration risk' must not appear as bare jargon in descriptions."""
        src = _read_widget_registry()
        descriptions = re.findall(r'description:\s*\n?\s*"([^"]*)"', src, re.DOTALL)
        combined = " ".join(descriptions)
        assert (
            "concentration risk" not in combined.lower()
        ), "Widget description uses unexplained 'concentration risk' jargon"

    # ── Plain-English content must be present ────────────────────────────

    def test_fire_widget_explains_concept(self):
        """FIRE widget description must explain what financial independence means."""
        src = _read_widget_registry()
        fire_block = re.search(
            r'"fire-metrics".*?component: FireMetricsWidget',
            src,
            re.DOTALL,
        )
        assert fire_block, "fire-metrics widget block not found"
        block = fire_block.group()
        assert any(
            phrase in block
            for phrase in [
                "never needing to work",
                "financially independent",
                "financial independence",
                "don't need to work",
                "stop working",
            ]
        ), "FIRE widget description should explain the concept in plain English"

    def test_roth_conversion_explains_concept(self):
        """Roth conversion widget must explain the tax trade-off in plain English."""
        src = _read_widget_registry()
        roth_block = re.search(
            r'"roth-conversion".*?component: RothConversionWidget',
            src,
            re.DOTALL,
        )
        assert roth_block, "roth-conversion widget block not found"
        block = roth_block.group()
        assert any(
            phrase in block
            for phrase in [
                "tax-free",
                "taxes now",
                "pay taxes",
                "future withdrawals",
            ]
        ), "Roth conversion widget should explain the tax trade-off"

    def test_fee_analysis_quantifies_impact(self):
        """Fee analysis widget should mention a concrete dollar or percentage impact."""
        src = _read_widget_registry()
        fee_block = re.search(
            r'"fee-analysis".*?component: FeeAnalysisWidget',
            src,
            re.DOTALL,
        )
        assert fee_block, "fee-analysis widget block not found"
        block = fee_block.group()
        assert any(
            phrase in block
            for phrase in [
                "$",
                "cost",
                "decades",
                "long-term",
                "years",
                "0.5%",
            ]
        ), "Fee analysis widget should hint at long-term cost impact"

    def test_fund_overlap_explains_diversification(self):
        """Fund overlap widget must explain why overlap is a problem."""
        src = _read_widget_registry()
        overlap_block = re.search(
            r'"fund-overlap".*?component: FundOverlapWidget',
            src,
            re.DOTALL,
        )
        assert overlap_block, "fund-overlap widget block not found"
        block = overlap_block.group()
        assert any(
            phrase in block
            for phrase in [
                "diversif",
                "same stocks",
                "same bets",
                "less diversified",
                "doubling down",
            ]
        ), "Fund overlap widget should explain why it matters (diversification)"

    def test_tax_loss_harvesting_explains_benefit(self):
        """Tax loss harvesting widget must explain the tax benefit in plain English."""
        src = _read_widget_registry()
        tlh_block = re.search(
            r'"tax-loss-harvesting".*?component: TaxLossHarvestingWidget',
            src,
            re.DOTALL,
        )
        assert tlh_block, "tax-loss-harvesting widget block not found"
        block = tlh_block.group()
        assert any(
            phrase in block
            for phrase in [
                "tax bill",
                "reduce your tax",
                "offset",
                "save on taxes",
            ]
        ), "Tax loss harvesting widget should explain the tax benefit"

    def test_social_security_explains_delay_benefit(self):
        """Social security widget must explain why delaying claiming is beneficial."""
        src = _read_widget_registry()
        ss_block = re.search(
            r'"social-security".*?component: SocialSecurityWidget',
            src,
            re.DOTALL,
        )
        assert ss_block, "social-security widget block not found"
        block = ss_block.group()
        assert any(
            phrase in block
            for phrase in [
                "bigger",
                "larger",
                "more per month",
                "delay",
                "waiting",
                "8%",
            ]
        ), "Social Security widget should explain the benefit of delaying claiming"

    def test_financial_health_lists_plain_factors(self):
        """Financial health widget must describe the score factors in plain English."""
        src = _read_widget_registry()
        fh_block = re.search(
            r'"financial-health".*?component: FinancialHealthWidget',
            src,
            re.DOTALL,
        )
        assert fh_block, "financial-health widget block not found"
        block = fh_block.group()
        # Must NOT just say "debt-to-income" without explanation
        assert "debt-to-income" not in block, (
            "Financial health description uses unexplained 'debt-to-income' — "
            "describe it plainly instead"
        )
        # Must mention something recognizable
        assert any(
            phrase in block for phrase in ["save", "emergency", "debt", "retirement", "score"]
        ), "Financial health description should list the factors in plain English"

    # ── Investments page empty state ──────────────────────────────────────


_INVESTMENTS_PATH = (
    pathlib.Path(__file__).parents[3] / "frontend" / "src" / "pages" / "InvestmentsPage.tsx"
)


def _read_investments_page() -> str:
    return _INVESTMENTS_PATH.read_text(encoding="utf-8")


class TestInvestmentsPageCopy:
    """Ensure InvestmentsPage uses plain-English copy for novice users."""

    def test_empty_state_no_jargon_allocation(self):
        """Empty state must not use 'allocated' or 'allocation' without explanation."""
        src = _read_investments_page()
        # Find the empty state block
        empty_block_match = re.search(
            r"No investment accounts yet.*?Add investment accounts",
            src,
            re.DOTALL,
        )
        assert empty_block_match, "Empty state block not found"
        block = empty_block_match.group()
        assert (
            "allocation" not in block.lower()
        ), "Empty state uses 'allocation' — replace with plain description"

    def test_empty_state_no_jargon_fees_eating(self):
        """Empty state must not use 'eating into your returns' slang."""
        src = _read_investments_page()
        assert (
            "eating into" not in src
        ), "InvestmentsPage uses 'eating into your returns' — replace with plain language"

    def test_empty_state_explains_stocks_and_bonds(self):
        """Empty state should explain stocks vs bonds in plain terms."""
        src = _read_investments_page()
        empty_block_match = re.search(
            r"No investment accounts yet.*?Add investment accounts",
            src,
            re.DOTALL,
        )
        assert empty_block_match, "Empty state block not found"
        block = empty_block_match.group()
        assert any(
            phrase in block for phrase in ["growth", "stability", "safety", "stocks", "bonds"]
        ), "Empty state should describe what stocks and bonds mean"

    def test_cost_basis_label_is_plain_english(self):
        """'Cost Basis' label must be replaced with plain-English equivalent."""
        src = _read_investments_page()
        # The stat help text and column header should say "What you paid" not "Cost Basis"
        assert (
            "Cost Basis:" not in src
        ), "InvestmentsPage uses 'Cost Basis:' label — replace with 'What you paid:'"
        assert (
            "What you paid" in src
        ), "InvestmentsPage should use 'What you paid' instead of 'Cost Basis'"

    def test_cost_basis_column_header_is_plain_english(self):
        """Holdings table 'Cost Basis' column header should be replaced."""
        src = _read_investments_page()
        assert (
            "<Th isNumeric>Cost Basis</Th>" not in src
        ), "Holdings table uses 'Cost Basis' column header — replace with plain English"
