/**
 * Unit tests for the canWriteResource logic used in UserViewContext.
 *
 * The pure function is extracted here for isolated testing.  The implementation
 * in UserViewContext.tsx is:
 *
 *   canWriteResource(resourceType): boolean
 *     - true when isSelfView || isCombinedView
 *     - false when !isOtherUserView (should never happen, but safe fallback)
 *     - true when an active, non-expired grant from selectedUserId exists for
 *       the exact resource type and includes at least one write action
 *       (create | update | delete)
 */

import { describe, it, expect } from 'vitest';
import type { PermissionGrant } from '../../features/permissions/api/permissionsApi';

// ---------------------------------------------------------------------------
// Pure function mirroring UserViewContext.canWriteResource
// ---------------------------------------------------------------------------

function canWriteResource(
  resourceType: string,
  {
    isSelfView,
    isCombinedView,
    isOtherUserView,
    selectedUserId,
    receivedGrants,
  }: {
    isSelfView: boolean;
    isCombinedView: boolean;
    isOtherUserView: boolean;
    selectedUserId: string | null;
    receivedGrants: PermissionGrant[];
  },
): boolean {
  if (isSelfView || isCombinedView) return true;
  if (!isOtherUserView) return false;
  const now = new Date();
  return receivedGrants.some(
    (g) =>
      g.grantor_id === selectedUserId &&
      g.resource_type === resourceType &&
      g.is_active &&
      (!g.expires_at || new Date(g.expires_at) > now) &&
      (g.actions.includes('create') ||
        g.actions.includes('update') ||
        g.actions.includes('delete')),
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const OWNER = 'user-owner-id';
const VIEWER = 'user-viewer-id';
const ORG = 'org-id';
const futureDate = () => new Date(Date.now() + 10 * 60 * 1000).toISOString();
const pastDate = () => new Date(Date.now() - 10 * 60 * 1000).toISOString();

function makeGrant(overrides: Partial<PermissionGrant> = {}): PermissionGrant {
  return {
    id: 'grant-1',
    organization_id: ORG,
    grantor_id: OWNER,
    grantee_id: VIEWER,
    resource_type: 'transaction',
    resource_id: null,
    actions: ['read', 'create'],
    granted_at: new Date().toISOString(),
    expires_at: null,
    is_active: true,
    ...overrides,
  };
}

const selfCtx = {
  isSelfView: true,
  isCombinedView: false,
  isOtherUserView: false,
  selectedUserId: OWNER,
  receivedGrants: [],
};

const combinedCtx = {
  isSelfView: false,
  isCombinedView: true,
  isOtherUserView: false,
  selectedUserId: null,
  receivedGrants: [],
};

function otherCtx(grants: PermissionGrant[]) {
  return {
    isSelfView: false,
    isCombinedView: false,
    isOtherUserView: true,
    selectedUserId: OWNER,
    receivedGrants: grants,
  };
}

// ---------------------------------------------------------------------------
// Self view
// ---------------------------------------------------------------------------

describe('canWriteResource — self view', () => {
  it('always returns true regardless of resource type', () => {
    expect(canWriteResource('transaction', selfCtx)).toBe(true);
    expect(canWriteResource('budget', selfCtx)).toBe(true);
    expect(canWriteResource('report', selfCtx)).toBe(true);
  });

  it('returns true even with no grants', () => {
    expect(canWriteResource('account', { ...selfCtx, receivedGrants: [] })).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Combined household view
// ---------------------------------------------------------------------------

describe('canWriteResource — combined view', () => {
  it('always returns true regardless of resource type', () => {
    expect(canWriteResource('transaction', combinedCtx)).toBe(true);
    expect(canWriteResource('savings_goal', combinedCtx)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Other-user view: no grants
// ---------------------------------------------------------------------------

describe('canWriteResource — other-user view with no grants', () => {
  it('returns false when no grants exist', () => {
    expect(canWriteResource('transaction', otherCtx([]))).toBe(false);
  });

  it('returns false for every resource type when empty grants', () => {
    for (const rt of ['account', 'budget', 'report', 'rule', 'category']) {
      expect(canWriteResource(rt, otherCtx([]))).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------
// Other-user view: matching grants
// ---------------------------------------------------------------------------

describe('canWriteResource — other-user view with grants', () => {
  it('returns true when there is a create grant for the resource type', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['read', 'create'] })];
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(true);
  });

  it('returns true when there is an update grant for the resource type', () => {
    const grants = [makeGrant({ resource_type: 'budget', actions: ['update'] })];
    expect(canWriteResource('budget', otherCtx(grants))).toBe(true);
  });

  it('returns true when there is a delete grant for the resource type', () => {
    const grants = [makeGrant({ resource_type: 'rule', actions: ['delete'] })];
    expect(canWriteResource('rule', otherCtx(grants))).toBe(true);
  });

  it('returns false when the grant is read-only', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['read'] })];
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(false);
  });

  it('returns false when the grant is for a different resource type', () => {
    const grants = [makeGrant({ resource_type: 'account', actions: ['create'] })];
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(false);
    expect(canWriteResource('budget', otherCtx(grants))).toBe(false);
  });

  it('returns false when the grant is for a different grantor', () => {
    const grants = [makeGrant({ grantor_id: 'someone-else', resource_type: 'transaction', actions: ['create'] })];
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(false);
  });

  it('returns false when the grant is inactive', () => {
    const grants = [makeGrant({ is_active: false, resource_type: 'transaction', actions: ['create'] })];
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(false);
  });

  it('returns false when the grant is expired', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['create'], expires_at: pastDate() })];
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(false);
  });

  it('returns true when the grant has a future expiry', () => {
    const grants = [makeGrant({ resource_type: 'transaction', actions: ['create'], expires_at: futureDate() })];
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(true);
  });

  it('returns true when at least one of multiple grants gives write access', () => {
    const grants = [
      makeGrant({ id: 'g1', resource_type: 'transaction', actions: ['read'] }),
      makeGrant({ id: 'g2', resource_type: 'transaction', actions: ['update'] }),
    ];
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(true);
  });

  it('is resource-type-specific: does not bleed between types', () => {
    const grants = [makeGrant({ resource_type: 'account', actions: ['create', 'update', 'delete'] })];
    // account → writable
    expect(canWriteResource('account', otherCtx(grants))).toBe(true);
    // transaction/budget → no grant → not writable
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(false);
    expect(canWriteResource('budget', otherCtx(grants))).toBe(false);
    expect(canWriteResource('report', otherCtx(grants))).toBe(false);
  });

  it('handles multiple resource types in grants independently', () => {
    const grants = [
      makeGrant({ id: 'g1', resource_type: 'account', actions: ['read'] }),
      makeGrant({ id: 'g2', resource_type: 'transaction', actions: ['create'] }),
      makeGrant({ id: 'g3', resource_type: 'budget', actions: ['update', 'delete'] }),
    ];
    expect(canWriteResource('account', otherCtx(grants))).toBe(false);    // read-only
    expect(canWriteResource('transaction', otherCtx(grants))).toBe(true); // create
    expect(canWriteResource('budget', otherCtx(grants))).toBe(true);      // update+delete
    expect(canWriteResource('rule', otherCtx(grants))).toBe(false);       // no grant
  });
});
