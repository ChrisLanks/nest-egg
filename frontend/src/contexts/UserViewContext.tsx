/**
 * User View Context
 *
 * Global state management for multi-user household view selection.
 * Allows switching between "Combined", "Self", and other household members.
 * Also holds the multi-member filter state (selectedMemberIds) so that
 * checkbox-based member filtering in the header persists across pages.
 *
 * Persistence strategy:
 *   - URL param (?user=<id>) is source of truth when present
 *   - localStorage ('nest-egg-view') provides cross-navigation persistence
 *
 * Member filter state:
 *   - householdMembers is registered by Layout (inside ProtectedRoute) so the
 *     authenticated API call never fires on public routes.
 *   - selectedMemberIds tracks which members' data is visible.
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
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "../features/auth/stores/authStore";
import {
  permissionsApi,
  type PermissionGrant,
} from "../features/permissions/api/permissionsApi";
import type { HouseholdMember } from "../hooks/useHouseholdMembers";

interface UserViewContextType {
  /** Currently selected user ID (null = combined view) */
  selectedUserId: string | null;
  /** Change the selected user view */
  setSelectedUserId: (userId: string | null) => void;
  /** Check if viewing as current user */
  isSelfView: boolean;
  /** Check if viewing combined household */
  isCombinedView: boolean;
  /** Check if viewing another user's data */
  isOtherUserView: boolean;
  /**
   * Check if current user can edit a specific resource type in this view.
   * True for own data / combined view, or when the other user has granted write access
   * to this exact resource type.
   */
  canWriteResource: (resourceType: string) => boolean;
  /**
   * Check if the current user can write a resource of the given type owned by ownerId.
   * Use for per-resource checks (e.g., "can I edit this specific account?").
   * Returns true if: ownerId is the current user, user is org admin, or an active
   * write grant from ownerId exists for this resourceType.
   */
  canWriteOwnedResource: (resourceType: string, ownerId: string) => boolean;
  /**
   * Check if current user can edit in this view (any resource type).
   * Prefer canWriteResource(type) for page-level guards.
   * @deprecated Use canWriteResource(resourceType) for accurate per-page checks.
   */
  canEdit: boolean;
  /** Active grants received from other household members (available in other-user and combined views) */
  receivedGrants: PermissionGrant[];
  /** True while the receivedGrants query is in its initial load */
  isLoadingGrants: boolean;

  // ── Multi-member filter state ────────────────────────────────────────────

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

const UserViewContext = createContext<UserViewContextType | undefined>(
  undefined,
);

const VIEW_STORAGE_KEY = "nest-egg-view";

const readStoredView = (): string | null => {
  try {
    const stored = localStorage.getItem(VIEW_STORAGE_KEY);
    if (!stored || stored === "combined") return null;
    return stored;
  } catch {
    return null;
  }
};

const saveStoredView = (userId: string | null): void => {
  try {
    localStorage.setItem(VIEW_STORAGE_KEY, userId ?? "combined");
  } catch {
    /* ignore */
  }
};

export const UserViewProvider = ({ children }: { children: ReactNode }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, accessToken } = useAuthStore();

  // Init: URL param takes priority, then localStorage, then null (combined)
  const [selectedUserId, setSelectedUserIdState] = useState<string | null>(
    () => {
      const urlParam = searchParams.get("user");
      if (urlParam !== null) return urlParam;
      return readStoredView();
    },
  );

  // Sync FROM URL when it changes (browser back/forward or explicit ?user= link).
  // When URL has no param we keep the current state — don't reset to combined.
  // This way navigating to pages that strip query params doesn't lose the selection.
  useEffect(() => {
    const urlUserId = searchParams.get("user");
    if (urlUserId !== null) {
      // URL explicitly specifies a user — honour it and persist it
      setSelectedUserIdState(urlUserId);
      saveStoredView(urlUserId);
    }
    // No URL param → keep current state (restored from localStorage or last explicit change)
  }, [searchParams]);

  // When the view changes, update URL and localStorage together
  const setSelectedUserId = useCallback(
    (userId: string | null) => {
      setSelectedUserIdState(userId);
      saveStoredView(userId);

      const newParams = new URLSearchParams(searchParams);
      if (userId) {
        newParams.set("user", userId);
      } else {
        newParams.delete("user");
      }
      setSearchParams(newParams, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  // If we restored from localStorage but the URL has no param, push it into the URL
  // so that navigateWithParams in Layout picks it up correctly.
  useEffect(() => {
    if (selectedUserId && !searchParams.get("user")) {
      const newParams = new URLSearchParams(searchParams);
      newParams.set("user", selectedUserId);
      setSearchParams(newParams, { replace: true });
    }
    // Only run once on mount — not on every searchParams change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isSelfView = selectedUserId === user?.id;
  const isCombinedView = selectedUserId === null;
  const isOtherUserView =
    selectedUserId !== null && selectedUserId !== user?.id;

  // Fetch received permission grants when viewing another user's data or combined
  // household (where we need grants to determine per-resource edit permissions).
  // Guard with !!accessToken so the query never fires before ProtectedRoute
  // restores the session — prevents a race condition where two concurrent
  // /auth/refresh calls rotate the cookie and invalidate each other.
  const { data: receivedGrants = [], isLoading: isLoadingGrants } = useQuery({
    queryKey: ["permissions", "received"],
    queryFn: permissionsApi.listReceived,
    enabled: !isSelfView && !!user && !!accessToken,
    staleTime: 5 * 60 * 1000,
  });

  // canWriteResource: own data / combined view, OR the data owner has granted write
  // access specifically for this resource type.
  const canWriteResource = useCallback(
    (resourceType: string): boolean => {
      if (isSelfView || isCombinedView) return true;
      if (!isOtherUserView) return false;
      const now = new Date();
      return receivedGrants.some(
        (g) =>
          g.grantor_id === selectedUserId &&
          g.resource_type === resourceType &&
          g.is_active &&
          (!g.expires_at || new Date(g.expires_at) > now) &&
          (g.actions.includes("create") ||
            g.actions.includes("update") ||
            g.actions.includes("delete")),
      );
    },
    [
      isSelfView,
      isCombinedView,
      isOtherUserView,
      selectedUserId,
      receivedGrants,
    ],
  );

  // canWriteOwnedResource: per-resource permission check — "can I write to this
  // specific resource owned by ownerId?" Checks ownership and grants.
  const canWriteOwnedResource = useCallback(
    (resourceType: string, ownerId: string): boolean => {
      if (user?.id === ownerId) return true;
      const now = new Date();
      return receivedGrants.some(
        (g) =>
          g.grantor_id === ownerId &&
          g.resource_type === resourceType &&
          g.is_active &&
          (!g.expires_at || new Date(g.expires_at) > now) &&
          (g.actions.includes("create") ||
            g.actions.includes("update") ||
            g.actions.includes("delete")),
      );
    },
    [user, receivedGrants],
  );

  // canEdit: true if write access exists for ANY resource type.
  // Prefer canWriteResource(type) for accurate per-page guards.
  const canEdit =
    isSelfView ||
    isCombinedView ||
    (isOtherUserView &&
      receivedGrants.some(
        (g) =>
          g.grantor_id === selectedUserId &&
          g.is_active &&
          (!g.expires_at || new Date(g.expires_at) > new Date()) &&
          (g.actions.includes("create") ||
            g.actions.includes("update") ||
            g.actions.includes("delete")),
      ));

  // ── Multi-member filter state ──────────────────────────────────────────

  const [householdMembers, setHouseholdMembers] = useState<HouseholdMember[]>(
    [],
  );
  const [selectedMemberIds, setSelectedMemberIds] = useState<Set<string>>(
    new Set(),
  );

  // Register members (called by Layout after useHouseholdMembers resolves)
  const _registerHouseholdMembers = useCallback(
    (members: HouseholdMember[]) => {
      setHouseholdMembers(members);
    },
    [],
  );

  // Reset selection to "all" whenever the members list changes (initial load
  // or household membership change). We intentionally do NOT depend on
  // isCombinedView here — the checkbox system drives selectedUserId, not the
  // other way around, to avoid circular resets.
  useEffect(() => {
    if (householdMembers.length > 0) {
      setSelectedMemberIds(new Set(householdMembers.map((m) => m.id)));
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

  // Sync selectedUserId from selectedMemberIds so that banners, API calls,
  // and URL params reflect the checkbox state.
  //   All selected  → null (combined)
  //   One selected   → that member's ID
  //   Partial (2+)   → null (combined, client-side filter)
  useEffect(() => {
    if (householdMembers.length === 0) return; // members not loaded yet
    if (isAllSelected) {
      if (selectedUserId !== null) setSelectedUserId(null);
    } else if (selectedMemberIds.size === 1) {
      const singleId = [...selectedMemberIds][0];
      if (selectedUserId !== singleId) setSelectedUserId(singleId);
    } else {
      // Partial multi-select → combined view (client-side filtering)
      if (selectedUserId !== null) setSelectedUserId(null);
    }
  }, [selectedMemberIds, isAllSelected, householdMembers.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleMember = useCallback((memberId: string) => {
    setSelectedMemberIds((prev) => {
      const next = new Set(prev);
      if (next.has(memberId)) {
        if (next.size <= 1) return prev; // don't deselect last
        next.delete(memberId);
      } else {
        next.add(memberId);
      }
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
    return undefined; // partial multi → combined, filter client-side
  }, [isAllSelected, selectedMemberIds]);

  const matchesMemberFilter = useCallback(
    (itemUserId: string | null | undefined): boolean => {
      if (isAllSelected) return true;
      if (!itemUserId) return true; // legacy items without user_id always pass
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
      selectedUserId,
      setSelectedUserId,
      isSelfView,
      isCombinedView,
      isOtherUserView,
      canWriteResource,
      canWriteOwnedResource,
      canEdit,
      receivedGrants,
      isLoadingGrants,
      // Multi-member filter
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
      selectedUserId,
      setSelectedUserId,
      isSelfView,
      isCombinedView,
      isOtherUserView,
      canWriteResource,
      canWriteOwnedResource,
      canEdit,
      receivedGrants,
      isLoadingGrants,
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
    <UserViewContext.Provider value={contextValue}>
      {children}
    </UserViewContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useUserView = () => {
  const context = useContext(UserViewContext);
  if (!context) {
    throw new Error("useUserView must be used within UserViewProvider");
  }
  return context;
};
