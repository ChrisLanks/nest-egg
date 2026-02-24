/**
 * Unit tests for TransactionDetailModal canEdit logic.
 *
 * The modal determines edit permission with this decision tree:
 *   - isSelfView       → always true  (all shown transactions are the user's own)
 *   - account loaded   → canWriteOwnedResource('transaction', account.user_id)
 *   - account loading  → false (safe loading state)
 *
 * Tests mirror the exact expression used in the component so that logic
 * regressions are caught without rendering.
 */

import { describe, it, expect } from 'vitest';

// ── helper mirroring TransactionDetailModal expression ────────────────────────

function resolveCanEdit(
  isSelfView: boolean,
  account: { user_id: string } | null | undefined,
  canWriteOwnedResource: (resourceType: string, ownerId: string) => boolean,
): boolean {
  return isSelfView
    ? true
    : account
      ? canWriteOwnedResource('transaction', account.user_id)
      : false;
}

const MY_ID = 'aaaa-bbbb-cccc-dddd';
const OTHER_ID = 'zzzz-yyyy-xxxx-wwww';

// Simulates canWriteOwnedResource: returns true only for own resources
const ownerOnly = (_type: string, ownerId: string) => ownerId === MY_ID;
// Simulates canWriteOwnedResource: returns true for own + granted
const withGrant = (_type: string, ownerId: string) => ownerId === MY_ID || ownerId === OTHER_ID;
// Simulates canWriteOwnedResource: always denies non-owned
const noGrants = (_type: string, ownerId: string) => ownerId === MY_ID;

// ── self view ─────────────────────────────────────────────────────────────────

describe('canEdit — self view', () => {
  it('is true when account is loaded and matches user', () => {
    expect(resolveCanEdit(true, { user_id: MY_ID }, ownerOnly)).toBe(true);
  });

  it('is true even while account query is loading (null)', () => {
    expect(resolveCanEdit(true, null, ownerOnly)).toBe(true);
  });

  it('is true even if account.user_id were somehow different', () => {
    // Self view bypasses the ownership check entirely
    expect(resolveCanEdit(true, { user_id: OTHER_ID }, ownerOnly)).toBe(true);
  });
});

// ── combined household view (own account) ────────────────────────────────────

describe('canEdit — combined view, own account', () => {
  it('is true when account.user_id matches current user', () => {
    expect(resolveCanEdit(false, { user_id: MY_ID }, ownerOnly)).toBe(true);
  });
});

// ── combined household view (other user's account, with grant) ───────────────

describe('canEdit — combined view, other user with grant', () => {
  it('is true when other user has granted write permission', () => {
    expect(resolveCanEdit(false, { user_id: OTHER_ID }, withGrant)).toBe(true);
  });
});

// ── combined household view (other user's account, no grant) ─────────────────

describe('canEdit — combined view, other user without grant', () => {
  it('is false when other user has not granted write permission', () => {
    expect(resolveCanEdit(false, { user_id: OTHER_ID }, noGrants)).toBe(false);
  });
});

// ── other-user view ──────────────────────────────────────────────────────────

describe('canEdit — other-user view', () => {
  it('is true when other user has granted write permission', () => {
    expect(resolveCanEdit(false, { user_id: OTHER_ID }, withGrant)).toBe(true);
  });

  it('is false when other user has no grants', () => {
    expect(resolveCanEdit(false, { user_id: OTHER_ID }, noGrants)).toBe(false);
  });
});

// ── loading / edge cases ─────────────────────────────────────────────────────

describe('canEdit — loading / edge cases', () => {
  it('is false while account query is still loading (undefined)', () => {
    expect(resolveCanEdit(false, undefined, withGrant)).toBe(false);
  });

  it('is false while account query is still loading (null)', () => {
    expect(resolveCanEdit(false, null, withGrant)).toBe(false);
  });
});
