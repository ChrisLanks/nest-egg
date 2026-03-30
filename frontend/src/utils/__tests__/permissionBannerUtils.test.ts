import { describe, it, expect } from "vitest";
import {
  getBannerAccess,
  getMultiMemberAccess,
  getResourceTypeForPath,
  ROUTE_TO_RESOURCE_TYPE,
  RESOURCE_TYPE_LABELS,
} from "../permissionBannerUtils";
import type { PermissionGrant } from "../../features/permissions/api/permissionsApi";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const GRANTOR = "user-owner-id";
const GRANTEE = "user-viewer-id";
const ORG = "org-id";

const futureDate = () => new Date(Date.now() + 10 * 60 * 1000).toISOString(); // +10 min
const pastDate = () => new Date(Date.now() - 10 * 60 * 1000).toISOString(); // -10 min

function makeGrant(overrides: Partial<PermissionGrant> = {}): PermissionGrant {
  return {
    id: "grant-1",
    organization_id: ORG,
    grantor_id: GRANTOR,
    grantee_id: GRANTEE,
    resource_type: "transaction",
    resource_id: null,
    actions: ["read"],
    granted_at: new Date().toISOString(),
    expires_at: null,
    is_active: true,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// getBannerAccess
// ---------------------------------------------------------------------------

describe("getBannerAccess", () => {
  it('returns "none" when resourceType is undefined', () => {
    expect(getBannerAccess([makeGrant()], GRANTOR, undefined)).toBe("none");
  });

  it('returns "none" when grants array is empty', () => {
    expect(getBannerAccess([], GRANTOR, "transaction")).toBe("none");
  });

  it('returns "read" for a read-only grant on the matching resource type', () => {
    const grants = [
      makeGrant({ resource_type: "transaction", actions: ["read"] }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("read");
  });

  it('returns "write" when grant includes create', () => {
    const grants = [
      makeGrant({ resource_type: "transaction", actions: ["read", "create"] }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("write");
  });

  it('returns "write" when grant includes update', () => {
    const grants = [
      makeGrant({ resource_type: "transaction", actions: ["update"] }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("write");
  });

  it('returns "write" when grant includes delete', () => {
    const grants = [
      makeGrant({ resource_type: "transaction", actions: ["delete"] }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("write");
  });

  it('returns "none" when the grant is for a different resource type', () => {
    const grants = [
      makeGrant({ resource_type: "account", actions: ["read", "create"] }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("none");
  });

  it('returns "none" when the grant is from a different grantor', () => {
    const grants = [
      makeGrant({
        grantor_id: "other-user",
        resource_type: "transaction",
        actions: ["read"],
      }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("none");
  });

  it('returns "none" when the grant is inactive (is_active false)', () => {
    const grants = [
      makeGrant({
        is_active: false,
        resource_type: "transaction",
        actions: ["read"],
      }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("none");
  });

  it('returns "none" when the grant is expired', () => {
    const grants = [
      makeGrant({
        resource_type: "transaction",
        actions: ["read"],
        expires_at: pastDate(),
      }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("none");
  });

  it('returns "read" when the grant has a future expiry', () => {
    const grants = [
      makeGrant({
        resource_type: "transaction",
        actions: ["read"],
        expires_at: futureDate(),
      }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("read");
  });

  it('returns "write" when one of multiple grants has write access', () => {
    const grants = [
      makeGrant({ id: "g1", resource_type: "transaction", actions: ["read"] }),
      makeGrant({
        id: "g2",
        resource_type: "transaction",
        actions: ["create", "update"],
      }),
    ];
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("write");
  });

  it('returns "write" for the correct resource type when mixed grants exist', () => {
    const grants = [
      makeGrant({ id: "g1", resource_type: "account", actions: ["read"] }), // read on accounts
      makeGrant({
        id: "g2",
        resource_type: "transaction",
        actions: ["create"],
      }), // write on transactions
    ];
    expect(getBannerAccess(grants, GRANTOR, "account")).toBe("read");
    expect(getBannerAccess(grants, GRANTOR, "transaction")).toBe("write");
    expect(getBannerAccess(grants, GRANTOR, "holding")).toBe("none");
  });
});

// ---------------------------------------------------------------------------
// getResourceTypeForPath
// ---------------------------------------------------------------------------

describe("getResourceTypeForPath", () => {
  it("resolves known exact paths", () => {
    expect(getResourceTypeForPath("/overview")).toBe("account");
    expect(getResourceTypeForPath("/accounts")).toBe("account");
    expect(getResourceTypeForPath("/transactions")).toBe("transaction");
    expect(getResourceTypeForPath("/categories")).toBe("category");
    expect(getResourceTypeForPath("/rules")).toBe("rule");
    expect(getResourceTypeForPath("/recurring")).toBe("recurring_transaction");
    expect(getResourceTypeForPath("/bills")).toBe("recurring_transaction");
    expect(getResourceTypeForPath("/investments")).toBe("holding");
    expect(getResourceTypeForPath("/budgets")).toBe("budget");
    expect(getResourceTypeForPath("/goals")).toBe("savings_goal");
    expect(getResourceTypeForPath("/cash-flow")).toBe("report");
    expect(getResourceTypeForPath("/trends")).toBe("report");
    expect(getResourceTypeForPath("/reports")).toBe("report");
    expect(getResourceTypeForPath("/tax-deductible")).toBe("report");
    expect(getResourceTypeForPath("/debt-payoff")).toBe("report");
    expect(getResourceTypeForPath("/year-in-review")).toBe("report");
    expect(getResourceTypeForPath("/rental-properties")).toBe("report");
    expect(getResourceTypeForPath("/education")).toBe("education_plan");
    expect(getResourceTypeForPath("/fire")).toBe("fire_plan");
    expect(getResourceTypeForPath("/calendar")).toBe("recurring_transaction");
    expect(getResourceTypeForPath("/retirement")).toBe("retirement_scenario");
    expect(getResourceTypeForPath("/mortgage")).toBe("report");
    expect(getResourceTypeForPath("/ss-claiming")).toBe("report");
    expect(getResourceTypeForPath("/tax-projection")).toBe("report");
    expect(getResourceTypeForPath("/smart-insights")).toBe("report");
    expect(getResourceTypeForPath("/investment-health")).toBe("report");
  });

  it("resolves dynamic sub-routes via prefix matching", () => {
    expect(getResourceTypeForPath("/accounts/some-uuid-here")).toBe("account");
    expect(getResourceTypeForPath("/transactions/abc-123")).toBe("transaction");
  });

  it("returns undefined for unknown paths", () => {
    expect(getResourceTypeForPath("/unknown-page")).toBeUndefined();
    expect(getResourceTypeForPath("/permissions")).toBeUndefined();
    expect(getResourceTypeForPath("/household")).toBeUndefined();
    expect(getResourceTypeForPath("/")).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// ROUTE_TO_RESOURCE_TYPE — structural checks
// ---------------------------------------------------------------------------

describe("ROUTE_TO_RESOURCE_TYPE", () => {
  it("contains the post-login destination /overview", () => {
    expect(ROUTE_TO_RESOURCE_TYPE["/overview"]).toBeDefined();
  });

  it("every mapped value has a human-readable label in RESOURCE_TYPE_LABELS", () => {
    const missingLabels = [
      ...new Set(Object.values(ROUTE_TO_RESOURCE_TYPE)),
    ].filter((type) => !RESOURCE_TYPE_LABELS[type]);
    expect(missingLabels).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Household default-access semantics
// ---------------------------------------------------------------------------

describe("Household default read access", () => {
  it('getBannerAccess returns "none" when no explicit grant exists', () => {
    // The utility accurately reports no explicit grant.
    // The UI layer (Layout) is responsible for treating "none" as read-only,
    // since household members always have implicit read access to each other's data.
    expect(getBannerAccess([], GRANTOR, "transaction")).toBe("none");
  });

  it('"none" is semantically distinct from "read" so callers can choose the display', () => {
    const readGrant = [makeGrant({ actions: ["read"] })];
    expect(getBannerAccess(readGrant, GRANTOR, "transaction")).toBe("read");
    expect(getBannerAccess([], GRANTOR, "transaction")).toBe("none");
  });
});

// ---------------------------------------------------------------------------
// getMultiMemberAccess
// ---------------------------------------------------------------------------

const SELF = "current-user-id";
const MEMBER_A = "member-aaa";
const MEMBER_B = "member-bbb";

describe("getMultiMemberAccess", () => {
  it("excludes the current user from the result", () => {
    const selected = new Set([SELF, MEMBER_A]);
    const result = getMultiMemberAccess([], SELF, selected, "transaction");
    expect(result).toHaveLength(1);
    expect(result[0].memberId).toBe(MEMBER_A);
  });

  it("returns empty array when only self is selected", () => {
    const selected = new Set([SELF]);
    const result = getMultiMemberAccess([], SELF, selected, "transaction");
    expect(result).toHaveLength(0);
  });

  it('returns "none" for members with no grants', () => {
    const selected = new Set([SELF, MEMBER_A, MEMBER_B]);
    const result = getMultiMemberAccess([], SELF, selected, "transaction");
    expect(result).toHaveLength(2);
    expect(result.find((r) => r.memberId === MEMBER_A)?.access).toBe("none");
    expect(result.find((r) => r.memberId === MEMBER_B)?.access).toBe("none");
  });

  it('returns "read" for a member with a read-only grant', () => {
    const grants = [
      makeGrant({
        grantor_id: MEMBER_A,
        resource_type: "transaction",
        actions: ["read"],
      }),
    ];
    const selected = new Set([SELF, MEMBER_A]);
    const result = getMultiMemberAccess(grants, SELF, selected, "transaction");
    expect(result[0].access).toBe("read");
  });

  it('returns "write" for a member with a write grant', () => {
    const grants = [
      makeGrant({
        grantor_id: MEMBER_A,
        resource_type: "transaction",
        actions: ["read", "update"],
      }),
    ];
    const selected = new Set([SELF, MEMBER_A]);
    const result = getMultiMemberAccess(grants, SELF, selected, "transaction");
    expect(result[0].access).toBe("write");
  });

  it("returns different access levels per member", () => {
    const grants = [
      makeGrant({
        id: "g1",
        grantor_id: MEMBER_A,
        resource_type: "account",
        actions: ["read", "create"],
      }),
      makeGrant({
        id: "g2",
        grantor_id: MEMBER_B,
        resource_type: "account",
        actions: ["read"],
      }),
    ];
    const selected = new Set([SELF, MEMBER_A, MEMBER_B]);
    const result = getMultiMemberAccess(grants, SELF, selected, "account");
    expect(result.find((r) => r.memberId === MEMBER_A)?.access).toBe("write");
    expect(result.find((r) => r.memberId === MEMBER_B)?.access).toBe("read");
  });

  it('returns "none" for all when resourceType is undefined', () => {
    const grants = [
      makeGrant({
        grantor_id: MEMBER_A,
        resource_type: "transaction",
        actions: ["read"],
      }),
    ];
    const selected = new Set([SELF, MEMBER_A]);
    const result = getMultiMemberAccess(grants, SELF, selected, undefined);
    expect(result[0].access).toBe("none");
  });

  it("ignores expired grants", () => {
    const grants = [
      makeGrant({
        grantor_id: MEMBER_A,
        resource_type: "transaction",
        actions: ["read", "update"],
        expires_at: pastDate(),
      }),
    ];
    const selected = new Set([SELF, MEMBER_A]);
    const result = getMultiMemberAccess(grants, SELF, selected, "transaction");
    expect(result[0].access).toBe("none");
  });

  it("respects future expiry dates", () => {
    const grants = [
      makeGrant({
        grantor_id: MEMBER_A,
        resource_type: "transaction",
        actions: ["read"],
        expires_at: futureDate(),
      }),
    ];
    const selected = new Set([SELF, MEMBER_A]);
    const result = getMultiMemberAccess(grants, SELF, selected, "transaction");
    expect(result[0].access).toBe("read");
  });

  it("ignores inactive grants", () => {
    const grants = [
      makeGrant({
        grantor_id: MEMBER_A,
        resource_type: "transaction",
        actions: ["read", "update"],
        is_active: false,
      }),
    ];
    const selected = new Set([SELF, MEMBER_A]);
    const result = getMultiMemberAccess(grants, SELF, selected, "transaction");
    expect(result[0].access).toBe("none");
  });

  it("handles empty selectedMemberIds", () => {
    const result = getMultiMemberAccess([], SELF, new Set(), "transaction");
    expect(result).toHaveLength(0);
  });
});
