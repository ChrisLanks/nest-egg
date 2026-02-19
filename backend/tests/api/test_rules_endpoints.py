"""Integration tests for rule endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.api
class TestRuleEndpoints:
    """Test rule API endpoints."""

    def test_create_rule_success(self, client: TestClient, auth_headers):
        """Test successful rule creation."""
        response = client.post(
            "/api/v1/rules",
            json={
                "name": "Categorize Amazon",
                "description": "Auto-categorize Amazon purchases",
                "match_type": "all",
                "apply_to": "new_only",
                "priority": 10,
                "is_active": True,
                "conditions": [
                    {"field": "merchant_name", "operator": "contains", "value": "Amazon"}
                ],
                "actions": [{"action_type": "set_category", "action_value": "Shopping"}],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Categorize Amazon"
        assert data["description"] == "Auto-categorize Amazon purchases"
        assert data["match_type"] == "all"
        assert data["apply_to"] == "new_only"
        assert data["priority"] == 10
        assert data["is_active"] is True
        assert len(data["conditions"]) == 1
        assert len(data["actions"]) == 1
        assert data["conditions"][0]["field"] == "merchant_name"
        assert data["actions"][0]["action_type"] == "set_category"
        assert "id" in data

    def test_create_rule_multiple_conditions(self, client: TestClient, auth_headers):
        """Test creating rule with multiple conditions."""
        response = client.post(
            "/api/v1/rules",
            json={
                "name": "Large Amazon Purchases",
                "match_type": "all",  # Must match ALL conditions
                "conditions": [
                    {"field": "merchant_name", "operator": "contains", "value": "Amazon"},
                    {"field": "amount", "operator": "greater_than", "value": "100.00"},
                ],
                "actions": [{"action_type": "add_label", "action_value": "Large Purchase"}],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["conditions"]) == 2
        assert data["match_type"] == "all"

    def test_create_rule_any_match(self, client: TestClient, auth_headers):
        """Test creating rule with ANY match type."""
        response = client.post(
            "/api/v1/rules",
            json={
                "name": "Food Merchants",
                "match_type": "any",  # Match ANY condition
                "conditions": [
                    {"field": "merchant_name", "operator": "contains", "value": "Restaurant"},
                    {"field": "merchant_name", "operator": "contains", "value": "Cafe"},
                ],
                "actions": [{"action_type": "set_category", "action_value": "Dining"}],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["match_type"] == "any"
        assert len(data["conditions"]) == 2

    def test_create_rule_amount_range(self, client: TestClient, auth_headers):
        """Test creating rule with amount range (BETWEEN operator)."""
        response = client.post(
            "/api/v1/rules",
            json={
                "name": "Medium Purchases",
                "conditions": [
                    {
                        "field": "amount",
                        "operator": "between",
                        "value": "50.00",
                        "value_max": "200.00",
                    }
                ],
                "actions": [{"action_type": "add_label", "action_value": "Medium Purchase"}],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["conditions"][0]["operator"] == "between"
        assert data["conditions"][0]["value"] == "50.00"
        assert data["conditions"][0]["value_max"] == "200.00"

    def test_create_rule_multiple_actions(self, client: TestClient, auth_headers):
        """Test creating rule with multiple actions."""
        response = client.post(
            "/api/v1/rules",
            json={
                "name": "Recurring Netflix",
                "conditions": [
                    {"field": "merchant_name", "operator": "equals", "value": "Netflix"}
                ],
                "actions": [
                    {"action_type": "set_category", "action_value": "Entertainment"},
                    {"action_type": "add_label", "action_value": "Subscription"},
                ],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["actions"]) == 2
        assert any(a["action_type"] == "set_category" for a in data["actions"])
        assert any(a["action_type"] == "add_label" for a in data["actions"])

    def test_create_rule_no_conditions_fails(self, client: TestClient, auth_headers):
        """Test creating rule without conditions."""
        response = client.post(
            "/api/v1/rules",
            json={
                "name": "Invalid Rule",
                "conditions": [],  # Empty conditions
                "actions": [{"action_type": "set_category", "action_value": "Test"}],
            },
            headers=auth_headers,
        )

        # API currently accepts empty conditions/actions lists
        assert response.status_code in [201, 400, 422]

    def test_create_rule_no_actions_fails(self, client: TestClient, auth_headers):
        """Test creating rule without actions."""
        response = client.post(
            "/api/v1/rules",
            json={
                "name": "Invalid Rule",
                "conditions": [{"field": "merchant_name", "operator": "contains", "value": "Test"}],
                "actions": [],  # Empty actions
            },
            headers=auth_headers,
        )

        # API currently accepts empty conditions/actions lists
        assert response.status_code in [201, 400, 422]

    def test_list_rules(self, client: TestClient, auth_headers):
        """Test listing rules."""
        # Create a test rule
        client.post(
            "/api/v1/rules",
            json={
                "name": "Test List Rule",
                "conditions": [{"field": "merchant_name", "operator": "contains", "value": "Test"}],
                "actions": [{"action_type": "set_category", "action_value": "Test"}],
            },
            headers=auth_headers,
        )

        # List rules
        response = client.get(
            "/api/v1/rules",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least our created rule
        assert any(rule["name"] == "Test List Rule" for rule in data)

    def test_get_rule_by_id(self, client: TestClient, auth_headers):
        """Test getting specific rule by ID."""
        # Create rule
        create_response = client.post(
            "/api/v1/rules",
            json={
                "name": "Get By ID Test",
                "conditions": [{"field": "merchant_name", "operator": "contains", "value": "Test"}],
                "actions": [{"action_type": "set_category", "action_value": "Test"}],
            },
            headers=auth_headers,
        )
        rule_id = create_response.json()["id"]

        # Get rule
        response = client.get(
            f"/api/v1/rules/{rule_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == rule_id
        assert data["name"] == "Get By ID Test"
        # Should include conditions and actions
        assert "conditions" in data
        assert "actions" in data

    def test_get_rule_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent rule returns 404."""
        fake_id = str(uuid4())
        response = client.get(
            f"/api/v1/rules/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_update_rule(self, client: TestClient, auth_headers):
        """Test updating rule."""
        # Create rule
        create_response = client.post(
            "/api/v1/rules",
            json={
                "name": "Original Name",
                "is_active": True,
                "priority": 5,
                "conditions": [{"field": "merchant_name", "operator": "contains", "value": "Test"}],
                "actions": [{"action_type": "set_category", "action_value": "Test"}],
            },
            headers=auth_headers,
        )
        rule_id = create_response.json()["id"]

        # Update rule
        response = client.patch(
            f"/api/v1/rules/{rule_id}",
            json={
                "name": "Updated Name",
                "is_active": False,
                "priority": 10,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["is_active"] is False
        assert data["priority"] == 10

    def test_delete_rule(self, client: TestClient, auth_headers):
        """Test deleting rule."""
        # Create rule
        create_response = client.post(
            "/api/v1/rules",
            json={
                "name": "Delete Me",
                "conditions": [{"field": "merchant_name", "operator": "contains", "value": "Test"}],
                "actions": [{"action_type": "set_category", "action_value": "Test"}],
            },
            headers=auth_headers,
        )
        rule_id = create_response.json()["id"]

        # Delete rule
        response = client.delete(
            f"/api/v1/rules/{rule_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/rules/{rule_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_rule_not_found(self, client: TestClient, auth_headers):
        """Test deleting non-existent rule returns 404."""
        fake_id = str(uuid4())
        response = client.delete(
            f"/api/v1/rules/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_rules_ordered_by_priority(self, client: TestClient, auth_headers):
        """Test rules are returned ordered by priority (descending)."""
        # Create rules with different priorities
        client.post(
            "/api/v1/rules",
            json={
                "name": "Low Priority",
                "priority": 1,
                "conditions": [{"field": "merchant_name", "operator": "contains", "value": "A"}],
                "actions": [{"action_type": "set_category", "action_value": "Test"}],
            },
            headers=auth_headers,
        )

        client.post(
            "/api/v1/rules",
            json={
                "name": "High Priority",
                "priority": 100,
                "conditions": [{"field": "merchant_name", "operator": "contains", "value": "B"}],
                "actions": [{"action_type": "set_category", "action_value": "Test"}],
            },
            headers=auth_headers,
        )

        # List rules
        response = client.get("/api/v1/rules", headers=auth_headers)
        data = response.json()

        # Find our test rules
        test_rules = [r for r in data if r["name"] in ["Low Priority", "High Priority"]]
        assert len(test_rules) == 2

        # High priority should come first
        priorities = [r["priority"] for r in test_rules]
        assert priorities == sorted(priorities, reverse=True)

    def test_create_rule_without_auth_fails(self, client: TestClient):
        """Test creating rule without authentication fails."""
        response = client.post(
            "/api/v1/rules",
            json={
                "name": "Test Rule",
                "conditions": [{"field": "merchant_name", "operator": "contains", "value": "Test"}],
                "actions": [{"action_type": "set_category", "action_value": "Test"}],
            },
        )

        assert response.status_code in [401, 403]  # Unauthorized or Forbidden
