"""Unit tests for the household net worth breakdown service."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.account import AccountCategory, AccountType
from app.services.household_net_worth_service import (
    get_household_net_worth_breakdown,
)


def _make_account(
    account_type: AccountType,
    balance: float,
    user_id=None,
):
    acct = MagicMock()
    acct.account_type = account_type
    acct.current_balance = balance
    acct.user_id = user_id
    acct.is_active = True
    return acct


def _make_db(accounts: list):
    scalars = MagicMock()
    scalars.all.return_value = accounts
    result = MagicMock()
    result.scalars.return_value = scalars
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.unit
class TestHouseholdNetWorthBreakdown:
    @pytest.mark.asyncio
    async def test_empty_org_returns_empty_members(self):
        db = _make_db([])
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)

        assert breakdown.members == []
        assert breakdown.member_count == 0
        assert breakdown.total_net_worth == 0.0
        assert breakdown.total_assets == 0.0
        assert breakdown.total_debts == 0.0

    @pytest.mark.asyncio
    async def test_single_user_correct_totals(self):
        uid = uuid.uuid4()
        accounts = [
            _make_account(AccountType.CHECKING, 10_000, user_id=uid),
            _make_account(AccountType.BROKERAGE, 50_000, user_id=uid),
        ]
        db = _make_db(accounts)
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)

        assert breakdown.member_count == 1
        member = breakdown.members[0]
        assert member.user_id == uid
        assert member.total_assets == pytest.approx(60_000, abs=0.01)
        assert member.total_debts == pytest.approx(0.0, abs=0.01)
        assert member.net_worth == pytest.approx(60_000, abs=0.01)
        assert member.account_count == 2

    @pytest.mark.asyncio
    async def test_none_user_id_goes_to_joint_bucket(self):
        uid = uuid.uuid4()
        accounts = [
            _make_account(AccountType.SAVINGS, 5_000, user_id=uid),
            _make_account(AccountType.SAVINGS, 20_000, user_id=None),
        ]
        db = _make_db(accounts)
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)

        joint = next(m for m in breakdown.members if m.user_id is None)
        assert joint.display_name == "Joint / Unattributed"
        assert joint.total_assets == pytest.approx(20_000, abs=0.01)
        assert breakdown.member_count == 1

    @pytest.mark.asyncio
    async def test_assets_and_debts_split_correctly(self):
        uid = uuid.uuid4()
        accounts = [
            _make_account(AccountType.BROKERAGE, 100_000, user_id=uid),
            _make_account(AccountType.MORTGAGE, 80_000, user_id=uid),
        ]
        db = _make_db(accounts)
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)

        member = breakdown.members[0]
        assert member.total_assets == pytest.approx(100_000, abs=0.01)
        assert member.total_debts == pytest.approx(80_000, abs=0.01)
        assert member.net_worth == pytest.approx(20_000, abs=0.01)

    @pytest.mark.asyncio
    async def test_credit_card_is_debt(self):
        uid = uuid.uuid4()
        accounts = [
            _make_account(AccountType.CREDIT_CARD, 3_500, user_id=uid),
        ]
        db = _make_db(accounts)
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)

        member = breakdown.members[0]
        assert member.total_debts == pytest.approx(3_500, abs=0.01)
        assert member.total_assets == pytest.approx(0.0, abs=0.01)
        assert member.net_worth == pytest.approx(-3_500, abs=0.01)

    @pytest.mark.asyncio
    async def test_multiple_members_tracked_separately(self):
        uid1 = uuid.uuid4()
        uid2 = uuid.uuid4()
        accounts = [
            _make_account(AccountType.CHECKING, 10_000, user_id=uid1),
            _make_account(AccountType.BROKERAGE, 200_000, user_id=uid2),
        ]
        db = _make_db(accounts)
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)

        assert breakdown.member_count == 2
        uids = {m.user_id for m in breakdown.members}
        assert uid1 in uids
        assert uid2 in uids
        m1 = next(m for m in breakdown.members if m.user_id == uid1)
        m2 = next(m for m in breakdown.members if m.user_id == uid2)
        assert m1.total_assets == pytest.approx(10_000, abs=0.01)
        assert m2.total_assets == pytest.approx(200_000, abs=0.01)

    @pytest.mark.asyncio
    async def test_totals_aggregate_all_members(self):
        uid1 = uuid.uuid4()
        uid2 = uuid.uuid4()
        accounts = [
            _make_account(AccountType.SAVINGS, 10_000, user_id=uid1),
            _make_account(AccountType.SAVINGS, 30_000, user_id=uid2),
            _make_account(AccountType.MORTGAGE, 5_000, user_id=uid1),
        ]
        db = _make_db(accounts)
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)

        assert breakdown.total_assets == pytest.approx(40_000, abs=0.01)
        assert breakdown.total_debts == pytest.approx(5_000, abs=0.01)
        assert breakdown.total_net_worth == pytest.approx(35_000, abs=0.01)

    @pytest.mark.asyncio
    async def test_accounts_by_type_grouping(self):
        uid = uuid.uuid4()
        accounts = [
            _make_account(AccountType.CHECKING, 1_000, user_id=uid),
            _make_account(AccountType.CHECKING, 2_000, user_id=uid),
            _make_account(AccountType.BROKERAGE, 50_000, user_id=uid),
        ]
        db = _make_db(accounts)
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)

        member = breakdown.members[0]
        assert AccountType.CHECKING.value in member.accounts_by_type
        assert AccountType.BROKERAGE.value in member.accounts_by_type
        assert member.accounts_by_type[AccountType.CHECKING.value] == pytest.approx(3_000, abs=0.01)
        assert member.accounts_by_type[AccountType.BROKERAGE.value] == pytest.approx(50_000, abs=0.01)

    @pytest.mark.asyncio
    async def test_display_name_from_map(self):
        uid = uuid.uuid4()
        accounts = [_make_account(AccountType.SAVINGS, 1_000, user_id=uid)]
        db = _make_db(accounts)
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(
            db, org_id, member_display_names={uid: "Alice"}
        )

        assert breakdown.members[0].display_name == "Alice"

    @pytest.mark.asyncio
    async def test_display_name_fallback_to_member_number(self):
        uid = uuid.uuid4()
        accounts = [_make_account(AccountType.SAVINGS, 1_000, user_id=uid)]
        db = _make_db(accounts)
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)

        assert breakdown.members[0].display_name == "Member 1"

    @pytest.mark.asyncio
    async def test_organization_id_echoed(self):
        db = _make_db([])
        org_id = uuid.uuid4()
        breakdown = await get_household_net_worth_breakdown(db, org_id)
        assert breakdown.organization_id == org_id
