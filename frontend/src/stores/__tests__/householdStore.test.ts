/**
 * Tests for the household store logic.
 *
 * Covers: setActiveHousehold, guest role resolution, revoked household reset,
 * and the fetchGuestHouseholds auto-reset behavior.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";

// ── Inline types mirroring the store ────────────────────────────────────────

interface GuestHousehold {
  organization_id: string;
  organization_name: string;
  role: "viewer" | "advisor";
  label: string | null;
  is_active: boolean;
}

interface HouseholdState {
  activeHouseholdId: string | null;
  activeHouseholdName: string | null;
  guestHouseholds: GuestHousehold[];
  isGuest: boolean;
  guestRole: "viewer" | "advisor" | null;
}

// ── Pure logic helpers mirroring householdStore.ts ──────────────────────────

function setActiveHousehold(
  state: HouseholdState,
  id: string | null,
  name: string | null = null,
): HouseholdState {
  if (!id) {
    return {
      ...state,
      activeHouseholdId: null,
      activeHouseholdName: null,
      isGuest: false,
      guestRole: null,
    };
  }

  const household = state.guestHouseholds.find((h) => h.organization_id === id);
  return {
    ...state,
    activeHouseholdId: id,
    activeHouseholdName: name || household?.organization_name || null,
    isGuest: true,
    guestRole: household?.role || "viewer",
  };
}

/** Simulates the revocation check inside fetchGuestHouseholds. */
function checkActiveStillValid(
  state: HouseholdState,
  fetchedHouseholds: GuestHousehold[],
): HouseholdState {
  const updated = { ...state, guestHouseholds: fetchedHouseholds };
  if (
    updated.activeHouseholdId &&
    !fetchedHouseholds.some(
      (h) => h.organization_id === updated.activeHouseholdId,
    )
  ) {
    return setActiveHousehold(updated, null);
  }
  return updated;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const makeHousehold = (
  overrides: Partial<GuestHousehold> = {},
): GuestHousehold => ({
  organization_id: "org-1",
  organization_name: "Smith Family",
  role: "viewer",
  label: null,
  is_active: true,
  ...overrides,
});

const defaultState = (): HouseholdState => ({
  activeHouseholdId: null,
  activeHouseholdName: null,
  guestHouseholds: [],
  isGuest: false,
  guestRole: null,
});

// ── Tests ───────────────────────────────────────────────────────────────────

describe("setActiveHousehold", () => {
  it("setting null resets to home context", () => {
    const state: HouseholdState = {
      ...defaultState(),
      activeHouseholdId: "org-1",
      isGuest: true,
      guestRole: "viewer",
    };
    const result = setActiveHousehold(state, null);
    expect(result.activeHouseholdId).toBeNull();
    expect(result.isGuest).toBe(false);
    expect(result.guestRole).toBeNull();
  });

  it("setting a guest household activates guest mode", () => {
    const state: HouseholdState = {
      ...defaultState(),
      guestHouseholds: [makeHousehold()],
    };
    const result = setActiveHousehold(state, "org-1");
    expect(result.activeHouseholdId).toBe("org-1");
    expect(result.isGuest).toBe(true);
    expect(result.guestRole).toBe("viewer");
    expect(result.activeHouseholdName).toBe("Smith Family");
  });

  it("resolves advisor role from guest list", () => {
    const state: HouseholdState = {
      ...defaultState(),
      guestHouseholds: [makeHousehold({ role: "advisor" })],
    };
    const result = setActiveHousehold(state, "org-1");
    expect(result.guestRole).toBe("advisor");
  });

  it("defaults to viewer when household not in list", () => {
    const state = defaultState();
    const result = setActiveHousehold(state, "unknown-org");
    expect(result.isGuest).toBe(true);
    expect(result.guestRole).toBe("viewer");
    expect(result.activeHouseholdName).toBeNull();
  });

  it("explicit name overrides the fetched name", () => {
    const state: HouseholdState = {
      ...defaultState(),
      guestHouseholds: [makeHousehold()],
    };
    const result = setActiveHousehold(state, "org-1", "Custom Name");
    expect(result.activeHouseholdName).toBe("Custom Name");
  });
});

describe("revoked household auto-reset", () => {
  it("resets to home when active household is no longer in fetched list", () => {
    const state: HouseholdState = {
      ...defaultState(),
      activeHouseholdId: "org-revoked",
      isGuest: true,
      guestRole: "viewer",
      guestHouseholds: [makeHousehold({ organization_id: "org-revoked" })],
    };
    // Fetch returns no households (access was revoked)
    const result = checkActiveStillValid(state, []);
    expect(result.activeHouseholdId).toBeNull();
    expect(result.isGuest).toBe(false);
  });

  it("keeps active household when it is still in fetched list", () => {
    const household = makeHousehold({ organization_id: "org-1" });
    const state: HouseholdState = {
      ...defaultState(),
      activeHouseholdId: "org-1",
      isGuest: true,
      guestRole: "viewer",
      guestHouseholds: [household],
    };
    const result = checkActiveStillValid(state, [household]);
    expect(result.activeHouseholdId).toBe("org-1");
    expect(result.isGuest).toBe(true);
  });

  it("no-op when no active household", () => {
    const state = defaultState();
    const result = checkActiveStillValid(state, []);
    expect(result.activeHouseholdId).toBeNull();
  });
});
