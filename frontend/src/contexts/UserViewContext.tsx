/**
 * User View Context
 *
 * Global state management for multi-user household view selection.
 * Allows switching between "Combined", "Self", and other household members.
 */

import { createContext, useContext, useState, useEffect, useMemo, ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../features/auth/stores/authStore';

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
  /** Check if current user can edit (only true for self view) */
  canEdit: boolean;
}

const UserViewContext = createContext<UserViewContextType | undefined>(undefined);

export const UserViewProvider = ({ children }: { children: ReactNode }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuthStore();

  // Get user_id from URL or default to null (combined)
  const userIdFromUrl = searchParams.get('user');
  const [selectedUserId, setSelectedUserIdState] = useState<string | null>(userIdFromUrl);

  // Sync with URL on mount and when URL changes
  useEffect(() => {
    const urlUserId = searchParams.get('user');
    setSelectedUserIdState(urlUserId);
  }, [searchParams]);

  // Update URL when selection changes
  const setSelectedUserId = (userId: string | null) => {
    setSelectedUserIdState(userId);

    const newParams = new URLSearchParams(searchParams);
    if (userId) {
      newParams.set('user', userId);
    } else {
      newParams.delete('user');
    }
    setSearchParams(newParams, { replace: true });
  };

  const contextValue = useMemo(() => {
    const isSelfView = selectedUserId === user?.id;
    const isCombinedView = selectedUserId === null;
    const isOtherUserView = selectedUserId !== null && selectedUserId !== user?.id;
    const canEdit = isSelfView || isCombinedView;
    return { selectedUserId, setSelectedUserId, isSelfView, isCombinedView, isOtherUserView, canEdit };
  }, [selectedUserId, user?.id, setSelectedUserId]);

  return (
    <UserViewContext.Provider
      value={contextValue}
    >
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
