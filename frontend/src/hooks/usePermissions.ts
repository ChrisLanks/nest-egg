/**
 * useCanI — React Query hook for checking permission grants.
 *
 * Usage:
 *   const canRead = useCanI('read', 'transaction', account.user_id);
 *   if (!canRead) return <ForbiddenBanner />;
 *
 * Returns true immediately if:
 *   - ownerId is not provided (caller owns the data)
 *   - current user IS the owner
 *   - current user is an org admin
 *   - there is an active, non-expired grant covering this action
 */

import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../features/auth/stores/authStore';
import { permissionsApi } from '../features/permissions/api/permissionsApi';
import type { GrantAction, ResourceType } from '../features/permissions/api/permissionsApi';

const FIVE_MINUTES = 5 * 60 * 1000;

export const useCanI = (
  action: GrantAction,
  resourceType: ResourceType,
  ownerId?: string,
): boolean => {
  const { user } = useAuthStore();

  const { data: receivedGrants = [] } = useQuery({
    queryKey: ['permissions', 'received'],
    queryFn: () => permissionsApi.listReceived(),
    staleTime: FIVE_MINUTES,
    // Only fetch when there might be grants to check
    enabled: !!user && !!ownerId && ownerId !== user?.id,
  });

  // No ownerId provided — assume caller owns the data
  if (!ownerId) return true;

  // Current user IS the owner
  if (user?.id === ownerId) return true;

  // Org admins always have access
  if ((user as any)?.is_org_admin) return true;

  const now = new Date();
  return receivedGrants.some(
    (g) =>
      g.grantor_id === ownerId &&
      g.resource_type === resourceType &&
      g.is_active &&
      g.actions.includes(action) &&
      (!g.expires_at || new Date(g.expires_at) > now),
  );
};
