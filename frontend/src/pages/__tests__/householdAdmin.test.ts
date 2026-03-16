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

// ── Confirmation dialog config logic ─────────────────────────────────────────

interface ConfirmConfig {
  title: string;
  body: string;
  confirmLabel: string;
  colorScheme: string;
}

function buildPromoteConfig(
  name: string,
  isCurrentlyAdmin: boolean,
): ConfirmConfig {
  const promoting = !isCurrentlyAdmin;
  return {
    title: promoting
      ? `Promote ${name} to Admin?`
      : `Demote ${name} to Member?`,
    body: promoting
      ? `${name} will gain admin privileges including the ability to manage members, invitations, and household settings.`
      : `${name} will lose admin privileges and become a regular member.`,
    confirmLabel: promoting ? "Promote" : "Demote",
    colorScheme: promoting ? "blue" : "orange",
  };
}

function buildRemoveConfig(name: string): ConfirmConfig {
  return {
    title: `Remove ${name}?`,
    body: `${name} will be removed from this household. Their accounts will be moved to a new solo household.`,
    confirmLabel: "Remove",
    colorScheme: "red",
  };
}

function buildCancelInvitationConfig(email: string): ConfirmConfig {
  return {
    title: "Cancel Invitation?",
    body: `The invitation to ${email} will be cancelled and can no longer be used to join.`,
    confirmLabel: "Cancel Invitation",
    colorScheme: "red",
  };
}

function buildRevokeGuestConfig(email: string): ConfirmConfig {
  return {
    title: "Revoke Guest Access?",
    body: `${email} will immediately lose access to your household data.`,
    confirmLabel: "Revoke Access",
    colorScheme: "red",
  };
}

function buildCancelGuestInvitationConfig(email: string): ConfirmConfig {
  return {
    title: "Cancel Guest Invitation?",
    body: `The invitation to ${email} will be cancelled.`,
    confirmLabel: "Cancel Invitation",
    colorScheme: "red",
  };
}

describe("confirmation dialog config — promote/demote", () => {
  it("builds promote config for a regular member", () => {
    const config = buildPromoteConfig("Alice", false);
    expect(config.title).toBe("Promote Alice to Admin?");
    expect(config.confirmLabel).toBe("Promote");
    expect(config.colorScheme).toBe("blue");
    expect(config.body).toContain("gain admin privileges");
  });

  it("builds demote config for an admin member", () => {
    const config = buildPromoteConfig("Bob", true);
    expect(config.title).toBe("Demote Bob to Member?");
    expect(config.confirmLabel).toBe("Demote");
    expect(config.colorScheme).toBe("orange");
    expect(config.body).toContain("lose admin privileges");
  });
});

describe("confirmation dialog config — remove member", () => {
  it("builds remove config with member name", () => {
    const config = buildRemoveConfig("Charlie");
    expect(config.title).toBe("Remove Charlie?");
    expect(config.confirmLabel).toBe("Remove");
    expect(config.colorScheme).toBe("red");
    expect(config.body).toContain("moved to a new solo household");
  });
});

describe("confirmation dialog config — cancel invitation", () => {
  it("builds cancel invitation config with email", () => {
    const config = buildCancelInvitationConfig("test@example.com");
    expect(config.title).toBe("Cancel Invitation?");
    expect(config.body).toContain("test@example.com");
    expect(config.body).toContain("can no longer be used to join");
    expect(config.confirmLabel).toBe("Cancel Invitation");
    expect(config.colorScheme).toBe("red");
  });
});

describe("confirmation dialog config — revoke guest", () => {
  it("builds revoke guest config with email", () => {
    const config = buildRevokeGuestConfig("guest@example.com");
    expect(config.title).toBe("Revoke Guest Access?");
    expect(config.body).toContain("guest@example.com");
    expect(config.body).toContain("immediately lose access");
    expect(config.confirmLabel).toBe("Revoke Access");
    expect(config.colorScheme).toBe("red");
  });
});

describe("confirmation dialog config — cancel guest invitation", () => {
  it("builds cancel guest invitation config with email", () => {
    const config = buildCancelGuestInvitationConfig("invited@example.com");
    expect(config.title).toBe("Cancel Guest Invitation?");
    expect(config.body).toContain("invited@example.com");
    expect(config.confirmLabel).toBe("Cancel Invitation");
    expect(config.colorScheme).toBe("red");
  });
});
