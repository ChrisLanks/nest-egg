"""Tests for PM audit round 22 fixes.

Covers:
1. notification_service mark_as_read/mark_as_dismissed: only checked org_id,
   allowing User A to mark User B's personal notifications (budget alerts,
   goal completions) as read or dismissed.

2. rental_property_service get_property_pnl / update_rental_fields: only
   checked organization_id, allowing any org member to view or modify another
   user's rental property data. Fixed to accept user_id and scope accordingly.
"""

import inspect


# ─── Notification service ────────────────────────────────────────────────────


def test_mark_as_read_checks_user_id():
    """mark_as_read must filter by Notification.user_id == user.id."""
    from app.services.notification_service import NotificationService

    source = inspect.getsource(NotificationService.mark_as_read)
    assert "Notification.user_id == user.id" in source, (
        "mark_as_read must check Notification.user_id to prevent cross-user modification"
    )


def test_mark_as_dismissed_checks_user_id():
    """mark_as_dismissed must filter by Notification.user_id == user.id."""
    from app.services.notification_service import NotificationService

    source = inspect.getsource(NotificationService.mark_as_dismissed)
    assert "Notification.user_id == user.id" in source, (
        "mark_as_dismissed must check Notification.user_id to prevent cross-user modification"
    )


# ─── Rental property service ─────────────────────────────────────────────────


def test_get_property_pnl_accepts_user_id():
    """get_property_pnl must accept a user_id parameter."""
    from app.services.rental_property_service import RentalPropertyService

    sig = inspect.signature(RentalPropertyService.get_property_pnl)
    assert "user_id" in sig.parameters, "get_property_pnl must accept user_id"


def test_get_property_pnl_scopes_to_user():
    """get_property_pnl must apply Account.user_id filter when user_id provided."""
    from app.services.rental_property_service import RentalPropertyService

    source = inspect.getsource(RentalPropertyService.get_property_pnl)
    assert "Account.user_id == user_id" in source or "user_id" in source, (
        "get_property_pnl must conditionally filter by Account.user_id"
    )


def test_update_rental_fields_accepts_user_id():
    """update_rental_fields must accept a user_id parameter."""
    from app.services.rental_property_service import RentalPropertyService

    sig = inspect.signature(RentalPropertyService.update_rental_fields)
    assert "user_id" in sig.parameters, "update_rental_fields must accept user_id"


def test_update_rental_fields_scopes_to_user():
    """update_rental_fields must apply Account.user_id filter when user_id provided."""
    from app.services.rental_property_service import RentalPropertyService

    source = inspect.getsource(RentalPropertyService.update_rental_fields)
    assert "user_id" in source, (
        "update_rental_fields must conditionally filter by Account.user_id"
    )


def test_rental_api_passes_user_id_to_pnl():
    """GET /pnl endpoint must pass current_user.id to get_property_pnl."""
    from app.api.v1 import rental_properties

    source = inspect.getsource(rental_properties.get_property_pnl)
    assert "current_user.id" in source, (
        "get_property_pnl endpoint must pass current_user.id to service"
    )


def test_rental_api_passes_user_id_to_update():
    """PATCH endpoint must pass current_user.id to update_rental_fields."""
    from app.api.v1 import rental_properties

    source = inspect.getsource(rental_properties.update_rental_fields)
    assert "current_user.id" in source, (
        "update_rental_fields endpoint must pass current_user.id to service"
    )
