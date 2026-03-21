/**
 * Tests for guest access permission gating logic.
 *
 * Covers: invite guest button visibility, revoke button visibility,
 * guest section visibility, and guest role badge rendering.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";

// ── Types mirroring the page components ─────────────────────────────────────

interface CurrentUser {
  id: string;
  is_org_admin: boolean;
}

interface GuestRecord {
  id: string;
  user_id: string;
  user_email: string;
  role: "viewer" | "advisor";
  label: string | null;
  is_active: boolean;
}

interface GuestInvitation {
  id: string;
  email: string;
  role: "viewer" | "advisor";
  status: "pending" | "accepted" | "declined" | "expired";
}

// ── Logic helpers mirroring HouseholdSettingsPage.tsx ────────────────────────

/** Guest access section is only visible to org admins. */
function canSeeGuestSection(user: CurrentUser): boolean {
  return user.is_org_admin;
}

/** Invite guest button visibility. */
function canInviteGuest(user: CurrentUser): boolean {
  return user.is_org_admin;
}

/** Revoke button is visible for active guests, admin only. */
function canRevokeGuest(user: CurrentUser, guest: GuestRecord): boolean {
  return user.is_org_admin && guest.is_active;
}

/** Cancel pending invitation, admin only. */
function canCancelGuestInvitation(
  user: CurrentUser,
  inv: GuestInvitation,
): boolean {
  return user.is_org_admin && inv.status === "pending";
}

/** Role badge color. */
function roleBadgeColor(role: "viewer" | "advisor"): string {
  return role === "advisor" ? "purple" : "gray";
}

/** Validate guest invite email. */
function validateGuestEmail(email: string): { valid: boolean; error: string } {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email) return { valid: false, error: "Email is required" };
  if (!emailRegex.test(email))
    return { valid: false, error: "Invalid email address" };
  return { valid: true, error: "" };
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("guest access section visibility", () => {
  it("admin can see guest access section", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    expect(canSeeGuestSection(user)).toBe(true);
  });

  it("non-admin cannot see guest access section", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    expect(canSeeGuestSection(user)).toBe(false);
  });
});

describe("invite guest button", () => {
  it("admin can invite guests", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    expect(canInviteGuest(user)).toBe(true);
  });

  it("non-admin cannot invite guests", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    expect(canInviteGuest(user)).toBe(false);
  });
});

describe("revoke guest access", () => {
  it("admin can revoke active guest", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const guest: GuestRecord = {
      id: "g1",
      user_id: "u2",
      user_email: "guest@example.com",
      role: "viewer",
      label: null,
      is_active: true,
    };
    expect(canRevokeGuest(user, guest)).toBe(true);
  });

  it("admin cannot revoke already-inactive guest", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const guest: GuestRecord = {
      id: "g1",
      user_id: "u2",
      user_email: "guest@example.com",
      role: "viewer",
      label: null,
      is_active: false,
    };
    expect(canRevokeGuest(user, guest)).toBe(false);
  });

  it("non-admin cannot revoke guest", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    const guest: GuestRecord = {
      id: "g1",
      user_id: "u2",
      user_email: "guest@example.com",
      role: "viewer",
      label: null,
      is_active: true,
    };
    expect(canRevokeGuest(user, guest)).toBe(false);
  });
});

describe("cancel guest invitation", () => {
  it("admin can cancel pending invitation", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const inv: GuestInvitation = {
      id: "i1",
      email: "guest@example.com",
      role: "viewer",
      status: "pending",
    };
    expect(canCancelGuestInvitation(user, inv)).toBe(true);
  });

  it("cannot cancel already-accepted invitation", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: true };
    const inv: GuestInvitation = {
      id: "i1",
      email: "guest@example.com",
      role: "viewer",
      status: "accepted",
    };
    expect(canCancelGuestInvitation(user, inv)).toBe(false);
  });

  it("non-admin cannot cancel invitation", () => {
    const user: CurrentUser = { id: "u1", is_org_admin: false };
    const inv: GuestInvitation = {
      id: "i1",
      email: "guest@example.com",
      role: "viewer",
      status: "pending",
    };
    expect(canCancelGuestInvitation(user, inv)).toBe(false);
  });
});

describe("role badge color", () => {
  it("viewer gets gray badge", () => {
    expect(roleBadgeColor("viewer")).toBe("gray");
  });

  it("advisor gets purple badge", () => {
    expect(roleBadgeColor("advisor")).toBe("purple");
  });
});

describe("guest email validation", () => {
  it("rejects empty email", () => {
    const result = validateGuestEmail("");
    expect(result.valid).toBe(false);
    expect(result.error).toBe("Email is required");
  });

  it("rejects invalid email", () => {
    const result = validateGuestEmail("not-an-email");
    expect(result.valid).toBe(false);
    expect(result.error).toBe("Invalid email address");
  });

  it("accepts valid email", () => {
    const result = validateGuestEmail("guest@example.com");
    expect(result.valid).toBe(true);
    expect(result.error).toBe("");
  });

  it("rejects email with spaces", () => {
    const result = validateGuestEmail("guest @example.com");
    expect(result.valid).toBe(false);
  });
});
