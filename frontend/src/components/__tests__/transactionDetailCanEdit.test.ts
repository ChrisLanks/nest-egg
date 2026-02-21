/**
 * Unit tests for TransactionDetailModal canEdit logic.
 *
 * The modal determines edit permission with this decision tree:
 *   - isSelfView       → always true  (all shown transactions are the user's own)
 *   - isOtherUserView  → always false (read-only view of another member)
 *   - combined view    → account.user_id === user.id (ownership check)
 *
 * Tests mirror the exact expression used in the component so that logic
 * regressions are caught without rendering.
 */

import { describe, it, expect } from 'vitest';

// ── helper mirroring TransactionDetailModal expression ────────────────────────

function resolveCanEdit(
  isSelfView: boolean,
  isOtherUserView: boolean,
  account: { user_id: string } | null | undefined,
  userId: string | undefined,
): boolean {
  return isSelfView
    ? true
    : isOtherUserView
      ? false
      : !!(account && account.user_id === userId);
}

const MY_ID = 'aaaa-bbbb-cccc-dddd';
const OTHER_ID = 'zzzz-yyyy-xxxx-wwww';

// ── self view ─────────────────────────────────────────────────────────────────

describe('canEdit — self view', () => {
  it('is true when account is loaded and matches user', () => {
    expect(resolveCanEdit(true, false, { user_id: MY_ID }, MY_ID)).toBe(true);
  });

  it('is true even while account query is loading (null)', () => {
    expect(resolveCanEdit(true, false, null, MY_ID)).toBe(true);
  });

  it('is true even if account.user_id were somehow different', () => {
    // Self view bypasses the ownership check entirely
    expect(resolveCanEdit(true, false, { user_id: OTHER_ID }, MY_ID)).toBe(true);
  });
});

// ── other-user view ───────────────────────────────────────────────────────────

describe('canEdit — other-user view', () => {
  it('is false when viewing another household member', () => {
    expect(resolveCanEdit(false, true, { user_id: OTHER_ID }, MY_ID)).toBe(false);
  });

  it('is false even if the account somehow matches the current user', () => {
    // isOtherUserView overrides ownership — you selected someone else's view
    expect(resolveCanEdit(false, true, { user_id: MY_ID }, MY_ID)).toBe(false);
  });

  it('is false when account is still loading', () => {
    expect(resolveCanEdit(false, true, null, MY_ID)).toBe(false);
  });
});

// ── combined household view ───────────────────────────────────────────────────

describe('canEdit — combined household view', () => {
  it('is true when account.user_id matches current user', () => {
    expect(resolveCanEdit(false, false, { user_id: MY_ID }, MY_ID)).toBe(true);
  });

  it('is false when account belongs to another household member', () => {
    expect(resolveCanEdit(false, false, { user_id: OTHER_ID }, MY_ID)).toBe(false);
  });

  it('is false while account query is still loading (undefined)', () => {
    expect(resolveCanEdit(false, false, undefined, MY_ID)).toBe(false);
  });

  it('is false while account query is still loading (null)', () => {
    expect(resolveCanEdit(false, false, null, MY_ID)).toBe(false);
  });

  it('is false when user is not authenticated (userId undefined)', () => {
    expect(resolveCanEdit(false, false, { user_id: MY_ID }, undefined)).toBe(false);
  });
});
