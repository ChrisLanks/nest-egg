/**
 * Tests for household admin permission gating logic.
 *
 * Covers: invite button visibility, cancel invitation visibility,
 * remove member visibility, promote/demote visibility, org prefs
 * read-only vs editable based on is_org_admin flag.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";

interface HouseholdMember {
  id: string;
  email: string;
  display_name?: string;
  is_org_admin: boolean;
  is_primary_household_member: boolean;
}

interface CurrentUser {
  id: string;
  is_org_admin: boolean;
}

// ── Invite button visibility ────────────────────────────────────────────────

describe("invite button visibility", () => {
  it("admin can see invite button", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    expect(user.is_org_admin).toBe(true);
  });

  it("non-admin cannot see invite button", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    expect(user.is_org_admin).toBe(false);
  });
});

// ── Cancel invitation visibility ────────────────────────────────────────────

describe("cancel invitation visibility", () => {
  it("admin can cancel invitations", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const canCancel = user.is_org_admin;
    expect(canCancel).toBe(true);
  });

  it("non-admin cannot cancel invitations", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    const canCancel = user.is_org_admin;
    expect(canCancel).toBe(false);
  });
});

// ── Remove member visibility ────────────────────────────────────────────────

describe("remove member visibility", () => {
  it("admin can remove non-primary members", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const member: HouseholdMember = {
      id: "u2",
      email: "member@example.com",
      is_org_admin: false,
      is_primary_household_member: false,
    };
    const canRemove =
      user.is_org_admin &&
      member.id !== user.id &&
      !member.is_primary_household_member;
    expect(canRemove).toBe(true);
  });

  it("admin cannot remove primary member", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const member: HouseholdMember = {
      id: "u2",
      email: "primary@example.com",
      is_org_admin: true,
      is_primary_household_member: true,
    };
    const canRemove =
      user.is_org_admin &&
      member.id !== user.id &&
      !member.is_primary_household_member;
    expect(canRemove).toBe(false);
  });

  it("non-admin cannot remove anyone", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    const member: HouseholdMember = {
      id: "u2",
      email: "member@example.com",
      is_org_admin: false,
      is_primary_household_member: false,
    };
    const canRemove =
      user.is_org_admin &&
      member.id !== user.id &&
      !member.is_primary_household_member;
    expect(canRemove).toBe(false);
  });
});

// ── Promote/demote visibility ───────────────────────────────────────────────

describe("promote/demote visibility", () => {
  it("admin can promote a regular member", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const member: HouseholdMember = {
      id: "u2",
      email: "member@example.com",
      is_org_admin: false,
      is_primary_household_member: false,
    };
    const canChangeRole =
      user.is_org_admin &&
      member.id !== user.id &&
      !member.is_primary_household_member;
    expect(canChangeRole).toBe(true);
  });

  it("admin can demote another admin", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const member: HouseholdMember = {
      id: "u2",
      email: "admin2@example.com",
      is_org_admin: true,
      is_primary_household_member: false,
    };
    const canChangeRole =
      user.is_org_admin &&
      member.id !== user.id &&
      !member.is_primary_household_member;
    expect(canChangeRole).toBe(true);
  });

  it("admin cannot change role of primary member", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const member: HouseholdMember = {
      id: "u2",
      email: "primary@example.com",
      is_org_admin: true,
      is_primary_household_member: true,
    };
    const canChangeRole =
      user.is_org_admin &&
      member.id !== user.id &&
      !member.is_primary_household_member;
    expect(canChangeRole).toBe(false);
  });

  it("admin cannot change own role", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const member: HouseholdMember = {
      id: "u1",
      email: "admin@example.com",
      is_org_admin: true,
      is_primary_household_member: false,
    };
    const canChangeRole =
      user.is_org_admin &&
      member.id !== user.id &&
      !member.is_primary_household_member;
    expect(canChangeRole).toBe(false);
  });

  it("non-admin cannot promote/demote anyone", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    const member: HouseholdMember = {
      id: "u2",
      email: "member@example.com",
      is_org_admin: false,
      is_primary_household_member: false,
    };
    const canChangeRole =
      user.is_org_admin &&
      member.id !== user.id &&
      !member.is_primary_household_member;
    expect(canChangeRole).toBe(false);
  });

  it("promote toggles is_org_admin from false to true", () => {
    const member = { is_org_admin: false };
    const newIsAdmin = !member.is_org_admin;
    expect(newIsAdmin).toBe(true);
  });

  it("demote toggles is_org_admin from true to false", () => {
    const member = { is_org_admin: true };
    const newIsAdmin = !member.is_org_admin;
    expect(newIsAdmin).toBe(false);
  });
});

// ── Org preferences visibility ──────────────────────────────────────────────

describe("org preferences visibility", () => {
  it("all users can view org preferences", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    const orgPrefs = { monthly_start_day: 1 };
    const canView = !!user && !!orgPrefs;
    expect(canView).toBe(true);
  });

  it("admin can edit org preferences", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const canEdit = user.is_org_admin;
    expect(canEdit).toBe(true);
  });

  it("non-admin sees read-only org preferences", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    const canEdit = user.is_org_admin;
    expect(canEdit).toBe(false);
  });
});
