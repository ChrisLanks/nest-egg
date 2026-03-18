/**
 * Member Filter Context
 *
 * Extracted from UserViewContext to reduce re-renders.
 * Components that only need member filter state can use `useMemberFilter()`
 * instead of the full `useUserView()` — preventing re-renders when
 * permissions or view selection change.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  useCallback,
  type ReactNode,
} from "react";
import type { HouseholdMember } from "../hooks/useHouseholdMembers";

export interface MemberFilterContextType {
  /** Household members (empty until registered by Layout inside ProtectedRoute) */
  householdMembers: HouseholdMember[];
  /** Register household members — called by Layout after fetching */
  _registerHouseholdMembers: (members: HouseholdMember[]) => void;
  /** Set of currently selected member IDs */
  selectedMemberIds: Set<string>;
  /** Update the selected member IDs set directly */
  setSelectedMemberIds: (ids: Set<string>) => void;
  /** Toggle a single member on/off (won't deselect the last one) */
  toggleMember: (memberId: string) => void;
  /** Select all members (= combined) */
  selectAll: () => void;
  /** Whether every member is currently selected */
  isAllSelected: boolean;
  /** Whether the multi-select filter should be visible (combined view, 2+ members) */
  showMemberFilter: boolean;
  /**
   * Effective user_id for API calls in combined view with member filter:
   * - undefined when all selected or partial multi (caller fetches combined)
   * - string when exactly one member is selected
   */
  memberEffectiveUserId: string | undefined;
  /** True when a subset (not all) of members is selected — caller should filter client-side */
  isPartialMemberSelection: boolean;
  /** Convenience: test whether an item belongs to a selected member */
  matchesMemberFilter: (itemUserId: string | null | undefined) => boolean;
  /** Sorted array of selected IDs (stable reference for query keys) */
  selectedMemberIdsKey: string;
}

const MemberFilterContext = createContext<MemberFilterContextType | undefined>(
  undefined,
);

const MEMBER_SELECTION_KEY = "nest-egg-member-selection";

const readStoredMemberSelection = (): string[] | null => {
  try {
    const stored = localStorage.getItem(MEMBER_SELECTION_KEY);
    if (!stored) return null;
    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
};

const saveStoredMemberSelection = (ids: Set<string>): void => {
  try {
    localStorage.setItem(MEMBER_SELECTION_KEY, JSON.stringify([...ids]));
  } catch {
    /* ignore */
  }
};

export const MemberFilterProvider = ({
  isCombinedView,
  onSelectionChange,
  children,
}: {
  isCombinedView: boolean;
  onSelectionChange: (
    memberIds: Set<string>,
    allMemberIds: Set<string>,
  ) => void;
  children: ReactNode;
}) => {
  const [householdMembers, setHouseholdMembers] = useState<HouseholdMember[]>(
    [],
  );
  const [selectedMemberIds, setSelectedMemberIdsRaw] = useState<Set<string>>(
    new Set(),
  );

  // Wrap setter to also persist to localStorage
  const setSelectedMemberIds = useCallback((ids: Set<string>) => {
    setSelectedMemberIdsRaw(ids);
    saveStoredMemberSelection(ids);
  }, []);

  const _registerHouseholdMembers = useCallback(
    (members: HouseholdMember[]) => {
      setHouseholdMembers(members);
    },
    [],
  );

  // Restore selection from localStorage or default to "all" when members list changes
  useEffect(() => {
    if (householdMembers.length > 0) {
      const memberIdSet = new Set(householdMembers.map((m) => m.id));
      const stored = readStoredMemberSelection();
      if (stored && stored.length > 0) {
        // Only keep IDs that are still valid members
        const validIds = stored.filter((id) => memberIdSet.has(id));
        if (validIds.length > 0) {
          // eslint-disable-next-line react-hooks/set-state-in-effect
          setSelectedMemberIdsRaw(new Set(validIds));
          return;
        }
      }
      // Default to all members
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedMemberIdsRaw(new Set(memberIdSet));
    }
  }, [householdMembers]);

  const allMemberIds = useMemo(
    () => new Set(householdMembers.map((m) => m.id)),
    [householdMembers],
  );

  const isAllSelected =
    selectedMemberIds.size === allMemberIds.size &&
    allMemberIds.size > 0 &&
    [...allMemberIds].every((id) => selectedMemberIds.has(id));

  // Notify parent (UserViewProvider) when selection changes
  useEffect(() => {
    if (householdMembers.length > 0) {
      onSelectionChange(selectedMemberIds, allMemberIds);
    }
  }, [
    selectedMemberIds,
    allMemberIds,
    householdMembers.length,
    onSelectionChange,
  ]);

  const toggleMember = useCallback((memberId: string) => {
    setSelectedMemberIdsRaw((prev) => {
      const next = new Set(prev);
      if (next.has(memberId)) {
        if (next.size <= 1) return prev;
        next.delete(memberId);
      } else {
        next.add(memberId);
      }
      saveStoredMemberSelection(next);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedMemberIds(new Set(allMemberIds));
  }, [allMemberIds]);

  const showMemberFilter = isCombinedView && householdMembers.length > 1;

  const isPartialMemberSelection = !isAllSelected && selectedMemberIds.size > 0;

  const memberEffectiveUserId = useMemo(() => {
    if (isAllSelected || selectedMemberIds.size === 0) return undefined;
    if (selectedMemberIds.size === 1) return [...selectedMemberIds][0];
    return undefined;
  }, [isAllSelected, selectedMemberIds]);

  const matchesMemberFilter = useCallback(
    (itemUserId: string | null | undefined): boolean => {
      if (isAllSelected) return true;
      if (!itemUserId) return true;
      return selectedMemberIds.has(itemUserId);
    },
    [isAllSelected, selectedMemberIds],
  );

  const selectedMemberIdsKey = useMemo(
    () => [...selectedMemberIds].sort().join(","),
    [selectedMemberIds],
  );

  const contextValue = useMemo(
    () => ({
      householdMembers,
      _registerHouseholdMembers,
      selectedMemberIds,
      setSelectedMemberIds,
      toggleMember,
      selectAll,
      isAllSelected,
      showMemberFilter,
      memberEffectiveUserId,
      isPartialMemberSelection,
      matchesMemberFilter,
      selectedMemberIdsKey,
    }),
    [
      householdMembers,
      _registerHouseholdMembers,
      selectedMemberIds,
      toggleMember,
      selectAll,
      isAllSelected,
      showMemberFilter,
      memberEffectiveUserId,
      isPartialMemberSelection,
      matchesMemberFilter,
      selectedMemberIdsKey,
    ],
  );

  return (
    <MemberFilterContext.Provider value={contextValue}>
      {children}
    </MemberFilterContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useMemberFilter = (): MemberFilterContextType => {
  const context = useContext(MemberFilterContext);
  if (!context) {
    throw new Error("useMemberFilter must be used within MemberFilterProvider");
  }
  return context;
};
