/**
 * Unit tests for the multi-member filter logic used in useMultiMemberFilter.
 *
 * The pure functions are extracted here for isolated testing. They mirror the
 * derivation logic in useMultiMemberFilter.ts:
 *
 *   - isAllSelected: all members are in the selected set
 *   - effectiveUserId: undefined for combined/partial, string for single
 *   - isPartialSelection: subset of members selected
 *   - matchesFilter: does an item's user_id pass the filter?
 *   - toggleMember: add/remove a member, never deselect the last one
 *   - selectAll: reset to all members
 *   - showFilter: only in combined view with 2+ members
 *   - selectedIdsKey: stable cache key string
 */

import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// Pure functions mirroring useMultiMemberFilter logic
// ---------------------------------------------------------------------------

function computeIsAllSelected(
  selectedIds: Set<string>,
  allIds: Set<string>,
): boolean {
  return (
    selectedIds.size === allIds.size &&
    allIds.size > 0 &&
    [...allIds].every((id) => selectedIds.has(id))
  );
}

function computeEffectiveUserId(
  selectedIds: Set<string>,
  isAllSelected: boolean,
): string | undefined {
  if (isAllSelected || selectedIds.size === 0) return undefined;
  if (selectedIds.size === 1) return [...selectedIds][0];
  return undefined; // partial multi → combined
}

function computeIsPartialSelection(
  isAllSelected: boolean,
  selectedIds: Set<string>,
): boolean {
  return !isAllSelected && selectedIds.size > 0;
}

function computeMatchesFilter(
  itemUserId: string | null | undefined,
  selectedIds: Set<string>,
  isAllSelected: boolean,
): boolean {
  if (isAllSelected) return true;
  if (!itemUserId) return true; // legacy items without user_id always pass
  return selectedIds.has(itemUserId);
}

function computeToggleMember(
  selectedIds: Set<string>,
  memberId: string,
): Set<string> {
  const next = new Set(selectedIds);
  if (next.has(memberId)) {
    if (next.size <= 1) return selectedIds; // don't deselect last
    next.delete(memberId);
  } else {
    next.add(memberId);
  }
  return next;
}

function computeSelectAll(allIds: Set<string>): Set<string> {
  return new Set(allIds);
}

function computeShowFilter(
  isCombinedView: boolean,
  memberCount: number,
): boolean {
  return isCombinedView && memberCount > 1;
}

function computeSelectedIdsKey(selectedIds: Set<string>): string {
  return [...selectedIds].sort().join(",");
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

const USER_A = "user-aaa";
const USER_B = "user-bbb";
const USER_C = "user-ccc";

const ALL_IDS = new Set([USER_A, USER_B, USER_C]);

function setOf(...ids: string[]): Set<string> {
  return new Set(ids);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("multiMemberFilter — isAllSelected", () => {
  it("returns true when all members are selected", () => {
    expect(computeIsAllSelected(setOf(USER_A, USER_B, USER_C), ALL_IDS)).toBe(
      true,
    );
  });

  it("returns false when subset is selected", () => {
    expect(computeIsAllSelected(setOf(USER_A, USER_B), ALL_IDS)).toBe(false);
  });

  it("returns false when one member is selected", () => {
    expect(computeIsAllSelected(setOf(USER_A), ALL_IDS)).toBe(false);
  });

  it("returns false when no members are selected", () => {
    expect(computeIsAllSelected(new Set(), ALL_IDS)).toBe(false);
  });

  it("returns false when allIds is empty", () => {
    expect(computeIsAllSelected(new Set(), new Set())).toBe(false);
  });

  it("returns true for single-member household with that member selected", () => {
    expect(computeIsAllSelected(setOf(USER_A), setOf(USER_A))).toBe(true);
  });

  it("returns false when selectedIds has extra IDs not in allIds (size mismatch)", () => {
    // selectedIds is a superset — size check fails so isAllSelected is false
    expect(
      computeIsAllSelected(setOf(USER_A, USER_B, USER_C, "extra"), ALL_IDS),
    ).toBe(false);
  });
});

describe("multiMemberFilter — effectiveUserId", () => {
  it("returns undefined when all selected", () => {
    expect(
      computeEffectiveUserId(setOf(USER_A, USER_B, USER_C), true),
    ).toBeUndefined();
  });

  it("returns undefined when no members selected", () => {
    expect(computeEffectiveUserId(new Set(), false)).toBeUndefined();
  });

  it("returns the single ID when exactly one selected", () => {
    expect(computeEffectiveUserId(setOf(USER_B), false)).toBe(USER_B);
  });

  it("returns undefined for partial multi-select (2 of 3)", () => {
    expect(
      computeEffectiveUserId(setOf(USER_A, USER_C), false),
    ).toBeUndefined();
  });

  it("returns undefined when isAllSelected is true even with one member", () => {
    // single-member household where that one is "all"
    expect(computeEffectiveUserId(setOf(USER_A), true)).toBeUndefined();
  });
});

describe("multiMemberFilter — isPartialSelection", () => {
  it("returns false when all selected", () => {
    expect(computeIsPartialSelection(true, setOf(USER_A, USER_B, USER_C))).toBe(
      false,
    );
  });

  it("returns false when none selected", () => {
    expect(computeIsPartialSelection(false, new Set())).toBe(false);
  });

  it("returns true when subset selected", () => {
    expect(computeIsPartialSelection(false, setOf(USER_A))).toBe(true);
  });

  it("returns true when 2 of 3 selected", () => {
    expect(computeIsPartialSelection(false, setOf(USER_A, USER_B))).toBe(true);
  });
});

describe("multiMemberFilter — matchesFilter", () => {
  it("passes everything when all selected", () => {
    expect(computeMatchesFilter(USER_A, setOf(USER_A, USER_B), true)).toBe(
      true,
    );
    expect(computeMatchesFilter("unknown", setOf(USER_A), true)).toBe(true);
  });

  it("passes items with null/undefined user_id (legacy items)", () => {
    expect(computeMatchesFilter(null, setOf(USER_A), false)).toBe(true);
    expect(computeMatchesFilter(undefined, setOf(USER_A), false)).toBe(true);
  });

  it("passes items belonging to a selected member", () => {
    expect(computeMatchesFilter(USER_A, setOf(USER_A, USER_B), false)).toBe(
      true,
    );
  });

  it("rejects items belonging to a deselected member", () => {
    expect(computeMatchesFilter(USER_C, setOf(USER_A, USER_B), false)).toBe(
      false,
    );
  });

  it("works with single selected member", () => {
    expect(computeMatchesFilter(USER_B, setOf(USER_B), false)).toBe(true);
    expect(computeMatchesFilter(USER_A, setOf(USER_B), false)).toBe(false);
  });
});

describe("multiMemberFilter — toggleMember", () => {
  it("adds a member that is not selected", () => {
    const result = computeToggleMember(setOf(USER_A), USER_B);
    expect(result.has(USER_A)).toBe(true);
    expect(result.has(USER_B)).toBe(true);
    expect(result.size).toBe(2);
  });

  it("removes a member that is selected (when others remain)", () => {
    const result = computeToggleMember(setOf(USER_A, USER_B), USER_A);
    expect(result.has(USER_A)).toBe(false);
    expect(result.has(USER_B)).toBe(true);
    expect(result.size).toBe(1);
  });

  it("prevents deselecting the last member", () => {
    const original = setOf(USER_A);
    const result = computeToggleMember(original, USER_A);
    // Should return the original set unchanged
    expect(result).toBe(original);
    expect(result.size).toBe(1);
    expect(result.has(USER_A)).toBe(true);
  });

  it("prevents deselecting the last member (reference equality)", () => {
    const original = setOf(USER_B);
    const result = computeToggleMember(original, USER_B);
    expect(result).toBe(original); // exact same object = no state update
  });

  it("can toggle the same member on and off", () => {
    const step1 = computeToggleMember(setOf(USER_A, USER_B), USER_B);
    expect(step1.has(USER_B)).toBe(false);
    const step2 = computeToggleMember(step1, USER_B);
    expect(step2.has(USER_B)).toBe(true);
  });

  it("handles toggling all three members off one by one (last remains)", () => {
    let ids = setOf(USER_A, USER_B, USER_C);
    ids = computeToggleMember(ids, USER_A);
    expect(ids.size).toBe(2);
    ids = computeToggleMember(ids, USER_B);
    expect(ids.size).toBe(1);
    expect(ids.has(USER_C)).toBe(true);
    // Trying to remove the last one does nothing
    const final = computeToggleMember(ids, USER_C);
    expect(final.size).toBe(1);
    expect(final).toBe(ids);
  });
});

describe("multiMemberFilter — selectAll", () => {
  it("returns a new set containing all IDs", () => {
    const result = computeSelectAll(ALL_IDS);
    expect(result.size).toBe(3);
    expect(result.has(USER_A)).toBe(true);
    expect(result.has(USER_B)).toBe(true);
    expect(result.has(USER_C)).toBe(true);
  });

  it("returns a new set (not the same reference)", () => {
    const result = computeSelectAll(ALL_IDS);
    expect(result).not.toBe(ALL_IDS);
  });

  it("works with empty allIds", () => {
    const result = computeSelectAll(new Set());
    expect(result.size).toBe(0);
  });

  it("works with single member", () => {
    const result = computeSelectAll(setOf(USER_A));
    expect(result.size).toBe(1);
    expect(result.has(USER_A)).toBe(true);
  });
});

describe("multiMemberFilter — showFilter", () => {
  it("returns true in combined view with 2+ members", () => {
    expect(computeShowFilter(true, 2)).toBe(true);
    expect(computeShowFilter(true, 3)).toBe(true);
    expect(computeShowFilter(true, 10)).toBe(true);
  });

  it("returns false in combined view with 0 or 1 member", () => {
    expect(computeShowFilter(true, 0)).toBe(false);
    expect(computeShowFilter(true, 1)).toBe(false);
  });

  it("returns false when not in combined view", () => {
    expect(computeShowFilter(false, 3)).toBe(false);
    expect(computeShowFilter(false, 2)).toBe(false);
    expect(computeShowFilter(false, 0)).toBe(false);
  });
});

describe("multiMemberFilter — selectedIdsKey", () => {
  it("produces a stable sorted comma-joined key", () => {
    expect(computeSelectedIdsKey(setOf(USER_C, USER_A, USER_B))).toBe(
      [USER_A, USER_B, USER_C].sort().join(","),
    );
  });

  it("is deterministic regardless of insertion order", () => {
    const key1 = computeSelectedIdsKey(setOf(USER_B, USER_A));
    const key2 = computeSelectedIdsKey(setOf(USER_A, USER_B));
    expect(key1).toBe(key2);
  });

  it("returns empty string for empty set", () => {
    expect(computeSelectedIdsKey(new Set())).toBe("");
  });

  it("returns single ID for single selection", () => {
    expect(computeSelectedIdsKey(setOf(USER_A))).toBe(USER_A);
  });
});

describe("multiMemberFilter — retirement per-person derivation", () => {
  // Retirement pages need exactly one member selected to show scenarios.
  // This mirrors the logic: singleSelectedId = selectedIds.size === 1 ? first : null

  function computeSingleSelectedId(selectedIds: Set<string>): string | null {
    return selectedIds.size === 1 ? [...selectedIds][0] : null;
  }

  it("returns the ID when exactly one member selected", () => {
    expect(computeSingleSelectedId(setOf(USER_B))).toBe(USER_B);
  });

  it("returns null when all members selected", () => {
    expect(computeSingleSelectedId(setOf(USER_A, USER_B, USER_C))).toBeNull();
  });

  it("returns null when two members selected", () => {
    expect(computeSingleSelectedId(setOf(USER_A, USER_C))).toBeNull();
  });

  it("returns null when empty", () => {
    expect(computeSingleSelectedId(new Set())).toBeNull();
  });
});

describe("multiMemberFilter — integration scenarios", () => {
  it("full workflow: start all → deselect two → single user API call", () => {
    let ids = setOf(USER_A, USER_B, USER_C);
    let isAll = computeIsAllSelected(ids, ALL_IDS);
    expect(isAll).toBe(true);
    expect(computeEffectiveUserId(ids, isAll)).toBeUndefined();

    // Deselect B
    ids = computeToggleMember(ids, USER_B);
    isAll = computeIsAllSelected(ids, ALL_IDS);
    expect(isAll).toBe(false);
    expect(computeIsPartialSelection(isAll, ids)).toBe(true);
    expect(computeEffectiveUserId(ids, isAll)).toBeUndefined(); // still 2 selected

    // Deselect C → only A remains
    ids = computeToggleMember(ids, USER_C);
    isAll = computeIsAllSelected(ids, ALL_IDS);
    expect(computeEffectiveUserId(ids, isAll)).toBe(USER_A);
  });

  it("full workflow: single → selectAll → combined", () => {
    let ids = setOf(USER_B);
    let isAll = computeIsAllSelected(ids, ALL_IDS);
    expect(computeEffectiveUserId(ids, isAll)).toBe(USER_B);

    ids = computeSelectAll(ALL_IDS);
    isAll = computeIsAllSelected(ids, ALL_IDS);
    expect(computeEffectiveUserId(ids, isAll)).toBeUndefined();
    expect(isAll).toBe(true);
  });

  it("matchesFilter reflects toggle changes correctly", () => {
    let ids = setOf(USER_A, USER_B, USER_C);
    let isAll = computeIsAllSelected(ids, ALL_IDS);

    // All selected: everything passes
    expect(computeMatchesFilter(USER_A, ids, isAll)).toBe(true);
    expect(computeMatchesFilter(USER_C, ids, isAll)).toBe(true);

    // Deselect C
    ids = computeToggleMember(ids, USER_C);
    isAll = computeIsAllSelected(ids, ALL_IDS);
    expect(computeMatchesFilter(USER_A, ids, isAll)).toBe(true);
    expect(computeMatchesFilter(USER_C, ids, isAll)).toBe(false);
  });

  it("selectedIdsKey changes when selection changes", () => {
    const key1 = computeSelectedIdsKey(setOf(USER_A, USER_B, USER_C));
    const ids2 = computeToggleMember(setOf(USER_A, USER_B, USER_C), USER_B);
    const key2 = computeSelectedIdsKey(ids2);
    expect(key1).not.toBe(key2);
  });

  it("two-member household: toggle keeps at least one", () => {
    const twoIds = setOf(USER_A, USER_B);

    const ids = computeToggleMember(twoIds, USER_A);
    expect(ids.size).toBe(1);
    expect(ids.has(USER_B)).toBe(true);

    // Can't remove last
    const final = computeToggleMember(ids, USER_B);
    expect(final).toBe(ids);
    expect(final.size).toBe(1);
  });
});
