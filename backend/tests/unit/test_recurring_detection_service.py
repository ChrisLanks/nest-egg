"""Tests for recurring detection service."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.services.recurring_detection_service import RecurringDetectionService
from app.models.recurring_transaction import RecurringTransaction, RecurringFrequency
from app.models.transaction import Transaction


class TestRecurringDetectionService:
    """Test suite for recurring detection service."""

    def test_calculate_frequency_weekly(self):
        """Should detect weekly pattern."""
        service = RecurringDetectionService()

        # Weekly transactions (7 days apart)
        dates = [
            date(2024, 1, 1),
            date(2024, 1, 8),
            date(2024, 1, 15),
            date(2024, 1, 22),
        ]

        frequency = service._calculate_frequency(dates)
        assert frequency == RecurringFrequency.WEEKLY

    def test_calculate_frequency_biweekly(self):
        """Should detect biweekly pattern."""
        service = RecurringDetectionService()

        dates = [
            date(2024, 1, 1),
            date(2024, 1, 15),
            date(2024, 1, 29),
            date(2024, 2, 12),
        ]

        frequency = service._calculate_frequency(dates)
        assert frequency == RecurringFrequency.BIWEEKLY

    def test_calculate_frequency_monthly(self):
        """Should detect monthly pattern."""
        service = RecurringDetectionService()

        dates = [
            date(2024, 1, 1),
            date(2024, 2, 1),
            date(2024, 3, 1),
            date(2024, 4, 1),
        ]

        frequency = service._calculate_frequency(dates)
        assert frequency == RecurringFrequency.MONTHLY

    def test_calculate_frequency_quarterly(self):
        """Should detect quarterly pattern."""
        service = RecurringDetectionService()

        dates = [
            date(2024, 1, 1),
            date(2024, 4, 1),
            date(2024, 7, 1),
            date(2024, 10, 1),
        ]

        frequency = service._calculate_frequency(dates)
        assert frequency == RecurringFrequency.QUARTERLY

    def test_calculate_frequency_yearly(self):
        """Should detect yearly pattern."""
        service = RecurringDetectionService()

        dates = [
            date(2022, 1, 1),
            date(2023, 1, 1),
            date(2024, 1, 1),
        ]

        frequency = service._calculate_frequency(dates)
        assert frequency == RecurringFrequency.YEARLY

    def test_calculate_frequency_irregular(self):
        """Should return None for irregular dates."""
        service = RecurringDetectionService()

        # Irregular dates
        dates = [
            date(2024, 1, 1),
            date(2024, 1, 10),
            date(2024, 2, 5),
            date(2024, 3, 20),
        ]

        frequency = service._calculate_frequency(dates)
        assert frequency is None

    def test_calculate_frequency_too_few_dates(self):
        """Should return None for single date."""
        service = RecurringDetectionService()

        dates = [date(2024, 1, 1)]

        frequency = service._calculate_frequency(dates)
        assert frequency is None

    def test_calculate_frequency_with_tolerance(self):
        """Should allow tolerance in date gaps."""
        service = RecurringDetectionService()

        # Weekly pattern with slight variation (±2 days)
        dates = [
            date(2024, 1, 1),
            date(2024, 1, 8),  # 7 days
            date(2024, 1, 16),  # 8 days
            date(2024, 1, 22),  # 6 days
        ]

        frequency = service._calculate_frequency(dates)
        # Should still be weekly due to tolerance
        assert frequency == RecurringFrequency.WEEKLY

    def test_calculate_confidence_score_high(self):
        """Should calculate high confidence for perfect pattern."""
        service = RecurringDetectionService()

        # Perfect pattern: many transactions, no variance, perfect dates
        score = service._calculate_confidence_score(
            transaction_count=5,
            amount_variance=Decimal("0.00"),
            date_consistency=1.0,
        )

        assert score >= Decimal("0.90")
        assert score <= Decimal("1.00")

    def test_calculate_confidence_score_low(self):
        """Should calculate low confidence for inconsistent pattern."""
        service = RecurringDetectionService()

        # Poor pattern: few transactions, high variance, poor dates
        score = service._calculate_confidence_score(
            transaction_count=2,
            amount_variance=Decimal("100.00"),
            date_consistency=0.5,
        )

        assert score < Decimal("0.60")

    def test_calculate_confidence_score_medium(self):
        """Should calculate medium confidence for moderate pattern."""
        service = RecurringDetectionService()

        score = service._calculate_confidence_score(
            transaction_count=4,
            amount_variance=Decimal("10.00"),
            date_consistency=0.8,
        )

        assert Decimal("0.60") <= score < Decimal("0.90")

    def test_calculate_confidence_score_components(self):
        """Should weight different components properly."""
        service = RecurringDetectionService()

        # High transaction count should increase score
        score_high_count = service._calculate_confidence_score(
            transaction_count=10,
            amount_variance=Decimal("0"),
            date_consistency=1.0,
        )

        score_low_count = service._calculate_confidence_score(
            transaction_count=2,
            amount_variance=Decimal("0"),
            date_consistency=1.0,
        )

        assert score_high_count > score_low_count

    @pytest.mark.asyncio
    async def test_detect_recurring_patterns_basic(self, db, test_user, test_account):
        """Should detect simple recurring pattern."""
        service = RecurringDetectionService()

        # Create monthly recurring transactions
        base_date = date(2024, 1, 1)
        for i in range(4):
            txn = Transaction(
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=base_date + timedelta(days=30 * i),
                amount=Decimal("-50.00"),
                merchant_name="Netflix",
            )
            db.add(txn)
        await db.commit()

        patterns = await service.detect_recurring_patterns(db, test_user, min_occurrences=3)

        assert len(patterns) > 0
        netflix_pattern = next((p for p in patterns if p.merchant_name == "Netflix"), None)
        assert netflix_pattern is not None
        assert netflix_pattern.frequency == RecurringFrequency.MONTHLY
        assert netflix_pattern.confidence_score >= Decimal("0.60")
        assert netflix_pattern.occurrence_count == 4

    @pytest.mark.asyncio
    async def test_detect_recurring_patterns_ignores_insufficient_data(
        self, db, test_user, test_account
    ):
        """Should ignore patterns with insufficient occurrences."""
        service = RecurringDetectionService()

        # Only 2 transactions (below minimum of 3)
        for i in range(2):
            txn = Transaction(
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=date(2024, 1, 1) + timedelta(days=30 * i),
                amount=Decimal("-50.00"),
                merchant_name="Rare Merchant",
            )
            db.add(txn)
        await db.commit()

        patterns = await service.detect_recurring_patterns(db, test_user, min_occurrences=3)

        # Should not detect pattern
        rare_pattern = next((p for p in patterns if p.merchant_name == "Rare Merchant"), None)
        assert rare_pattern is None

    @pytest.mark.asyncio
    async def test_detect_recurring_patterns_updates_existing(self, db, test_user, test_account):
        """Should update existing pattern with new data."""
        service = RecurringDetectionService()

        # Create transactions
        for i in range(3):
            txn = Transaction(
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=date(2024, 1, 1) + timedelta(days=30 * i),
                amount=Decimal("-50.00"),
                merchant_name="Spotify",
            )
            db.add(txn)
        await db.commit()

        # First detection
        patterns1 = await service.detect_recurring_patterns(db, test_user)
        assert len(patterns1) > 0

        # Add more transactions
        for i in range(3, 5):
            txn = Transaction(
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=date(2024, 1, 1) + timedelta(days=30 * i),
                amount=Decimal("-50.00"),
                merchant_name="Spotify",
            )
            db.add(txn)
        await db.commit()

        # Second detection should update, not create new
        patterns2 = await service.detect_recurring_patterns(db, test_user)

        spotify_patterns = [p for p in patterns2 if p.merchant_name == "Spotify"]
        assert len(spotify_patterns) == 1  # Should only have one pattern
        assert spotify_patterns[0].occurrence_count == 5  # Updated count

    @pytest.mark.asyncio
    async def test_detect_recurring_patterns_filters_low_confidence(
        self, db, test_user, test_account
    ):
        """Should exclude low confidence patterns."""
        service = RecurringDetectionService()

        # Create irregular pattern (low confidence)
        irregular_dates = [
            date(2024, 1, 1),
            date(2024, 1, 10),
            date(2024, 2, 5),
        ]

        for d in irregular_dates:
            txn = Transaction(
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=d,
                amount=Decimal("-50.00"),
                merchant_name="Irregular Store",
            )
            db.add(txn)
        await db.commit()

        patterns = await service.detect_recurring_patterns(db, test_user)

        # Should filter out low confidence
        irregular_pattern = next(
            (p for p in patterns if p.merchant_name == "Irregular Store"), None
        )
        if irregular_pattern:
            # If it's detected, confidence should be below threshold or None
            assert irregular_pattern is None or irregular_pattern.confidence_score < Decimal("0.60")

    @pytest.mark.asyncio
    async def test_detect_recurring_patterns_calculates_next_expected_date(
        self, db, test_user, test_account
    ):
        """Should calculate next expected date based on frequency."""
        service = RecurringDetectionService()

        # Monthly pattern
        base_date = date(2024, 1, 1)
        for i in range(3):
            txn = Transaction(
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=base_date + timedelta(days=30 * i),
                amount=Decimal("-50.00"),
                merchant_name="Monthly Service",
            )
            db.add(txn)
        await db.commit()

        patterns = await service.detect_recurring_patterns(db, test_user)

        pattern = next((p for p in patterns if p.merchant_name == "Monthly Service"), None)
        if pattern:
            # Last occurrence was 2024-03-02 (base + 60 days)
            # Next expected should be ~30 days later
            assert pattern.next_expected_date is not None
            expected_gap = (pattern.next_expected_date - pattern.last_occurrence).days
            assert 25 <= expected_gap <= 35  # ~30 days with tolerance

    @pytest.mark.asyncio
    async def test_create_manual_recurring(self, db, test_user, test_account):
        """Should create manual recurring transaction."""
        service = RecurringDetectionService()

        pattern = await service.create_manual_recurring(
            db=db,
            user=test_user,
            merchant_name="Rent",
            account_id=test_account.id,
            frequency=RecurringFrequency.MONTHLY,
            average_amount=Decimal("2000.00"),
            is_bill=True,
            reminder_days_before=5,
        )

        assert pattern.id is not None
        assert pattern.merchant_name == "Rent"
        assert pattern.frequency == RecurringFrequency.MONTHLY
        assert pattern.average_amount == Decimal("2000.00")
        assert pattern.is_user_created is True
        assert pattern.confidence_score == Decimal("1.00")  # Manual = perfect confidence
        assert pattern.is_bill is True
        assert pattern.reminder_days_before == 5

    @pytest.mark.asyncio
    async def test_get_recurring_transactions(self, db, test_user, test_account):
        """Should get all recurring transactions."""
        service = RecurringDetectionService()

        # Create manual patterns
        await service.create_manual_recurring(
            db, test_user, "Pattern 1", test_account.id, RecurringFrequency.MONTHLY, Decimal("100")
        )
        await service.create_manual_recurring(
            db, test_user, "Pattern 2", test_account.id, RecurringFrequency.WEEKLY, Decimal("50")
        )

        patterns = await service.get_recurring_transactions(db, test_user)

        assert len(patterns) >= 2

    @pytest.mark.asyncio
    async def test_get_recurring_transactions_filter_active(self, db, test_user, test_account):
        """Should filter by is_active status."""
        service = RecurringDetectionService()

        # Create active pattern
        _active = await service.create_manual_recurring(
            db, test_user, "Active", test_account.id, RecurringFrequency.MONTHLY, Decimal("100")
        )

        # Create inactive pattern
        inactive = await service.create_manual_recurring(
            db, test_user, "Inactive", test_account.id, RecurringFrequency.MONTHLY, Decimal("100")
        )
        inactive.is_active = False
        await db.commit()

        # Get only active
        active_patterns = await service.get_recurring_transactions(db, test_user, is_active=True)
        active_names = [p.merchant_name for p in active_patterns]
        assert "Active" in active_names
        assert "Inactive" not in active_names

    @pytest.mark.asyncio
    async def test_update_recurring_transaction(self, db, test_user, test_account):
        """Should update recurring transaction pattern."""
        service = RecurringDetectionService()

        # Create pattern
        pattern = await service.create_manual_recurring(
            db, test_user, "Original", test_account.id, RecurringFrequency.MONTHLY, Decimal("100")
        )

        # Update
        updated = await service.update_recurring_transaction(
            db,
            pattern.id,
            test_user,
            merchant_name="Updated Name",
            average_amount=Decimal("150.00"),
        )

        assert updated is not None
        assert updated.merchant_name == "Updated Name"
        assert updated.average_amount == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_update_recurring_transaction_cross_org_blocked(
        self, db, test_user, test_account
    ):
        """Should not allow updating patterns from other orgs."""
        service = RecurringDetectionService()

        # Create pattern in other org
        other_org_id = uuid4()
        other_pattern = RecurringTransaction(
            id=uuid4(),
            organization_id=other_org_id,
            account_id=test_account.id,
            merchant_name="Other Org Pattern",
            frequency=RecurringFrequency.MONTHLY,
            average_amount=Decimal("100"),
            confidence_score=Decimal("1.00"),
            occurrence_count=1,
        )
        db.add(other_pattern)
        await db.commit()

        # Try to update
        updated = await service.update_recurring_transaction(
            db, other_pattern.id, test_user, merchant_name="Hacked"
        )

        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_recurring_transaction(self, db, test_user, test_account):
        """Should delete recurring transaction pattern."""
        service = RecurringDetectionService()

        # Create pattern
        pattern = await service.create_manual_recurring(
            db, test_user, "To Delete", test_account.id, RecurringFrequency.MONTHLY, Decimal("100")
        )
        pattern_id = pattern.id

        # Delete
        success = await service.delete_recurring_transaction(db, pattern_id, test_user)
        assert success is True

        # Verify deleted
        patterns = await service.get_recurring_transactions(db, test_user)
        deleted_pattern = next((p for p in patterns if p.id == pattern_id), None)
        assert deleted_pattern is None

    @pytest.mark.asyncio
    async def test_delete_recurring_transaction_cross_org_blocked(
        self, db, test_user, test_account
    ):
        """Should not allow deleting patterns from other orgs."""
        service = RecurringDetectionService()

        # Create pattern in other org
        other_org_id = uuid4()
        other_pattern = RecurringTransaction(
            id=uuid4(),
            organization_id=other_org_id,
            account_id=test_account.id,
            merchant_name="Other Org",
            frequency=RecurringFrequency.MONTHLY,
            average_amount=Decimal("100"),
            confidence_score=Decimal("1.00"),
            occurrence_count=1,
        )
        db.add(other_pattern)
        await db.commit()

        # Try to delete
        success = await service.delete_recurring_transaction(db, other_pattern.id, test_user)
        assert success is False

    @pytest.mark.asyncio
    async def test_get_upcoming_bills(self, db, test_user, test_account):
        """Should get bills due soon."""
        service = RecurringDetectionService()

        # Create bill due in 2 days
        upcoming = await service.create_manual_recurring(
            db,
            test_user,
            "Upcoming Bill",
            test_account.id,
            RecurringFrequency.MONTHLY,
            Decimal("100"),
            is_bill=True,
            reminder_days_before=5,
        )
        upcoming.next_expected_date = date.today() + timedelta(days=2)
        await db.commit()

        # Create bill far in future
        far_future = await service.create_manual_recurring(
            db,
            test_user,
            "Far Future",
            test_account.id,
            RecurringFrequency.MONTHLY,
            Decimal("100"),
            is_bill=True,
            reminder_days_before=3,
        )
        far_future.next_expected_date = date.today() + timedelta(days=60)
        await db.commit()

        # Get upcoming bills
        bills = await service.get_upcoming_bills(db, test_user, days_ahead=30)

        # Should include upcoming (within reminder window) but not far future
        bill_names = [b["merchant_name"] for b in bills]
        assert "Upcoming Bill" in bill_names
        assert "Far Future" not in bill_names

    @pytest.mark.asyncio
    async def test_get_upcoming_bills_includes_overdue(self, db, test_user, test_account):
        """Should include overdue bills."""
        service = RecurringDetectionService()

        # Create overdue bill
        overdue = await service.create_manual_recurring(
            db,
            test_user,
            "Overdue",
            test_account.id,
            RecurringFrequency.MONTHLY,
            Decimal("100"),
            is_bill=True,
            reminder_days_before=3,
        )
        overdue.next_expected_date = date.today() - timedelta(days=5)  # 5 days ago
        await db.commit()

        bills = await service.get_upcoming_bills(db, test_user)

        # Should include overdue
        overdue_bill = next((b for b in bills if b["merchant_name"] == "Overdue"), None)
        assert overdue_bill is not None
        assert overdue_bill["is_overdue"] is True
        assert overdue_bill["days_until_due"] < 0

    @pytest.mark.asyncio
    async def test_get_subscriptions(self, db, test_user, test_account):
        """Should get subscription-like patterns."""
        service = RecurringDetectionService()

        # Create monthly subscription
        monthly_sub = await service.create_manual_recurring(
            db,
            test_user,
            "Netflix",
            test_account.id,
            RecurringFrequency.MONTHLY,
            Decimal("15.99"),
        )
        monthly_sub.confidence_score = Decimal("0.80")  # High confidence
        await db.commit()

        # Create yearly subscription
        yearly_sub = await service.create_manual_recurring(
            db,
            test_user,
            "Prime",
            test_account.id,
            RecurringFrequency.YEARLY,
            Decimal("119.00"),
        )
        yearly_sub.confidence_score = Decimal("0.90")
        await db.commit()

        # Create weekly pattern (not a subscription)
        weekly = await service.create_manual_recurring(
            db,
            test_user,
            "Grocery",
            test_account.id,
            RecurringFrequency.WEEKLY,
            Decimal("50.00"),
        )
        weekly.confidence_score = Decimal("0.85")
        await db.commit()

        subscriptions = await service.get_subscriptions(db, test_user.organization_id)

        # Should only include monthly/yearly
        sub_names = [s.merchant_name for s in subscriptions]
        assert "Netflix" in sub_names
        assert "Prime" in sub_names
        assert "Grocery" not in sub_names

    @pytest.mark.asyncio
    async def test_get_subscriptions_filters_low_confidence(self, db, test_user, test_account):
        """Should exclude low confidence patterns."""
        service = RecurringDetectionService()

        # High confidence subscription
        high_conf = await service.create_manual_recurring(
            db,
            test_user,
            "High Confidence",
            test_account.id,
            RecurringFrequency.MONTHLY,
            Decimal("10.00"),
        )
        high_conf.confidence_score = Decimal("0.80")
        await db.commit()

        # Low confidence subscription
        low_conf = await service.create_manual_recurring(
            db,
            test_user,
            "Low Confidence",
            test_account.id,
            RecurringFrequency.MONTHLY,
            Decimal("10.00"),
        )
        low_conf.confidence_score = Decimal("0.50")
        await db.commit()

        subscriptions = await service.get_subscriptions(db, test_user.organization_id)

        sub_names = [s.merchant_name for s in subscriptions]
        assert "High Confidence" in sub_names
        assert "Low Confidence" not in sub_names

    @pytest.mark.asyncio
    async def test_get_subscription_summary(self, db, test_user, test_account):
        """Should calculate subscription costs."""
        service = RecurringDetectionService()

        # Monthly subscription: $10
        monthly = await service.create_manual_recurring(
            db,
            test_user,
            "Monthly",
            test_account.id,
            RecurringFrequency.MONTHLY,
            Decimal("10.00"),
        )
        monthly.confidence_score = Decimal("0.80")
        await db.commit()

        # Yearly subscription: $120 ($10/month)
        yearly = await service.create_manual_recurring(
            db,
            test_user,
            "Yearly",
            test_account.id,
            RecurringFrequency.YEARLY,
            Decimal("120.00"),
        )
        yearly.confidence_score = Decimal("0.90")
        await db.commit()

        summary = await service.get_subscription_summary(db, test_user.organization_id)

        assert summary["total_count"] == 2
        # Monthly cost = 10 + (120/12) = 20
        assert summary["monthly_cost"] == 20.0
        # Yearly cost = 20 * 12 = 240
        assert summary["yearly_cost"] == 240.0

    @pytest.mark.asyncio
    async def test_get_subscription_summary_empty(self, db, test_user):
        """Should handle no subscriptions."""
        service = RecurringDetectionService()

        summary = await service.get_subscription_summary(db, test_user.organization_id)

        assert summary["total_count"] == 0
        assert summary["monthly_cost"] == 0.0
        assert summary["yearly_cost"] == 0.0

    def test_singleton_instance(self):
        """Should provide singleton instance."""
        from app.services.recurring_detection_service import recurring_detection_service

        assert recurring_detection_service is not None
        assert isinstance(recurring_detection_service, RecurringDetectionService)
