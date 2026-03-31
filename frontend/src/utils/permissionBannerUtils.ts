/**
 * Utilities for the view-indicator banner in Layout.
 *
 * These are pure functions (no React dependencies) so they can be unit-tested
 * without a DOM environment.
 */

import type { PermissionGrant } from "../features/permissions/api/permissionsApi";

/**
 * Maps page paths to their primary resource type.
 * Dynamic segments (e.g. /accounts/123) are handled by getResourceTypeForPath.
 */
export const ROUTE_TO_RESOURCE_TYPE: Record<string, string> = {
  "/overview": "account",
  "/accounts": "account",
  "/transactions": "transaction",
  "/categories": "category",
  "/rules": "rule",
  "/recurring": "recurring_transaction",
  "/bills": "recurring_transaction",
  "/investments": "holding",
  "/budgets": "budget",
  "/goals": "savings_goal",
  "/cash-flow": "report",
  "/trends": "report",
  "/reports": "report",
  "/tax-deductible": "report",
  "/debt-payoff": "report",
  "/retirement": "retirement_scenario",
  "/year-in-review": "report",
  "/rental-properties": "report",
  "/education": "education_plan",
  "/fire": "fire_plan",
  "/calendar": "recurring_transaction",
  "/mortgage": "report",
  "/ss-claiming": "report",
  "/tax-projection": "report",
  "/financial-health": "report",
  "/net-worth-timeline": "report",
  "/tax-center": "report",
  "/life-planning": "report",
  "/investment-tools": "report",
  "/pe-performance": "report",
};

/** Human-friendly label for each resource type */
export const RESOURCE_TYPE_LABELS: Record<string, string> = {
  account: "Accounts",
  transaction: "Transactions",
  category: "Categories",
  rule: "Rules",
  recurring_transaction: "Recurring",
  holding: "Investments",
  budget: "Budgets",
  savings_goal: "Goals",
  report: "Reports",
  bill: "Bills",
  contribution: "Contributions",
  org_settings: "Settings",
  retirement_scenario: "Retirement Planner",
  education_plan: "Education Planning",
  fire_plan: "FIRE Calculator",
};

/**
 * Resolve the primary resource type for a given pathname.
 * Handles both exact matches (/accounts) and dynamic sub-routes (/accounts/123).
 */
export function getResourceTypeForPath(pathname: string): string | undefined {
  if (ROUTE_TO_RESOURCE_TYPE[pathname]) return ROUTE_TO_RESOURCE_TYPE[pathname];
  for (const [route, type] of Object.entries(ROUTE_TO_RESOURCE_TYPE)) {
    if (pathname.startsWith(route + "/")) return type;
  }
  return undefined;
}

export type BannerAccess = "write" | "read" | "none";

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
  if (!resourceType) return "none";

  const now = new Date();
  const activeForResource = grants.filter(
    (g) =>
      g.grantor_id === selectedUserId &&
      g.resource_type === resourceType &&
      g.is_active &&
      (!g.expires_at || new Date(g.expires_at) > now),
  );

  if (activeForResource.length === 0) return "none";

  const hasWrite = activeForResource.some(
    (g) =>
      g.actions.includes("create") ||
      g.actions.includes("update") ||
      g.actions.includes("delete"),
  );
  if (hasWrite) return "write";

  if (activeForResource.some((g) => g.actions.includes("read"))) return "read";

  return "none";
}

export interface MemberAccessInfo {
  memberId: string;
  access: BannerAccess;
}

/**
 * Compute per-member access levels for a multi-member selection.
 * Returns an entry for each non-self member in the selection, describing
 * the current user's access to that member's data for the given resource type.
 *
 * Household members always have implicit read access, so 'none' (no explicit
 * grant) is treated as read-only by the UI — same as the single-user banner.
 */
export function getMultiMemberAccess(
  grants: PermissionGrant[],
  currentUserId: string,
  selectedMemberIds: Set<string>,
  resourceType: string | undefined,
): MemberAccessInfo[] {
  const result: MemberAccessInfo[] = [];
  for (const memberId of selectedMemberIds) {
    if (memberId === currentUserId) continue;
    result.push({
      memberId,
      access: getBannerAccess(grants, memberId, resourceType),
    });
  }
  return result;
}
