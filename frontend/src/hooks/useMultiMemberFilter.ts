/**
 * Multi-select household member filter hook.
 *
 * Reads from the global MemberFilterContext so the selection persists
 * across tab / page navigation.
 *
 * In combined/household view, allows toggling individual members on or off.
 * All members start selected (= combined view). At least one member must
 * remain selected at all times.
 *
 * For pages that call APIs accepting a single `user_id`:
 *   - All selected   → effectiveUserId = undefined  (combined API call)
 *   - One selected    → effectiveUserId = that ID    (single user API call)
 *   - Partial (2+)    → effectiveUserId = undefined  (combined, filtered client-side)
 *
 * `matchesFilter` is provided for client-side filtering of items that have
 * a `user_id` field.
 */

import { useCallback, useMemo } from "react";
import { useUserView } from "../contexts/UserViewContext";
import { useMemberFilterContext } from "../contexts/MemberFilterContext";
import type { HouseholdMember } from "./useHouseholdMembers";

export interface MultiMemberFilter {
  /** Set of currently selected member IDs */
  selectedIds: Set<string>;
  /** Toggle a single member on/off (won't deselect the last one) */
  toggleMember: (memberId: string) => void;
  /** Select all members (= combined) */
  selectAll: () => void;
  /** Whether every member is currently selected */
  isAllSelected: boolean;
  /** Whether the multi-select bar should be visible */
  showFilter: boolean;
  /** Household members list */
  members: HouseholdMember[];
  /**
   * Effective user_id for API calls:
   * - undefined when all selected or partial multi (caller fetches combined)
   * - string when exactly one member is selected
   */
  effectiveUserId: string | undefined;
  /** True when a subset (not all) of members is selected — caller should filter client-side */
  isPartialSelection: boolean;
  /** Convenience: test whether an item belongs to a selected member */
  matchesFilter: (itemUserId: string | null | undefined) => boolean;
  /** Sorted array of selected IDs (stable reference for query keys) */
  selectedIdsKey: string;
}

export function useMultiMemberFilter(): MultiMemberFilter {
  const { isCombinedView } = useUserView();
  const { selectedIds, setSelectedIds, members } = useMemberFilterContext();

  const allIds = useMemo(() => new Set(members.map((m) => m.id)), [members]);

  const isAllSelected =
    selectedIds.size === allIds.size &&
    allIds.size > 0 &&
    [...allIds].every((id) => selectedIds.has(id));

  const toggleMember = useCallback(
    (memberId: string) => {
      setSelectedIds(
        (() => {
          const next = new Set(selectedIds);
          if (next.has(memberId)) {
            // Don't deselect the last member
            if (next.size <= 1) return selectedIds;
            next.delete(memberId);
          } else {
            next.add(memberId);
          }
          return next;
        })(),
      );
    },
    [selectedIds, setSelectedIds],
  );

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(allIds));
  }, [allIds, setSelectedIds]);

  const showFilter = isCombinedView && members.length > 1;

  const isPartialSelection = !isAllSelected && selectedIds.size > 0;

  // For API calls: undefined = fetch combined, string = fetch single user
  const effectiveUserId = useMemo(() => {
    if (isAllSelected || selectedIds.size === 0) return undefined;
    if (selectedIds.size === 1) return [...selectedIds][0];
    // Partial multi-select: fetch combined, filter client-side
    return undefined;
  }, [isAllSelected, selectedIds]);

  const matchesFilter = useCallback(
    (itemUserId: string | null | undefined): boolean => {
      if (isAllSelected) return true;
      if (!itemUserId) return true; // legacy items without user_id always pass
      return selectedIds.has(itemUserId);
    },
    [isAllSelected, selectedIds],
  );

  // Stable string key for React Query cache differentiation
  const selectedIdsKey = useMemo(
    () => [...selectedIds].sort().join(","),
    [selectedIds],
  );

  return {
    selectedIds,
    toggleMember,
    selectAll,
    isAllSelected,
    showFilter,
    members,
    effectiveUserId,
    isPartialSelection,
    matchesFilter,
    selectedIdsKey,
  };
}
