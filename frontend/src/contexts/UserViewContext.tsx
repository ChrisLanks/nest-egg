/**
 * User View Context
 *
 * Global state management for multi-user household view selection.
 * Allows switching between "Combined", "Self", and other household members.
 *
 * Persistence strategy:
 *   - URL param (?user=<id>) is source of truth when present
 *   - localStorage ('nest-egg-view') provides cross-navigation persistence
 *   - On pages that strip query params, localStorage restores the selection
 */

import { createContext, useContext, useState, useEffect, useMemo, useCallback, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../features/auth/stores/authStore';
import { permissionsApi, type PermissionGrant } from '../features/permissions/api/permissionsApi';

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
   * Check if current user can edit in this view (any resource type).
   * Prefer canWriteResource(type) for page-level guards.
   * @deprecated Use canWriteResource(resourceType) for accurate per-page checks.
   */
  canEdit: boolean;
  /** Active grants received from the currently-viewed user (empty when not isOtherUserView) */
  receivedGrants: PermissionGrant[];
  /** True while the receivedGrants query is in its initial load */
  isLoadingGrants: boolean;
}

const UserViewContext = createContext<UserViewContextType | undefined>(undefined);

const VIEW_STORAGE_KEY = 'nest-egg-view';

const readStoredView = (): string | null => {
  try {
    const stored = localStorage.getItem(VIEW_STORAGE_KEY);
    if (!stored || stored === 'combined') return null;
    return stored;
  } catch {
    return null;
  }
};

const saveStoredView = (userId: string | null): void => {
  try {
    localStorage.setItem(VIEW_STORAGE_KEY, userId ?? 'combined');
  } catch { /* ignore */ }
};

export const UserViewProvider = ({ children }: { children: ReactNode }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, accessToken } = useAuthStore();

  // Init: URL param takes priority, then localStorage, then null (combined)
  const [selectedUserId, setSelectedUserIdState] = useState<string | null>(() => {
    const urlParam = searchParams.get('user');
    if (urlParam !== null) return urlParam;
    return readStoredView();
  });

  // Sync FROM URL when it changes (browser back/forward or explicit ?user= link).
  // When URL has no param we keep the current state — don't reset to combined.
  // This way navigating to pages that strip query params doesn't lose the selection.
  useEffect(() => {
    const urlUserId = searchParams.get('user');
    if (urlUserId !== null) {
      // URL explicitly specifies a user — honour it and persist it
      setSelectedUserIdState(urlUserId);
      saveStoredView(urlUserId);
    }
    // No URL param → keep current state (restored from localStorage or last explicit change)
  }, [searchParams]);

  // When the view changes, update URL and localStorage together
  const setSelectedUserId = useCallback((userId: string | null) => {
    setSelectedUserIdState(userId);
    saveStoredView(userId);

    const newParams = new URLSearchParams(searchParams);
    if (userId) {
      newParams.set('user', userId);
    } else {
      newParams.delete('user');
    }
    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);

  // If we restored from localStorage but the URL has no param, push it into the URL
  // so that navigateWithParams in Layout picks it up correctly.
  useEffect(() => {
    if (selectedUserId && !searchParams.get('user')) {
      const newParams = new URLSearchParams(searchParams);
      newParams.set('user', selectedUserId);
      setSearchParams(newParams, { replace: true });
    }
  // Only run once on mount — not on every searchParams change
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isSelfView = selectedUserId === user?.id;
  const isCombinedView = selectedUserId === null;
  const isOtherUserView = selectedUserId !== null && selectedUserId !== user?.id;

  // Fetch received permission grants when viewing another user's data.
  // Guard with !!accessToken so the query never fires before ProtectedRoute
  // restores the session — prevents a race condition where two concurrent
  // /auth/refresh calls rotate the cookie and invalidate each other.
  const { data: receivedGrants = [], isLoading: isLoadingGrants } = useQuery({
    queryKey: ['permissions', 'received'],
    queryFn: permissionsApi.listReceived,
    enabled: isOtherUserView && !!user && !!accessToken,
    staleTime: 5 * 60 * 1000,
  });

  // canWriteResource: own data / combined view, OR the data owner has granted write
  // access specifically for this resource type.
  const canWriteResource = useCallback((resourceType: string): boolean => {
    if (isSelfView || isCombinedView) return true;
    if (!isOtherUserView) return false;
    const now = new Date();
    return receivedGrants.some((g) =>
      g.grantor_id === selectedUserId &&
      g.resource_type === resourceType &&
      g.is_active &&
      (!g.expires_at || new Date(g.expires_at) > now) &&
      (g.actions.includes('create') || g.actions.includes('update') || g.actions.includes('delete'))
    );
  }, [isSelfView, isCombinedView, isOtherUserView, selectedUserId, receivedGrants]);

  // canEdit: true if write access exists for ANY resource type.
  // Prefer canWriteResource(type) for accurate per-page guards.
  const canEdit = isSelfView || isCombinedView || (
    isOtherUserView && receivedGrants.some((g) =>
      g.grantor_id === selectedUserId &&
      g.is_active &&
      (!g.expires_at || new Date(g.expires_at) > new Date()) &&
      (g.actions.includes('create') || g.actions.includes('update') || g.actions.includes('delete'))
    )
  );

  const contextValue = useMemo(() => ({
    selectedUserId,
    setSelectedUserId,
    isSelfView,
    isCombinedView,
    isOtherUserView,
    canWriteResource,
    canEdit,
    receivedGrants,
    isLoadingGrants,
  }), [selectedUserId, setSelectedUserId, isSelfView, isCombinedView, isOtherUserView, canWriteResource, canEdit, receivedGrants, isLoadingGrants]);

  return (
    <UserViewContext.Provider value={contextValue}>
      {children}
    </UserViewContext.Provider>
  );
};

export const useUserView = () => {
  const context = useContext(UserViewContext);
  if (!context) {
    throw new Error('useUserView must be used within UserViewProvider');
  }
  return context;
};
