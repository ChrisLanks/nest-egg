"""Unit tests for estate planning API endpoints and service."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.api.v1.estate import (
    create_beneficiary,
    delete_beneficiary,
    get_tax_exposure,
    list_beneficiaries,
    list_documents,
    upsert_document,
    BeneficiaryCreate,
    EstateDocumentUpsert,
)
from app.services.estate_planning_service import EstatePlanningService


def _make_user(org_id=None):
    u = Mock()
    u.id = uuid4()
    u.organization_id = org_id or uuid4()
    return u


# ── EstatePlanningService ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestEstatePlanningService:
    def test_single_below_exemption(self):
        result = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("500000"),
            filing_status="single",
        )
        assert result["above_exemption"] is False
        assert result["taxable_estate"] == 0.0
        assert result["estimated_federal_tax"] == 0.0

    def test_single_above_exemption(self):
        # $15M estate exceeds ~$13.99M exemption
        result = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("15000000"),
            filing_status="single",
        )
        assert result["above_exemption"] is True
        assert result["taxable_estate"] > 0
        assert result["estimated_federal_tax"] > 0

    def test_married_doubles_exemption(self):
        single = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("20000000"),
            filing_status="single",
        )
        married = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("20000000"),
            filing_status="married",
        )
        assert married["federal_exemption"] == pytest.approx(single["federal_exemption"] * 2)

    def test_married_20m_below_combined_exemption(self):
        # $20M < $27.98M married exemption → no tax
        result = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("20000000"),
            filing_status="married",
        )
        assert result["above_exemption"] is False

    def test_40_pct_rate_above_exemption(self):
        result = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("14990000"),
            filing_status="single",
        )
        if result["above_exemption"]:
            expected_tax = result["taxable_estate"] * 0.40
            assert abs(result["estimated_federal_tax"] - expected_tax) < 1

    def test_beneficiary_coverage_all_covered(self):
        accounts = [{"id": "a1", "balance": 100_000}]
        bens = [{"account_id": "a1", "designation_type": "primary"}]
        result = EstatePlanningService.get_beneficiary_coverage_summary(accounts, bens)
        assert result["coverage_pct"] == 100.0
        assert result["covered_accounts"] == 1

    def test_beneficiary_coverage_none_covered(self):
        accounts = [{"id": "a1", "balance": 100_000}]
        bens = []
        result = EstatePlanningService.get_beneficiary_coverage_summary(accounts, bens)
        assert result["coverage_pct"] == 0.0
        assert result["covered_accounts"] == 0

    def test_beneficiary_coverage_partial(self):
        accounts = [
            {"id": "a1", "balance": 50_000},
            {"id": "a2", "balance": 50_000},
        ]
        bens = [{"account_id": "a1", "designation_type": "primary"}]
        result = EstatePlanningService.get_beneficiary_coverage_summary(accounts, bens)
        assert result["coverage_pct"] == 50.0

    def test_validate_beneficiary_pcts_valid(self):
        designations = [
            {"designation_type": "primary", "percentage": 60},
            {"designation_type": "primary", "percentage": 40},
        ]
        result = EstatePlanningService.validate_beneficiary_percentages(
            designations, "primary"
        )
        assert result["valid"] is True

    def test_validate_beneficiary_pcts_invalid(self):
        designations = [
            {"designation_type": "primary", "percentage": 60},
            {"designation_type": "primary", "percentage": 30},
        ]
        result = EstatePlanningService.validate_beneficiary_percentages(
            designations, "primary"
        )
        assert result["valid"] is False
        assert "90" in result["message"]

    def test_validate_no_designations_is_valid(self):
        result = EstatePlanningService.validate_beneficiary_percentages([], "primary")
        assert result["valid"] is True


# ── get_tax_exposure endpoint ─────────────────────────────────────────────────


@pytest.mark.unit
class TestGetTaxExposureEndpoint:
    async def test_returns_dict_with_required_keys(self):
        result = await get_tax_exposure(
            net_worth=5_000_000,
            filing_status="single",
            current_user=_make_user(),
        )
        assert "net_worth" in result
        assert "federal_exemption" in result
        assert "taxable_estate" in result
        assert "estimated_federal_tax" in result
        assert "above_exemption" in result

    async def test_married_has_higher_exemption_than_single(self):
        single = await get_tax_exposure(
            net_worth=10_000_000,
            filing_status="single",
            current_user=_make_user(),
        )
        married = await get_tax_exposure(
            net_worth=10_000_000,
            filing_status="married",
            current_user=_make_user(),
        )
        assert married["federal_exemption"] > single["federal_exemption"]


# ── list_beneficiaries endpoint ───────────────────────────────────────────────


@pytest.mark.unit
class TestListBeneficiariesEndpoint:
    async def test_returns_serialized_rows(self):
        mock_db = AsyncMock()
        user = _make_user()

        ben = Mock()
        ben.id = uuid4()
        ben.account_id = uuid4()
        ben.name = "Jane Doe"
        ben.relationship = "spouse"
        ben.designation_type = "primary"
        ben.percentage = Decimal("100.00")
        ben.dob = None
        ben.notes = None

        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = [ben]
        mock_db.execute.return_value = result_mock

        result = await list_beneficiaries(
            account_id=None, current_user=user, db=mock_db
        )

        assert len(result) == 1
        assert result[0]["name"] == "Jane Doe"
        assert result[0]["percentage"] == 100.0

    async def test_returns_empty_when_none(self):
        mock_db = AsyncMock()
        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result_mock

        result = await list_beneficiaries(
            account_id=None, current_user=_make_user(), db=mock_db
        )
        assert result == []


# ── create_beneficiary endpoint ───────────────────────────────────────────────


@pytest.mark.unit
class TestCreateBeneficiaryEndpoint:
    async def test_creates_and_returns_beneficiary(self):
        mock_db = AsyncMock()
        user = _make_user()

        new_ben = Mock()
        new_ben.id = uuid4()
        new_ben.name = "John Smith"
        new_ben.percentage = Decimal("50.00")

        mock_db.refresh = AsyncMock(return_value=None)
        # After add + commit + refresh, simulate reading from new_ben
        # We patch the Ben object that gets attached via db.add
        import app.api.v1.estate as estate_mod
        from unittest.mock import patch

        with patch.object(estate_mod, "Beneficiary") as MockBen:
            MockBen.return_value = new_ben
            result = await create_beneficiary(
                body=BeneficiaryCreate(
                    name="John Smith",
                    relationship="child",
                    designation_type="primary",
                    percentage=Decimal("50"),
                ),
                current_user=user,
                db=mock_db,
            )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        assert result["name"] == "John Smith"


# ── upsert_document endpoint ──────────────────────────────────────────────────


@pytest.mark.unit
class TestUpsertDocumentEndpoint:
    async def test_creates_new_document(self):
        mock_db = AsyncMock()
        user = _make_user()

        # Simulate: document not found (scalar_one_or_none returns None)
        find_result = Mock()
        find_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = find_result

        # Provide a real-ish object for refresh to operate on
        mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

        await upsert_document(
            body=EstateDocumentUpsert(
                document_type="will",
                last_reviewed_date=None,
            ),
            current_user=user,
            db=mock_db,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    async def test_updates_existing_document(self):
        from datetime import date

        mock_db = AsyncMock()
        user = _make_user()

        existing_doc = Mock()
        existing_doc.id = uuid4()
        existing_doc.document_type = "will"
        existing_doc.last_reviewed_date = date(2025, 1, 1)
        existing_doc.notes = None

        find_result = Mock()
        find_result.scalar_one_or_none.return_value = existing_doc
        mock_db.execute.return_value = find_result
        mock_db.refresh = AsyncMock(return_value=None)

        await upsert_document(
            body=EstateDocumentUpsert(
                document_type="will",
                last_reviewed_date=date(2026, 3, 1),
            ),
            current_user=user,
            db=mock_db,
        )

        # Should update in place, not add
        mock_db.add.assert_not_called()
        assert existing_doc.last_reviewed_date == date(2026, 3, 1)


# ── list_documents endpoint ───────────────────────────────────────────────────


@pytest.mark.unit
class TestListDocumentsEndpoint:
    async def test_returns_empty_when_none(self):
        mock_db = AsyncMock()
        result_mock = Mock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result_mock

        result = await list_documents(current_user=_make_user(), db=mock_db)
        assert result == []
