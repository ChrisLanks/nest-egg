/**
 * User View Context
 *
 * Global state management for multi-user household view selection.
 * Allows switching between "Combined", "Self", and other household members.
 *
 * The member filter state has been extracted into MemberFilterContext to
 * reduce unnecessary re-renders. Components that only need filter state
 * can import `useMemberFilter()` directly.
 *
 * Persistence strategy:
 *   - URL param (?user=<id>) is source of truth when present
 *   - localStorage ('nest-egg-view') provides cross-navigation persistence
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
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "../features/auth/stores/authStore";
import {
  permissionsApi,
  type PermissionGrant,
} from "../features/permissions/api/permissionsApi";
import { MemberFilterProvider, useMemberFilter } from "./MemberFilterContext";
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
  canWriteResource: (resourceType: string) => boolean;
  canWriteOwnedResource: (resourceType: string, ownerId: string) => boolean;
  /** @deprecated Use canWriteResource(resourceType) for accurate per-page checks. */
  canEdit: boolean;
  /** Active grants received from other household members */
  receivedGrants: PermissionGrant[];
  /** True while the receivedGrants query is in its initial load */
  isLoadingGrants: boolean;
}

/** Combined type that merges view + permissions with member filter (backwards compat) */
type FullUserViewContextType = UserViewContextType & {
  householdMembers: HouseholdMember[];
  _registerHouseholdMembers: (members: HouseholdMember[]) => void;
  selectedMemberIds: Set<string>;
  setSelectedMemberIds: (ids: Set<string>) => void;
  toggleMember: (memberId: string) => void;
  selectAll: () => void;
  isAllSelected: boolean;
  showMemberFilter: boolean;
  memberEffectiveUserId: string | undefined;
  isPartialMemberSelection: boolean;
  matchesMemberFilter: (itemUserId: string | null | undefined) => boolean;
  selectedMemberIdsKey: string;
};

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

/** Inner component that provides view + permissions context */
const UserViewInner = ({ children }: { children: ReactNode }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, accessToken } = useAuthStore();

  const [selectedUserId, setSelectedUserIdState] = useState<string | null>(
    () => {
      const urlParam = searchParams.get("user");
      if (urlParam !== null) return urlParam;
      return readStoredView();
    },
  );

  useEffect(() => {
    const urlUserId = searchParams.get("user");
    if (urlUserId !== null) {
      setSelectedUserIdState(urlUserId);
      saveStoredView(urlUserId);
    }
  }, [searchParams]);

  const setSelectedUserId = useCallback(
    (userId: string | null) => {
      setSelectedUserIdState(userId);
      saveStoredView(userId);

      // Read live URL to avoid stale closures (this callback can be captured
      // by other callbacks like handleSelectionChange that don't re-create
      // when the pathname changes).
      const newParams = new URLSearchParams(window.location.search);
      if (userId) {
        newParams.set("user", userId);
      } else {
        newParams.delete("user");
      }
      const search = newParams.toString();
      navigate(
        {
          pathname: window.location.pathname,
          search: search ? `?${search}` : "",
        },
        { replace: true },
      );
    },
    [navigate],
  );

  useEffect(() => {
    if (selectedUserId && !searchParams.get("user")) {
      const newParams = new URLSearchParams(window.location.search);
      newParams.set("user", selectedUserId);
      const search = newParams.toString();
      navigate(
        {
          pathname: window.location.pathname,
          search: search ? `?${search}` : "",
        },
        { replace: true },
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isSelfView = selectedUserId === user?.id;
  const isCombinedView = selectedUserId === null;
  const isOtherUserView =
    selectedUserId !== null && selectedUserId !== user?.id;

  const { data: receivedGrants = [], isLoading: isLoadingGrants } = useQuery({
    queryKey: ["permissions", "received"],
    queryFn: permissionsApi.listReceived,
    enabled: !isSelfView && !!user && !!accessToken,
    staleTime: 5 * 60 * 1000,
  });

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

  // Handle member filter selection changes to keep selectedUserId in sync
  const handleSelectionChange = useCallback(
    (memberIds: Set<string>, allMemberIds: Set<string>) => {
      const isAll =
        memberIds.size === allMemberIds.size &&
        allMemberIds.size > 0 &&
        [...allMemberIds].every((id) => memberIds.has(id));

      if (isAll) {
        if (selectedUserId !== null) setSelectedUserId(null);
      } else if (memberIds.size === 1) {
        const singleId = [...memberIds][0];
        if (selectedUserId !== singleId) setSelectedUserId(singleId);
      } else {
        if (selectedUserId !== null) setSelectedUserId(null);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedUserId],
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
    ],
  );

  return (
    <UserViewContext.Provider value={contextValue}>
      <MemberFilterProvider
        isCombinedView={isCombinedView}
        onSelectionChange={handleSelectionChange}
      >
        {children}
      </MemberFilterProvider>
    </UserViewContext.Provider>
  );
};

export const UserViewProvider = ({ children }: { children: ReactNode }) => {
  return <UserViewInner>{children}</UserViewInner>;
};

/**
 * Hook for view selection and permissions only.
 * Use this when you don't need member filter state.
 */
// eslint-disable-next-line react-refresh/only-export-components
export const useUserViewCore = (): UserViewContextType => {
  const context = useContext(UserViewContext);
  if (!context) {
    throw new Error("useUserViewCore must be used within UserViewProvider");
  }
  return context;
};

/**
 * Backwards-compatible hook that returns both view + member filter state.
 * Prefer useUserViewCore() or useMemberFilter() for better performance.
 */
// eslint-disable-next-line react-refresh/only-export-components
export const useUserView = (): FullUserViewContextType => {
  const viewContext = useContext(UserViewContext);
  if (!viewContext) {
    throw new Error("useUserView must be used within UserViewProvider");
  }
  const memberFilter = useMemberFilter();
  return { ...viewContext, ...memberFilter };
};
