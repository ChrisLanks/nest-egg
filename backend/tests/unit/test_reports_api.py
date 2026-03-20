"""Unit tests for reports API endpoints."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.reports import (
    ExecuteReportRequest,
    ReportTemplateCreate,
    ReportTemplateUpdate,
    create_report_template,
    delete_report_template,
    execute_report,
    execute_saved_report,
    export_report_csv,
    get_household_summary,
    get_report_template,
    get_tax_loss_harvesting,
    list_report_templates,
    update_report_template,
)
from app.models.account import AccountType
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.is_active = True
    return user


def _make_template(user, *, is_shared=False, creator_id=None):
    template = Mock()
    template.id = uuid4()
    template.organization_id = user.organization_id
    template.name = "Monthly Report"
    template.description = "Monthly financial summary"
    template.report_type = "income_expense"
    template.config = {"period": "monthly"}
    template.is_shared = is_shared
    template.created_by_user_id = creator_id or user.id
    template.created_at = datetime(2024, 1, 1, 12, 0, 0)
    template.updated_at = datetime(2024, 1, 15, 12, 0, 0)
    return template


def _db_returning(obj):
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = obj
    db.execute.return_value = result
    return db


# ---------------------------------------------------------------------------
# List Templates
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListReportTemplates:
    """Test list_report_templates endpoint."""

    @pytest.mark.asyncio
    async def test_list_templates_success(self):
        user = _make_user()
        template = _make_template(user)
        db = AsyncMock()

        scalars_mock = Mock()
        scalars_mock.all.return_value = [template]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        result = await list_report_templates(after=None, limit=50, current_user=user, db=db)

        assert len(result) == 1
        assert result[0].name == "Monthly Report"

    @pytest.mark.asyncio
    async def test_list_templates_empty(self):
        user = _make_user()
        db = AsyncMock()

        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        result = await list_report_templates(after=None, limit=50, current_user=user, db=db)

        assert result == []


# ---------------------------------------------------------------------------
# Create Template
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateReportTemplate:
    """Test create_report_template endpoint."""

    @pytest.mark.asyncio
    async def test_create_template_success(self):
        user = _make_user()
        db = AsyncMock()

        template_data = ReportTemplateCreate(
            name="New Report",
            description="A new report",
            report_type="income_expense",
            config={"period": "quarterly"},
            is_shared=False,
        )

        # Mock db.refresh to set expected attributes on the added object
        created_template = _make_template(user)

        async def mock_refresh(obj):
            obj.id = created_template.id
            obj.organization_id = created_template.organization_id
            obj.name = created_template.name
            obj.description = created_template.description
            obj.report_type = created_template.report_type
            obj.config = created_template.config
            obj.is_shared = created_template.is_shared
            obj.created_by_user_id = created_template.created_by_user_id
            obj.created_at = created_template.created_at
            obj.updated_at = created_template.updated_at

        db.refresh = AsyncMock(side_effect=mock_refresh)

        result = await create_report_template(template_data=template_data, current_user=user, db=db)

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        assert result.name == "Monthly Report"


# ---------------------------------------------------------------------------
# Get Template
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetReportTemplate:
    """Test get_report_template endpoint."""

    @pytest.mark.asyncio
    async def test_get_template_success_creator(self):
        user = _make_user()
        template = _make_template(user)
        db = _db_returning(template)

        result = await get_report_template(template_id=template.id, current_user=user, db=db)

        assert result.name == "Monthly Report"

    @pytest.mark.asyncio
    async def test_get_template_success_shared(self):
        user = _make_user()
        other_user_id = uuid4()
        template = _make_template(user, is_shared=True, creator_id=other_user_id)
        db = _db_returning(template)

        result = await get_report_template(template_id=template.id, current_user=user, db=db)

        assert result.name == "Monthly Report"

    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        user = _make_user()
        db = _db_returning(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_report_template(template_id=uuid4(), current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_template_not_shared_not_creator_raises_403(self):
        user = _make_user()
        other_user_id = uuid4()
        template = _make_template(user, is_shared=False, creator_id=other_user_id)
        db = _db_returning(template)

        with pytest.raises(HTTPException) as exc_info:
            await get_report_template(template_id=template.id, current_user=user, db=db)

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Update Template
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateReportTemplate:
    """Test update_report_template endpoint."""

    @pytest.mark.asyncio
    async def test_update_template_success(self):
        user = _make_user()
        template = _make_template(user)
        db = _db_returning(template)

        template_data = ReportTemplateUpdate(name="Updated Report")

        await update_report_template(
            template_id=template.id,
            template_data=template_data,
            current_user=user,
            db=db,
        )

        assert template.name == "Updated Report"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_template_all_fields(self):
        user = _make_user()
        template = _make_template(user)
        db = _db_returning(template)

        template_data = ReportTemplateUpdate(
            name="New Name",
            description="New Desc",
            config={"new": "config"},
            is_shared=True,
        )

        await update_report_template(
            template_id=template.id,
            template_data=template_data,
            current_user=user,
            db=db,
        )

        assert template.name == "New Name"
        assert template.description == "New Desc"
        assert template.config == {"new": "config"}
        assert template.is_shared is True

    @pytest.mark.asyncio
    async def test_update_template_not_found(self):
        user = _make_user()
        db = _db_returning(None)

        with pytest.raises(HTTPException) as exc_info:
            await update_report_template(
                template_id=uuid4(),
                template_data=ReportTemplateUpdate(name="X"),
                current_user=user,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_template_not_creator_raises_403(self):
        user = _make_user()
        other_user_id = uuid4()
        template = _make_template(user, creator_id=other_user_id)
        db = _db_returning(template)

        with pytest.raises(HTTPException) as exc_info:
            await update_report_template(
                template_id=template.id,
                template_data=ReportTemplateUpdate(name="X"),
                current_user=user,
                db=db,
            )

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Delete Template
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeleteReportTemplate:
    """Test delete_report_template endpoint."""

    @pytest.mark.asyncio
    async def test_delete_template_success(self):
        user = _make_user()
        template = _make_template(user)
        db = _db_returning(template)

        await delete_report_template(template_id=template.id, current_user=user, db=db)

        db.delete.assert_awaited_once_with(template)
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_template_not_found(self):
        user = _make_user()
        db = _db_returning(None)

        with pytest.raises(HTTPException) as exc_info:
            await delete_report_template(template_id=uuid4(), current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_template_not_creator_raises_403(self):
        user = _make_user()
        other_user_id = uuid4()
        template = _make_template(user, creator_id=other_user_id)
        db = _db_returning(template)

        with pytest.raises(HTTPException) as exc_info:
            await delete_report_template(template_id=template.id, current_user=user, db=db)

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Execute Report
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecuteReport:
    """Test execute_report endpoint."""

    @pytest.mark.asyncio
    async def test_execute_report_no_user_filter(self):
        user = _make_user()
        mock_acc = Mock()
        mock_acc.id = uuid4()
        db = AsyncMock()

        request = ExecuteReportRequest(config={"type": "income_expense"})

        with patch(
            "app.api.v1.reports.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.reports.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.reports.ReportService.execute_report",
                    new_callable=AsyncMock,
                    return_value={"data": []},
                ):
                    result = await execute_report(
                        request=request, user_id=None, current_user=user, db=db
                    )

        assert result == {"data": []}

    @pytest.mark.asyncio
    async def test_execute_report_with_user_filter(self):
        user = _make_user()
        target_user_id = uuid4()
        mock_acc = Mock()
        mock_acc.id = uuid4()
        db = AsyncMock()

        request = ExecuteReportRequest(config={"type": "income_expense"})

        with patch(
            "app.api.v1.reports.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.reports.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.reports.ReportService.execute_report",
                    new_callable=AsyncMock,
                    return_value={"data": []},
                ):
                    await execute_report(
                        request=request,
                        user_id=target_user_id,
                        current_user=user,
                        db=db,
                    )

        mock_verify.assert_awaited_once()


# ---------------------------------------------------------------------------
# Execute Saved Report
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecuteSavedReport:
    """Test execute_saved_report endpoint."""

    @pytest.mark.asyncio
    async def test_execute_saved_success(self):
        user = _make_user()
        template = _make_template(user)
        mock_acc = Mock()
        mock_acc.id = uuid4()
        db = _db_returning(template)

        with patch(
            "app.api.v1.reports.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.reports.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.reports.ReportService.execute_report",
                    new_callable=AsyncMock,
                    return_value={"data": [{"total": 1000}]},
                ):
                    result = await execute_saved_report(
                        template_id=template.id,
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert "template" in result
        assert result["template"]["name"] == "Monthly Report"

    @pytest.mark.asyncio
    async def test_execute_saved_not_found(self):
        user = _make_user()
        db = _db_returning(None)

        with pytest.raises(HTTPException) as exc_info:
            await execute_saved_report(
                template_id=uuid4(),
                user_id=None,
                current_user=user,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_execute_saved_not_shared_not_creator_raises_403(self):
        user = _make_user()
        other_user_id = uuid4()
        template = _make_template(user, is_shared=False, creator_id=other_user_id)
        db = _db_returning(template)

        with pytest.raises(HTTPException) as exc_info:
            await execute_saved_report(
                template_id=template.id,
                user_id=None,
                current_user=user,
                db=db,
            )

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportReportCsv:
    """Test export_report_csv endpoint."""

    @pytest.mark.asyncio
    async def test_export_csv_success(self):
        user = _make_user()
        template = _make_template(user)
        mock_acc = Mock()
        mock_acc.id = uuid4()
        db = _db_returning(template)

        with patch(
            "app.api.v1.reports.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.reports.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.reports.ReportService.generate_export_csv",
                    new_callable=AsyncMock,
                    return_value="Date,Amount\n2024-01-01,100",
                ):
                    result = await export_report_csv(
                        template_id=template.id,
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert result.media_type == "text/csv"

    @pytest.mark.asyncio
    async def test_export_csv_not_found(self):
        user = _make_user()
        db = _db_returning(None)

        with pytest.raises(HTTPException) as exc_info:
            await export_report_csv(
                template_id=uuid4(),
                user_id=None,
                current_user=user,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_export_csv_not_shared_not_creator_raises_403(self):
        user = _make_user()
        other_user_id = uuid4()
        template = _make_template(user, is_shared=False, creator_id=other_user_id)
        db = _db_returning(template)

        with pytest.raises(HTTPException) as exc_info:
            await export_report_csv(
                template_id=template.id,
                user_id=None,
                current_user=user,
                db=db,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_export_csv_value_error_raises_404(self):
        user = _make_user()
        template = _make_template(user)
        mock_acc = Mock()
        mock_acc.id = uuid4()
        db = _db_returning(template)

        with patch(
            "app.api.v1.reports.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.reports.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.reports.ReportService.generate_export_csv",
                    new_callable=AsyncMock,
                    side_effect=ValueError("Not found"),
                ):
                    with pytest.raises(HTTPException) as exc_info:
                        await export_report_csv(
                            template_id=template.id,
                            user_id=None,
                            current_user=user,
                            db=db,
                        )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Tax Loss Harvesting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTaxLossHarvesting:
    """Test get_tax_loss_harvesting endpoint."""

    @pytest.mark.asyncio
    async def test_tax_loss_harvesting_success(self):
        user = _make_user()
        db = AsyncMock()

        opp = Mock()
        opp.unrealized_loss = -500.0
        opp.estimated_tax_savings = 150.0
        # Mock vars() to return dict-like data matching TaxLossOpportunityResponse
        opp.__dict__ = {
            "holding_id": uuid4(),
            "ticker": "AAPL",
            "name": "Apple Inc",
            "shares": Decimal("10"),
            "cost_basis": Decimal("1500.0"),
            "current_value": Decimal("1000.0"),
            "unrealized_loss": Decimal("-500.0"),
            "loss_percentage": Decimal("-33.33"),
            "estimated_tax_savings": Decimal("150.0"),
            "wash_sale_risk": False,
            "wash_sale_reason": None,
            "sector": "Technology",
            "suggested_replacements": ["MSFT", "GOOG"],
        }

        with patch(
            "app.api.v1.reports.tax_loss_harvesting_service.get_opportunities",
            new_callable=AsyncMock,
            return_value=[opp],
        ):
            result = await get_tax_loss_harvesting(user_id=None, current_user=user, db=db)

        assert result.total_harvestable_losses == -500.0
        assert result.total_estimated_tax_savings == 150.0
        assert len(result.opportunities) == 1

    @pytest.mark.asyncio
    async def test_tax_loss_harvesting_empty(self):
        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.reports.tax_loss_harvesting_service.get_opportunities",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await get_tax_loss_harvesting(user_id=None, current_user=user, db=db)

        assert result.total_harvestable_losses == 0
        assert result.total_estimated_tax_savings == 0
        assert result.opportunities == []

    @pytest.mark.asyncio
    async def test_tax_loss_harvesting_with_user_id_filtering(self):
        """Should call verify_household_member, get_user_accounts, and pass account_ids."""
        user = _make_user()
        target_user_id = uuid4()
        acc1 = Mock()
        acc1.id = uuid4()
        acc2 = Mock()
        acc2.id = uuid4()
        db = AsyncMock()

        with patch(
            "app.api.v1.reports.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.reports.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[acc1, acc2],
            ) as mock_get_accs:
                with patch(
                    "app.api.v1.reports.tax_loss_harvesting_service.get_opportunities",
                    new_callable=AsyncMock,
                    return_value=[],
                ) as mock_get_opps:
                    result = await get_tax_loss_harvesting(
                        user_id=target_user_id,
                        current_user=user,
                        db=db,
                    )

        mock_verify.assert_awaited_once_with(db, target_user_id, user.organization_id)
        mock_get_accs.assert_awaited_once_with(db, target_user_id, user.organization_id)
        call_kwargs = mock_get_opps.call_args.kwargs
        assert call_kwargs["account_ids"] == {acc1.id, acc2.id}
        assert result.opportunities == []

    @pytest.mark.asyncio
    async def test_tax_loss_harvesting_no_user_id_passes_none(self):
        """Should pass account_ids=None when no user_id provided."""
        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.reports.tax_loss_harvesting_service.get_opportunities",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_get_opps:
            await get_tax_loss_harvesting(user_id=None, current_user=user, db=db)

        call_kwargs = mock_get_opps.call_args.kwargs
        assert call_kwargs["account_ids"] is None


# ---------------------------------------------------------------------------
# Household Summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHouseholdSummary:
    """Test get_household_summary endpoint."""

    @pytest.mark.asyncio
    async def test_household_summary_success(self):
        user = _make_user()
        db = AsyncMock()

        # Accounts
        checking = Mock()
        checking.current_balance = Decimal("10000")
        checking.user_id = user.id
        checking.account_type = AccountType.CHECKING

        credit_card = Mock()
        credit_card.current_balance = Decimal("-2000")
        credit_card.user_id = user.id
        credit_card.account_type = AccountType.CREDIT_CARD

        # Account query
        acc_scalars = Mock()
        acc_scalars.all.return_value = [checking, credit_card]
        acc_result = Mock()
        acc_result.scalars.return_value = acc_scalars

        # Member query
        member = Mock()
        member.id = user.id
        member.display_name = "Test User"
        member.email = "test@example.com"
        member_scalars = Mock()
        member_scalars.all.return_value = [member]
        member_result = Mock()
        member_result.scalars.return_value = member_scalars

        db.execute = AsyncMock(side_effect=[acc_result, member_result])

        result = await get_household_summary(current_user=user, db=db)

        assert result["total_household_assets"] == 10000.0
        assert result["total_household_liabilities"] == 2000.0
        assert result["total_household_net_worth"] == 8000.0
        assert result["member_count"] == 1
        assert len(result["per_member_breakdown"]) == 1

    @pytest.mark.asyncio
    async def test_household_summary_no_accounts(self):
        user = _make_user()
        db = AsyncMock()

        acc_scalars = Mock()
        acc_scalars.all.return_value = []
        acc_result = Mock()
        acc_result.scalars.return_value = acc_scalars

        member = Mock()
        member.id = user.id
        member.display_name = "Test User"
        member.email = "test@example.com"
        member_scalars = Mock()
        member_scalars.all.return_value = [member]
        member_result = Mock()
        member_result.scalars.return_value = member_scalars

        db.execute = AsyncMock(side_effect=[acc_result, member_result])

        result = await get_household_summary(current_user=user, db=db)

        assert result["total_household_net_worth"] == 0.0
        assert result["total_household_assets"] == 0.0
        assert result["total_household_liabilities"] == 0.0

    @pytest.mark.asyncio
    async def test_household_summary_multiple_members(self):
        user = _make_user()
        other_user_id = uuid4()
        db = AsyncMock()

        checking1 = Mock()
        checking1.current_balance = Decimal("10000")
        checking1.user_id = user.id
        checking1.account_type = AccountType.CHECKING

        checking2 = Mock()
        checking2.current_balance = Decimal("5000")
        checking2.user_id = other_user_id
        checking2.account_type = AccountType.SAVINGS

        acc_scalars = Mock()
        acc_scalars.all.return_value = [checking1, checking2]
        acc_result = Mock()
        acc_result.scalars.return_value = acc_scalars

        member1 = Mock()
        member1.id = user.id
        member1.display_name = "User 1"
        member1.email = "user1@example.com"

        member2 = Mock()
        member2.id = other_user_id
        member2.display_name = "User 2"
        member2.email = "user2@example.com"

        member_scalars = Mock()
        member_scalars.all.return_value = [member1, member2]
        member_result = Mock()
        member_result.scalars.return_value = member_scalars

        db.execute = AsyncMock(side_effect=[acc_result, member_result])

        result = await get_household_summary(current_user=user, db=db)

        assert result["total_household_net_worth"] == 15000.0
        assert result["member_count"] == 2
        assert len(result["per_member_breakdown"]) == 2

    @pytest.mark.asyncio
    async def test_household_summary_debt_types(self):
        """Loans, mortgages, and student loans should be classified as liabilities."""
        user = _make_user()
        db = AsyncMock()

        mortgage = Mock()
        mortgage.current_balance = Decimal("-250000")
        mortgage.user_id = user.id
        mortgage.account_type = AccountType.MORTGAGE

        student_loan = Mock()
        student_loan.current_balance = Decimal("-35000")
        student_loan.user_id = user.id
        student_loan.account_type = AccountType.STUDENT_LOAN

        loan = Mock()
        loan.current_balance = Decimal("-15000")
        loan.user_id = user.id
        loan.account_type = AccountType.LOAN

        acc_scalars = Mock()
        acc_scalars.all.return_value = [mortgage, student_loan, loan]
        acc_result = Mock()
        acc_result.scalars.return_value = acc_scalars

        member = Mock()
        member.id = user.id
        member.display_name = "Test"
        member.email = "test@example.com"
        member_scalars = Mock()
        member_scalars.all.return_value = [member]
        member_result = Mock()
        member_result.scalars.return_value = member_scalars

        db.execute = AsyncMock(side_effect=[acc_result, member_result])

        result = await get_household_summary(current_user=user, db=db)

        assert result["total_household_liabilities"] == 300000.0
        assert result["total_household_assets"] == 0.0


# ---------------------------------------------------------------------------
# Guest user_id filter guard
# ---------------------------------------------------------------------------


def _make_guest_user():
    """Return a mock user with _is_guest=True (guest viewing a host household)."""
    user = _make_user()
    user._is_guest = True
    return user


@pytest.mark.unit
class TestGuestUserIdFilterBlocked:
    """Guests must not be able to filter report endpoints by individual member user_id.

    A guest with viewer role can view full household data, but must not be able
    to isolate a single member's accounts — that would leak per-member financial
    detail that the guest would not otherwise see through any UI flow.
    """

    @pytest.mark.asyncio
    async def test_execute_report_guest_with_user_id_raises_403(self):
        guest = _make_guest_user()
        db = AsyncMock()
        request = ExecuteReportRequest(config={"type": "income_expense"})

        with pytest.raises(HTTPException) as exc_info:
            await execute_report(
                request=request,
                user_id=uuid4(),
                current_user=guest,
                db=db,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_execute_saved_report_guest_with_user_id_raises_403(self):
        guest = _make_guest_user()
        template = _make_template(guest)
        db = _db_returning(template)

        with pytest.raises(HTTPException) as exc_info:
            await execute_saved_report(
                template_id=template.id,
                user_id=uuid4(),
                current_user=guest,
                db=db,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_export_csv_guest_with_user_id_raises_403(self):
        guest = _make_guest_user()
        template = _make_template(guest)
        db = _db_returning(template)

        with pytest.raises(HTTPException) as exc_info:
            await export_report_csv(
                template_id=template.id,
                user_id=uuid4(),
                current_user=guest,
                db=db,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_tax_loss_harvesting_guest_with_user_id_raises_403(self):
        guest = _make_guest_user()
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_tax_loss_harvesting(
                user_id=uuid4(),
                current_user=guest,
                db=db,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_execute_report_guest_without_user_id_allowed(self):
        """Guests can still run reports without a user_id filter (full household view)."""
        guest = _make_guest_user()
        mock_acc = Mock()
        mock_acc.id = uuid4()
        db = AsyncMock()
        request = ExecuteReportRequest(config={"type": "income_expense"})

        with patch(
            "app.api.v1.reports.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.reports.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.reports.ReportService.execute_report",
                    new_callable=AsyncMock,
                    return_value={"data": []},
                ):
                    result = await execute_report(
                        request=request,
                        user_id=None,
                        current_user=guest,
                        db=db,
                    )

        assert result == {"data": []}

    @pytest.mark.asyncio
    async def test_non_guest_with_user_id_allowed(self):
        """Regular household members can still filter by user_id."""
        user = _make_user()
        # _is_guest not set — getattr(..., False) returns False
        target_user_id = uuid4()
        mock_acc = Mock()
        mock_acc.id = uuid4()
        db = AsyncMock()
        request = ExecuteReportRequest(config={"type": "income_expense"})

        with patch(
            "app.api.v1.reports.verify_household_member",
            new_callable=AsyncMock,
        ):
            with patch(
                "app.api.v1.reports.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.reports.ReportService.execute_report",
                    new_callable=AsyncMock,
                    return_value={"data": []},
                ):
                    result = await execute_report(
                        request=request,
                        user_id=target_user_id,
                        current_user=user,
                        db=db,
                    )

        assert result == {"data": []}
