import { describe, it, expect } from 'vitest';
import {
  getBannerAccess,
  getResourceTypeForPath,
  ROUTE_TO_RESOURCE_TYPE,
  RESOURCE_TYPE_LABELS,
} from '../permissionBannerUtils';
import type { PermissionGrant } from '../../features/permissions/api/permissionsApi';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const GRANTOR = 'user-owner-id';
const GRANTEE = 'user-viewer-id';
const ORG = 'org-id';

const futureDate = () => new Date(Date.now() + 10 * 60 * 1000).toISOString(); // +10 min
const pastDate = () => new Date(Date.now() - 10 * 60 * 1000).toISOString();  // -10 min

function makeGrant(overrides: Partial<PermissionGrant> = {}): PermissionGrant {
  return {
    id: 'grant-1',
    organization_id: ORG,
    grantor_id: GRANTOR,
    grantee_id: GRANTEE,
    resource_type: 'transaction',
    resource_id: null,
    actions: ['read'],
    granted_at: new Date().toISOString(),
    expires_at: null,
    is_active: true,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// getBannerAccess
// ---------------------------------------------------------------------------

describe('getBannerAccess', () => {
  it('returns "none" when resourceType is undefined', () => {
    expect(getBannerAccess([makeGrant()], GRANTOR, undefined)).toBe('none');
  });

  it('returns "none" when grants array is empty', () => {
    expect(getBannerAccess([], GRANTOR, 'transaction')).toBe('none');
  });

  it('returns "read" for a read-only grant on the matching resource type', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['read'] })];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('read');
  });

  it('returns "write" when grant includes create', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['read', 'create'] })];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('write');
  });

  it('returns "write" when grant includes update', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['update'] })];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('write');
  });

  it('returns "write" when grant includes delete', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['delete'] })];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('write');
  });

  it('returns "none" when the grant is for a different resource type', () => {
    const grants = [makeGrant({ resource_type: 'account', actions: ['read', 'create'] })];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('none');
  });

  it('returns "none" when the grant is from a different grantor', () => {
    const grants = [makeGrant({ grantor_id: 'other-user', resource_type: 'transaction', actions: ['read'] })];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('none');
  });

  it('returns "none" when the grant is inactive (is_active false)', () => {
    const grants = [makeGrant({ is_active: false, resource_type: 'transaction', actions: ['read'] })];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('none');
  });

  it('returns "none" when the grant is expired', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['read'], expires_at: pastDate() })];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('none');
  });

  it('returns "read" when the grant has a future expiry', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['read'], expires_at: futureDate() })];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('read');
  });

  it('returns "write" when one of multiple grants has write access', () => {
    const grants = [
      makeGrant({ id: 'g1', resource_type: 'transaction', actions: ['read'] }),
      makeGrant({ id: 'g2', resource_type: 'transaction', actions: ['create', 'update'] }),
    ];
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('write');
  });

  it('returns "write" for the correct resource type when mixed grants exist', () => {
    const grants = [
      makeGrant({ id: 'g1', resource_type: 'account', actions: ['read'] }),       // read on accounts
      makeGrant({ id: 'g2', resource_type: 'transaction', actions: ['create'] }), // write on transactions
    ];
    expect(getBannerAccess(grants, GRANTOR, 'account')).toBe('read');
    expect(getBannerAccess(grants, GRANTOR, 'transaction')).toBe('write');
    expect(getBannerAccess(grants, GRANTOR, 'holding')).toBe('none');
  });
});

// ---------------------------------------------------------------------------
// getResourceTypeForPath
// ---------------------------------------------------------------------------

describe('getResourceTypeForPath', () => {
  it('resolves known exact paths', () => {
    expect(getResourceTypeForPath('/overview')).toBe('account');
    expect(getResourceTypeForPath('/accounts')).toBe('account');
    expect(getResourceTypeForPath('/transactions')).toBe('transaction');
    expect(getResourceTypeForPath('/categories')).toBe('category');
    expect(getResourceTypeForPath('/rules')).toBe('rule');
    expect(getResourceTypeForPath('/recurring')).toBe('recurring_transaction');
    expect(getResourceTypeForPath('/bills')).toBe('recurring_transaction');
    expect(getResourceTypeForPath('/investments')).toBe('holding');
    expect(getResourceTypeForPath('/budgets')).toBe('budget');
    expect(getResourceTypeForPath('/goals')).toBe('savings_goal');
    expect(getResourceTypeForPath('/income-expenses')).toBe('report');
    expect(getResourceTypeForPath('/trends')).toBe('report');
    expect(getResourceTypeForPath('/reports')).toBe('report');
    expect(getResourceTypeForPath('/tax-deductible')).toBe('report');
    expect(getResourceTypeForPath('/debt-payoff')).toBe('report');
  });

  it('resolves dynamic sub-routes via prefix matching', () => {
    expect(getResourceTypeForPath('/accounts/some-uuid-here')).toBe('account');
    expect(getResourceTypeForPath('/transactions/abc-123')).toBe('transaction');
  });

  it('returns undefined for unknown paths', () => {
    expect(getResourceTypeForPath('/unknown-page')).toBeUndefined();
    expect(getResourceTypeForPath('/permissions')).toBeUndefined();
    expect(getResourceTypeForPath('/household')).toBeUndefined();
    expect(getResourceTypeForPath('/')).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// ROUTE_TO_RESOURCE_TYPE — structural checks
// ---------------------------------------------------------------------------

describe('ROUTE_TO_RESOURCE_TYPE', () => {
  it('contains the post-login destination /overview', () => {
    expect(ROUTE_TO_RESOURCE_TYPE['/overview']).toBeDefined();
  });

  it('every mapped value has a human-readable label in RESOURCE_TYPE_LABELS', () => {
    const missingLabels = [...new Set(Object.values(ROUTE_TO_RESOURCE_TYPE))].filter(
      (type) => !RESOURCE_TYPE_LABELS[type],
    );
    expect(missingLabels).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Household default-access semantics
// ---------------------------------------------------------------------------

describe('Household default read access', () => {
  it('getBannerAccess returns "none" when no explicit grant exists', () => {
    // The utility accurately reports no explicit grant.
    // The UI layer (Layout) is responsible for treating "none" as read-only,
    // since household members always have implicit read access to each other's data.
    expect(getBannerAccess([], GRANTOR, 'transaction')).toBe('none');
  });

  it('"none" is semantically distinct from "read" so callers can choose the display', () => {
    const readGrant = [makeGrant({ actions: ['read'] })];
    expect(getBannerAccess(readGrant, GRANTOR, 'transaction')).toBe('read');
    expect(getBannerAccess([], GRANTOR, 'transaction')).toBe('none');
  });
});
