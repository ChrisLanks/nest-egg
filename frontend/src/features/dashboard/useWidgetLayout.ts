/**
 * Hook managing the dashboard widget layout state.
 *
 * - Reads the saved layout from the current user's profile (GET /auth/me)
 * - Falls back to DEFAULT_LAYOUT when null (new users, first load)
 * - In edit mode, keeps a local pendingLayout copy; discarded on Cancel
 * - Persists to the server via PUT /settings/dashboard-layout on Done
 */

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useCurrentUser } from '../../features/auth/hooks/useAuth';
import { queryKeys } from '../../services/queryClient';
import api from '../../services/api';
import { DEFAULT_LAYOUT } from './widgetRegistry';
import type { LayoutItem } from './types';

export const useWidgetLayout = () => {
  const { data: currentUser } = useCurrentUser();
  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [pendingLayout, setPendingLayout] = useState<LayoutItem[] | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const savedLayout = (currentUser?.dashboard_layout as LayoutItem[] | null | undefined) ?? null;
  const activeLayout: LayoutItem[] = pendingLayout ?? savedLayout ?? DEFAULT_LAYOUT;

  const startEditing = () => {
    setPendingLayout([...activeLayout]);
    setIsEditing(true);
  };

  const saveLayout = async () => {
    if (!pendingLayout) return;
    setIsSaving(true);
    try {
      await api.put('/settings/dashboard-layout', { layout: pendingLayout });
      queryClient.invalidateQueries({ queryKey: queryKeys.currentUser });
      setPendingLayout(null);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const cancelEditing = () => {
    setPendingLayout(null);
    setIsEditing(false);
  };

  return {
    layout: activeLayout,
    isEditing,
    isSaving,
    startEditing,
    saveLayout,
    cancelEditing,
    setPendingLayout,
  };
};
