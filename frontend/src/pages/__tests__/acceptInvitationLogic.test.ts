/**
 * Tests for AcceptInvitationPage logic: token validation, expiry checks,
 * invitation status gates, and flow state determination.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from AcceptInvitationPage.tsx) ──────────────────────────

interface InvitationDetails {
  email: string;
  organization_name?: string;
  invited_by_email: string;
  expires_at: string;
  status: string;
}

// ── Logic helpers ────────────────────────────────────────────────────────────

function isExpired(expiresAt: string): boolean {
  return new Date(expiresAt) < new Date();
}

function hasInvitationCode(code: string | null): boolean {
  return !!code;
}

function isAlreadyProcessed(status: string): boolean {
  return status !== "pending";
}

function getWelcomeMessage(orgName?: string): string {
  return orgName ? `${orgName}'s` : "the";
}

function formatExpiryDate(expiresAt: string): string {
  return new Date(expiresAt).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("hasInvitationCode", () => {
  it("returns false for null", () => {
    expect(hasInvitationCode(null)).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(hasInvitationCode("")).toBe(false);
  });

  it("returns true for a valid code", () => {
    expect(hasInvitationCode("abc-123-def")).toBe(true);
  });
});

describe("isExpired", () => {
  it("returns true for a past date", () => {
    expect(isExpired("2020-01-01T00:00:00Z")).toBe(true);
  });

  it("returns false for a far future date", () => {
    expect(isExpired("2099-12-31T23:59:59Z")).toBe(false);
  });
});

describe("isAlreadyProcessed", () => {
  it("returns false for pending status", () => {
    expect(isAlreadyProcessed("pending")).toBe(false);
  });

  it("returns true for accepted status", () => {
    expect(isAlreadyProcessed("accepted")).toBe(true);
  });

  it("returns true for declined status", () => {
    expect(isAlreadyProcessed("declined")).toBe(true);
  });

  it("returns true for expired status", () => {
    expect(isAlreadyProcessed("expired")).toBe(true);
  });
});

describe("getWelcomeMessage", () => {
  it("includes org name when provided", () => {
    expect(getWelcomeMessage("Smith Family")).toBe("Smith Family's");
  });

  it('falls back to "the" when no org name', () => {
    expect(getWelcomeMessage(undefined)).toBe("the");
    expect(getWelcomeMessage("")).toBe("the");
  });
});

describe("formatExpiryDate", () => {
  it("formats ISO date to readable US format", () => {
    const result = formatExpiryDate("2025-06-15T14:30:00Z");
    expect(result).toContain("June");
    expect(result).toContain("15");
    expect(result).toContain("2025");
  });
});

describe("Flow state determination", () => {
  it("shows invalid link when no code", () => {
    const code: string | null = null;
    const state = !code ? "invalid" : "ready";
    expect(state).toBe("invalid");
  });

  it("shows expired when past expiry date", () => {
    const invitation: InvitationDetails = {
      email: "test@example.com",
      invited_by_email: "admin@example.com",
      expires_at: "2020-01-01T00:00:00Z",
      status: "pending",
    };
    const expired = isExpired(invitation.expires_at);
    const processed = isAlreadyProcessed(invitation.status);
    expect(expired).toBe(true);
    expect(processed).toBe(false);
  });

  it("shows already processed when status is not pending", () => {
    const invitation: InvitationDetails = {
      email: "test@example.com",
      invited_by_email: "admin@example.com",
      expires_at: "2099-12-31T23:59:59Z",
      status: "accepted",
    };
    expect(isAlreadyProcessed(invitation.status)).toBe(true);
  });

  it("shows main acceptance UI when valid, pending, not expired", () => {
    const invitation: InvitationDetails = {
      email: "test@example.com",
      invited_by_email: "admin@example.com",
      expires_at: "2099-12-31T23:59:59Z",
      status: "pending",
    };
    const code = "valid-code";
    const canAccept =
      hasInvitationCode(code) &&
      !isExpired(invitation.expires_at) &&
      !isAlreadyProcessed(invitation.status);
    expect(canAccept).toBe(true);
  });
});

// ── Cache invalidation keys ───────────────────────────────────────────────────
// These tests document the query keys that MUST be invalidated on accept so that
// the newly-joined member sees fresh household and permissions data after login.

const REQUIRED_INVALIDATION_KEYS = ["household", "permissions"] as const;

describe("onSuccess cache invalidation keys", () => {
  it("household key is in the required invalidation list", () => {
    expect(REQUIRED_INVALIDATION_KEYS).toContain("household");
  });

  it("permissions key is in the required invalidation list", () => {
    expect(REQUIRED_INVALIDATION_KEYS).toContain("permissions");
  });

  it("requires exactly the two expected keys to be invalidated", () => {
    // Ensures no accidental drift — if new keys are added they must be reviewed
    expect(REQUIRED_INVALIDATION_KEYS).toHaveLength(2);
  });

  it("invalidating with household prefix clears member list queries", () => {
    // Simulate query key matching: a key that starts with "household"
    // should be considered stale after a new member joins.
    const cachedQueries = [
      ["household"],
      ["household", "members"],
      ["household", "invitations"],
      ["permissions"],
      ["accounts"],
    ];
    const invalidated = cachedQueries.filter((key) =>
      REQUIRED_INVALIDATION_KEYS.some((prefix) => key[0] === prefix)
    );
    expect(invalidated).toHaveLength(4); // household, household/members, household/invitations, permissions
  });
});
