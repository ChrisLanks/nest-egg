"""Integration tests for transaction API endpoints."""

import pytest
from fastapi import status
from decimal import Decimal
from datetime import date, datetime, timedelta
from uuid import uuid4

pytestmark = pytest.mark.asyncio


class TestTransactionEndpoints:
    """Test suite for transaction API endpoints."""

    async def test_list_transactions_success(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should list transactions for authenticated user."""
        # Create test transactions
        from app.models.transaction import Transaction

        txn1 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Test Merchant",
            description="Test transaction",
        )
        txn2 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today() - timedelta(days=1),
            amount=Decimal("-25.00"),
            merchant_name="Another Merchant",
            description="Another transaction",
        )

        db.add_all([txn1, txn2])
        await db.commit()

        response = await client.get("/api/v1/transactions/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "transactions" in data
        assert len(data["transactions"]) >= 2

    async def test_list_transactions_requires_authentication(self, client):
        """Should require authentication."""
        response = await client.get("/api/v1/transactions/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_list_transactions_pagination(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should support cursor-based pagination."""
        # Create multiple transactions
        from app.models.transaction import Transaction

        transactions = []
        for i in range(10):
            txn = Transaction(
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=date.today() - timedelta(days=i),
                amount=Decimal(f"-{i + 1}.00"),
                merchant_name=f"Merchant {i}",
                description=f"Transaction {i}",
            )
            transactions.append(txn)

        db.add_all(transactions)
        await db.commit()

        # First page
        response = await client.get(
            "/api/v1/transactions/", params={"page_size": 5}, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["transactions"]) <= 5

        if data.get("next_cursor"):
            # Second page
            response2 = await client.get(
                "/api/v1/transactions/",
                params={"page_size": 5, "cursor": data["next_cursor"]},
                headers=auth_headers,
            )
            assert response2.status_code == status.HTTP_200_OK

    async def test_list_transactions_filter_by_account(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should filter transactions by account."""
        # Create another account
        from app.models.account import Account, AccountType

        account2 = Account(
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Second Account",
            account_type=AccountType.SAVINGS,
        )
        db.add(account2)
        await db.commit()
        await db.refresh(account2)

        # Create transactions in both accounts
        from app.models.transaction import Transaction

        txn1 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Merchant 1",
        )
        txn2 = Transaction(
            organization_id=test_user.organization_id,
            account_id=account2.id,
            date=date.today(),
            amount=Decimal("-25.00"),
            merchant_name="Merchant 2",
        )

        db.add_all([txn1, txn2])
        await db.commit()

        # Filter by first account
        response = await client.get(
            "/api/v1/transactions/",
            params={"account_id": str(test_account.id)},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All transactions should be from the first account
        for txn in data["transactions"]:
            assert txn["account_id"] == str(test_account.id)

    async def test_list_transactions_filter_by_date_range(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should filter transactions by date range."""
        from app.models.transaction import Transaction

        # Create transactions on different dates
        txn_old = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today() - timedelta(days=30),
            amount=Decimal("-10.00"),
            merchant_name="Old Transaction",
        )
        txn_recent = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-20.00"),
            merchant_name="Recent Transaction",
        )

        db.add_all([txn_old, txn_recent])
        await db.commit()

        # Filter by recent dates only
        start_date = (date.today() - timedelta(days=7)).isoformat()
        end_date = date.today().isoformat()

        response = await client.get(
            "/api/v1/transactions/",
            params={"start_date": start_date, "end_date": end_date},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only contain recent transaction
        for txn in data["transactions"]:
            txn_date = datetime.fromisoformat(txn["date"]).date()
            assert txn_date >= datetime.fromisoformat(start_date).date()
            assert txn_date <= datetime.fromisoformat(end_date).date()

    async def test_list_transactions_search(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should search transactions by merchant name."""
        from app.models.transaction import Transaction

        txn1 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Starbucks Coffee",
        )
        txn2 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-25.00"),
            merchant_name="McDonald's",
        )

        db.add_all([txn1, txn2])
        await db.commit()

        # Search for "Starbucks"
        response = await client.get(
            "/api/v1/transactions/", params={"search": "Starbucks"}, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only contain Starbucks transaction
        assert len(data["transactions"]) >= 1
        assert any("Starbucks" in txn["merchant_name"] for txn in data["transactions"])

    async def test_get_transaction_by_id_success(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should get single transaction by ID."""
        from app.models.transaction import Transaction

        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Test Merchant",
            description="Test description",
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        response = await client.get(f"/api/v1/transactions/{txn.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(txn.id)
        assert data["merchant_name"] == "Test Merchant"
        assert data["amount"] == "-50.00"

    async def test_get_transaction_not_found(self, client, auth_headers):
        """Should return 404 for non-existent transaction."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/transactions/{fake_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_transaction_requires_authentication(
        self, client, test_user, test_account, db
    ):
        """Should require authentication to get transaction."""
        from app.models.transaction import Transaction

        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Test",
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        response = await client.get(f"/api/v1/transactions/{txn.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_transaction_success(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should update transaction successfully."""
        from app.models.transaction import Transaction

        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Original Merchant",
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        # Update merchant name
        update_data = {"merchant_name": "Updated Merchant"}

        response = await client.patch(
            f"/api/v1/transactions/{txn.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["merchant_name"] == "Updated Merchant"

    async def test_update_transaction_multiple_fields(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should update multiple transaction fields."""
        from app.models.transaction import Transaction

        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Original",
            description="Original description",
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        update_data = {
            "merchant_name": "New Merchant",
            "description": "New description",
            "notes": "Added notes",
        }

        response = await client.patch(
            f"/api/v1/transactions/{txn.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["merchant_name"] == "New Merchant"
        assert data["description"] == "New description"
        assert data["notes"] == "Added notes"

    async def test_add_label_to_transaction(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should add label to transaction."""
        from app.models.transaction import Transaction, Label

        # Create transaction
        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Test",
        )

        # Create label
        label = Label(organization_id=test_user.organization_id, name="Test Label", color="#FF0000")

        db.add_all([txn, label])
        await db.commit()
        await db.refresh(txn)
        await db.refresh(label)

        response = await client.post(
            f"/api/v1/transactions/{txn.id}/labels/{label.id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED

    async def test_remove_label_from_transaction(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should remove label from transaction."""
        from app.models.transaction import Transaction, Label, TransactionLabel

        # Create transaction and label
        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Test",
        )
        label = Label(organization_id=test_user.organization_id, name="Test Label", color="#FF0000")

        db.add_all([txn, label])
        await db.commit()
        await db.refresh(txn)
        await db.refresh(label)

        # Add label
        txn_label = TransactionLabel(transaction_id=txn.id, label_id=label.id)
        db.add(txn_label)
        await db.commit()

        # Remove label
        response = await client.delete(
            f"/api/v1/transactions/{txn.id}/labels/{label.id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_export_transactions_csv(self, client, auth_headers, test_user, test_account, db):
        """Should export transactions to CSV."""
        from app.models.transaction import Transaction

        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Test Merchant",
            description="Test description",
        )
        db.add(txn)
        await db.commit()

        response = await client.get("/api/v1/transactions/export/csv", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        # Verify CSV content
        csv_content = response.text
        assert "Test Merchant" in csv_content


class TestTransactionSecurityAndValidation:
    """Security and validation tests for transaction endpoints."""

    async def test_sql_injection_in_search_parameter(self, client, auth_headers):
        """Should protect against SQL injection in search parameter."""
        malicious_search = "'; DROP TABLE transactions--"

        response = await client.get(
            "/api/v1/transactions/", params={"search": malicious_search}, headers=auth_headers
        )

        # Should not execute SQL, should just return no results or error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    async def test_xss_protection_in_merchant_name(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should escape XSS in merchant names."""
        from app.models.transaction import Transaction

        xss_merchant = "<script>alert('XSS')</script>"

        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name=xss_merchant,
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        response = await client.get(f"/api/v1/transactions/{txn.id}", headers=auth_headers)

        # Response should not contain unescaped script tags
        assert b"<script>" not in response.content

    async def test_invalid_date_format(self, client, auth_headers):
        """Should reject invalid date formats."""
        response = await client.get(
            "/api/v1/transactions/", params={"start_date": "invalid-date"}, headers=auth_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_invalid_cursor(self, client, auth_headers):
        """Should reject invalid cursor."""
        response = await client.get(
            "/api/v1/transactions/", params={"cursor": "invalid_cursor"}, headers=auth_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_cannot_access_other_organization_transactions(
        self, client, auth_headers, test_user, test_account, db
    ):
        """Should not allow access to transactions from other organizations."""
        from app.models.transaction import Transaction
        from app.models.account import Account, AccountType
        from app.models.user import Organization, User

        # Create another organization
        other_org = Organization(name="Other Org")
        db.add(other_org)
        await db.commit()
        await db.refresh(other_org)

        # Create user in other org
        other_user = User(
            organization_id=other_org.id, email="other@example.com", hashed_password="hashed"
        )
        db.add(other_user)
        await db.commit()
        await db.refresh(other_user)

        # Create account in other org
        other_account = Account(
            organization_id=other_org.id,
            user_id=other_user.id,
            name="Other Account",
            account_type=AccountType.CHECKING,
        )
        db.add(other_account)
        await db.commit()
        await db.refresh(other_account)

        # Create transaction in other org
        other_txn = Transaction(
            organization_id=other_org.id,
            account_id=other_account.id,
            date=date.today(),
            amount=Decimal("-100.00"),
            merchant_name="Other Org Transaction",
        )
        db.add(other_txn)
        await db.commit()
        await db.refresh(other_txn)

        # Try to access other org's transaction with current user's auth
        response = await client.get(f"/api/v1/transactions/{other_txn.id}", headers=auth_headers)

        # Should not find it (404) or forbidden (403)
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]
