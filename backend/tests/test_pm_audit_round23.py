"""Tests for PM audit round 23 fixes.

Covers:
- notification_service.mark_all_as_read: was updating org-wide notifications
  (user_id=NULL) which share a single is_read flag. When User A called
  mark-all-read, those shared notifications were marked read for the entire
  household — User B would see them as already read.

  Fix: scope the bulk update to user_id == user.id only. Org-wide notifications
  are excluded from the bulk update to preserve per-user read state.
"""

import inspect


def test_mark_all_as_read_excludes_org_wide_notifications():
    """mark_all_as_read must NOT update notifications where user_id IS NULL."""
    from app.services.notification_service import NotificationService

    source = inspect.getsource(NotificationService.mark_all_as_read)
    # Must NOT include the or_(... user_id.is_(None)) pattern
    assert "user_id.is_(None)" not in source, (
        "mark_all_as_read must not touch org-wide (user_id=NULL) notifications — "
        "they share a single is_read flag across all household members"
    )


def test_mark_all_as_read_scopes_to_user_id():
    """mark_all_as_read must filter strictly by user_id == user.id."""
    from app.services.notification_service import NotificationService

    source = inspect.getsource(NotificationService.mark_all_as_read)
    assert "Notification.user_id == user.id" in source, (
        "mark_all_as_read must use Notification.user_id == user.id (not or_ with None)"
    )


def test_mark_all_as_read_still_checks_org():
    """mark_all_as_read must still filter by organization_id as defense-in-depth."""
    from app.services.notification_service import NotificationService

    source = inspect.getsource(NotificationService.mark_all_as_read)
    assert "organization_id == user.organization_id" in source, (
        "mark_all_as_read must retain the organization_id filter"
    )


def test_per_notification_mark_read_still_checks_user_id():
    """Per-notification mark_as_read must still check user_id (from round 22 fix)."""
    from app.services.notification_service import NotificationService

    source = inspect.getsource(NotificationService.mark_as_read)
    assert "Notification.user_id == user.id" in source, (
        "Per-notification mark_as_read must check user_id (regression guard)"
    )


def test_per_notification_dismiss_still_checks_user_id():
    """Per-notification mark_as_dismissed must still check user_id (from round 22 fix)."""
    from app.services.notification_service import NotificationService

    source = inspect.getsource(NotificationService.mark_as_dismissed)
    assert "Notification.user_id == user.id" in source, (
        "Per-notification mark_as_dismissed must check user_id (regression guard)"
    )
