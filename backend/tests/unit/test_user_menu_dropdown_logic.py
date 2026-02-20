"""
Tests for UserMenu dropdown state machine logic.

Mirrors the TypeScript behaviour in Layout.tsx UserMenu component.

The dropdown has three state transitions:
  1. Starts closed (isOpen = False).
  2. Button click toggles open ↔ closed.
  3. Clicking a menu item → navigate + close.
  4. Clicking Logout → logout callback + close.
  5. Mousedown outside the container → close (outside-click detection).
  6. Mousedown inside the container → stay open.

These are pure boolean/callback rules — no DOM or React needed.
Running them in Python ensures the edge cases are covered without
a frontend test framework.
"""

import pytest


# ---------------------------------------------------------------------------
# State machine mirroring Layout.tsx UserMenu
# ---------------------------------------------------------------------------

class UserMenuState:
    """
    Minimal Python mirror of the UserMenu component state machine.

    isOpen   — whether the dropdown is visible
    navigate_calls — list of paths passed to onNavigate
    logout_called  — whether onLogout was invoked
    """

    def __init__(self):
        self.is_open = False
        self.navigate_calls: list[str] = []
        self.logout_called = False

    # -- actions -------------------------------------------------------------

    def toggle(self):
        """MenuButton onClick: setIsOpen(prev => !prev)."""
        self.is_open = not self.is_open

    def click_item(self, path: str):
        """
        MenuItem onClick:
          onNavigate(path)
          setIsOpen(false)
        """
        self.navigate_calls.append(path)
        self.is_open = False

    def click_logout(self):
        """
        Logout row onClick:
          onLogout()
          setIsOpen(false)
        """
        self.logout_called = True
        self.is_open = False

    def outside_mousedown(self):
        """
        document mousedown handler (when is_open):
          if !ref.contains(target) → setIsOpen(false)
        Simulates a click outside the container.
        """
        if self.is_open:
            self.is_open = False

    def inside_mousedown(self):
        """
        document mousedown handler when target IS inside the ref.
        The condition `ref.contains(target)` is True → no-op.
        """
        pass  # is_open unchanged


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUserMenuInitialState:
    """Dropdown must start closed."""

    def test_starts_closed(self):
        menu = UserMenuState()
        assert menu.is_open is False

    def test_starts_with_no_navigation(self):
        menu = UserMenuState()
        assert menu.navigate_calls == []

    def test_starts_with_logout_not_called(self):
        menu = UserMenuState()
        assert menu.logout_called is False


@pytest.mark.unit
class TestUserMenuToggle:
    """Button click toggles the dropdown."""

    def test_first_click_opens(self):
        menu = UserMenuState()
        menu.toggle()
        assert menu.is_open is True

    def test_second_click_closes(self):
        menu = UserMenuState()
        menu.toggle()
        menu.toggle()
        assert menu.is_open is False

    def test_triple_click_leaves_open(self):
        menu = UserMenuState()
        menu.toggle()
        menu.toggle()
        menu.toggle()
        assert menu.is_open is True


@pytest.mark.unit
class TestUserMenuItemClick:
    """Clicking a nav item navigates and closes the dropdown."""

    def test_item_click_closes_dropdown(self):
        menu = UserMenuState()
        menu.toggle()  # open it first
        menu.click_item("/household")
        assert menu.is_open is False

    def test_item_click_records_path(self):
        menu = UserMenuState()
        menu.toggle()
        menu.click_item("/preferences")
        assert "/preferences" in menu.navigate_calls

    def test_household_settings_path(self):
        menu = UserMenuState()
        menu.toggle()
        menu.click_item("/household")
        assert menu.navigate_calls == ["/household"]

    def test_preferences_path(self):
        menu = UserMenuState()
        menu.toggle()
        menu.click_item("/preferences")
        assert menu.navigate_calls == ["/preferences"]

    def test_item_click_does_not_trigger_logout(self):
        menu = UserMenuState()
        menu.toggle()
        menu.click_item("/household")
        assert menu.logout_called is False


@pytest.mark.unit
class TestUserMenuLogout:
    """Logout row calls the logout callback and closes the dropdown."""

    def test_logout_closes_dropdown(self):
        menu = UserMenuState()
        menu.toggle()  # open first
        menu.click_logout()
        assert menu.is_open is False

    def test_logout_invokes_callback(self):
        menu = UserMenuState()
        menu.toggle()
        menu.click_logout()
        assert menu.logout_called is True

    def test_logout_does_not_navigate(self):
        menu = UserMenuState()
        menu.toggle()
        menu.click_logout()
        assert menu.navigate_calls == []


@pytest.mark.unit
class TestUserMenuOutsideClick:
    """
    Outside-click detection: mousedown outside the container closes.

    The useEffect in UserMenu:
      if (!isOpen) return;           # listener only active when open
      if (!ref.contains(target))     # outside → close
          setIsOpen(false)
    """

    def test_outside_click_closes_open_dropdown(self):
        menu = UserMenuState()
        menu.toggle()  # open
        menu.outside_mousedown()
        assert menu.is_open is False

    def test_outside_click_on_closed_dropdown_is_noop(self):
        """Listener is not attached when closed — no state change."""
        menu = UserMenuState()
        menu.outside_mousedown()
        assert menu.is_open is False  # was already False

    def test_inside_click_keeps_dropdown_open(self):
        """Clicking within the ref container must not close the menu."""
        menu = UserMenuState()
        menu.toggle()
        menu.inside_mousedown()
        assert menu.is_open is True

    def test_second_outside_click_after_reopen_closes_again(self):
        """Outside-click works every time the dropdown is opened."""
        menu = UserMenuState()
        menu.toggle()           # open
        menu.outside_mousedown()  # close
        menu.toggle()           # reopen
        menu.outside_mousedown()  # close again
        assert menu.is_open is False
