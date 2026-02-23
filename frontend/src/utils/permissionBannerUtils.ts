/**
 * Utilities for the view-indicator banner in Layout.
 *
 * These are pure functions (no React dependencies) so they can be unit-tested
 * without a DOM environment.
 */

import type { PermissionGrant } from '../features/permissions/api/permissionsApi';

/**
 * Maps page paths to their primary resource type.
 * Dynamic segments (e.g. /accounts/123) are handled by getResourceTypeForPath.
 */
export const ROUTE_TO_RESOURCE_TYPE: Record<string, string> = {
  '/overview': 'account',
  '/accounts': 'account',
  '/transactions': 'transaction',
  '/categories': 'category',
  '/rules': 'rule',
  '/recurring': 'recurring_transaction',
  '/bills': 'recurring_transaction',
  '/investments': 'holding',
  '/budgets': 'budget',
  '/goals': 'savings_goal',
  '/income-expenses': 'report',
  '/trends': 'report',
  '/reports': 'report',
  '/tax-deductible': 'report',
  '/debt-payoff': 'report',
};

/** Human-friendly label for each resource type */
export const RESOURCE_TYPE_LABELS: Record<string, string> = {
  account: 'Accounts',
  transaction: 'Transactions',
  category: 'Categories',
  rule: 'Rules',
  recurring_transaction: 'Recurring',
  holding: 'Investments',
  budget: 'Budgets',
  savings_goal: 'Goals',
  report: 'Reports',
  bill: 'Bills',
  contribution: 'Contributions',
  org_settings: 'Settings',
};

/**
 * Resolve the primary resource type for a given pathname.
 * Handles both exact matches (/accounts) and dynamic sub-routes (/accounts/123).
 */
export function getResourceTypeForPath(pathname: string): string | undefined {
  if (ROUTE_TO_RESOURCE_TYPE[pathname]) return ROUTE_TO_RESOURCE_TYPE[pathname];
  for (const [route, type] of Object.entries(ROUTE_TO_RESOURCE_TYPE)) {
    if (pathname.startsWith(route + '/')) return type;
  }
  return undefined;
}

export type BannerAccess = 'write' | 'read' | 'none';

/**
 * Determine the access level the viewer has for a specific resource type
 * based on grants received from the data owner (selectedUserId).
 *
 * Returns:
 *   'write' — at least one active grant includes a mutating action
 *   'read'  — active grant exists but only includes 'read'
 *   'none'  — no active grant for this resource type
 */
export function getBannerAccess(
  grants: PermissionGrant[],
  selectedUserId: string,
  resourceType: string | undefined,
): BannerAccess {
  if (!resourceType) return 'none';

  const now = new Date();
  const activeForResource = grants.filter(
    (g) =>
      g.grantor_id === selectedUserId &&
      g.resource_type === resourceType &&
      g.is_active &&
      (!g.expires_at || new Date(g.expires_at) > now),
  );

  if (activeForResource.length === 0) return 'none';

  const hasWrite = activeForResource.some(
    (g) =>
      g.actions.includes('create') ||
      g.actions.includes('update') ||
      g.actions.includes('delete'),
  );
  if (hasWrite) return 'write';

  if (activeForResource.some((g) => g.actions.includes('read'))) return 'read';

  return 'none';
}
