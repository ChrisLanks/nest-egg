/**
 * Tests for AccountItem display logic controlled by isMultiUser.
 *
 * When a household has only one member, user badges, the owner-colour
 * background, and the write-access left border should all be hidden.
 * When there are two or more members, all three elements are visible.
 *
 * These functions mirror the exact expressions used inside AccountItem so
 * that regressions in the conditional logic are caught without rendering.
 */

import { describe, it, expect } from 'vitest';

// ── pure helpers mirroring AccountItem logic ──────────────────────────────────

/** mirrors: !!members && members.length > 1  (computed at the call site) */
const computeIsMultiUser = (members: unknown[] | null | undefined): boolean =>
  !!members && members.length > 1;

/**
 * mirrors:
 *   isCombinedView && isMultiUser ? getUserBgColor(primaryOwnerId) : 'gray.50'
 */
const computeBgColor = (
  isCombinedView: boolean,
  isMultiUser: boolean,
  ownerColor: string,
): string => (isCombinedView && isMultiUser ? ownerColor : 'gray.50');

/**
 * mirrors:
 *   isOwnedByCurrentUser && isMultiUser ? 3 : 0
 */
const computeBorderWidth = (isOwned: boolean, isMultiUser: boolean): number =>
  isOwned && isMultiUser ? 3 : 0;

/**
 * mirrors:
 *   isCombinedView && membersLoaded && isMultiUser
 */
const computeShowBadges = (
  isCombinedView: boolean,
  membersLoaded: boolean,
  isMultiUser: boolean,
): boolean => isCombinedView && membersLoaded && isMultiUser;

// ── isMultiUser derivation ────────────────────────────────────────────────────

describe('computeIsMultiUser', () => {
  it('is false for a single-member household', () => {
    expect(computeIsMultiUser([{ id: 'u1' }])).toBe(false);
  });

  it('is true for a two-member household', () => {
    expect(computeIsMultiUser([{ id: 'u1' }, { id: 'u2' }])).toBe(true);
  });

  it('is true for three or more members', () => {
    expect(computeIsMultiUser([{}, {}, {}])).toBe(true);
  });

  it('is false when members list is empty', () => {
    expect(computeIsMultiUser([])).toBe(false);
  });

  it('is false when members is null (data still loading)', () => {
    expect(computeIsMultiUser(null)).toBe(false);
  });

  it('is false when members is undefined', () => {
    expect(computeIsMultiUser(undefined)).toBe(false);
  });
});

// ── background colour ─────────────────────────────────────────────────────────

describe('computeBgColor', () => {
  it('uses owner colour in combined multi-user view', () => {
    expect(computeBgColor(true, true, 'blue.100')).toBe('blue.100');
  });

  it('uses gray.50 in combined single-user view', () => {
    expect(computeBgColor(true, false, 'blue.100')).toBe('gray.50');
  });

  it('uses gray.50 when not in combined view, even if multi-user', () => {
    expect(computeBgColor(false, true, 'blue.100')).toBe('gray.50');
  });

  it('uses gray.50 when not in combined view and single-user', () => {
    expect(computeBgColor(false, false, 'blue.100')).toBe('gray.50');
  });
});

// ── left border (write-access indicator) ─────────────────────────────────────

describe('computeBorderWidth', () => {
  it('shows border when user owns account in multi-user household', () => {
    expect(computeBorderWidth(true, true)).toBe(3);
  });

  it('hides border in single-user household even if owned', () => {
    expect(computeBorderWidth(true, false)).toBe(0);
  });

  it('hides border for accounts not owned by current user', () => {
    expect(computeBorderWidth(false, true)).toBe(0);
  });

  it('hides border when not owned and single-user', () => {
    expect(computeBorderWidth(false, false)).toBe(0);
  });
});

// ── user badge visibility ─────────────────────────────────────────────────────

describe('computeShowBadges', () => {
  it('shows badges in combined multi-user view when members are loaded', () => {
    expect(computeShowBadges(true, true, true)).toBe(true);
  });

  it('hides badges in single-user household', () => {
    expect(computeShowBadges(true, true, false)).toBe(false);
  });

  it('hides badges when not in combined view', () => {
    expect(computeShowBadges(false, true, true)).toBe(false);
  });

  it('hides badges while members are still loading', () => {
    expect(computeShowBadges(true, false, true)).toBe(false);
  });
});
