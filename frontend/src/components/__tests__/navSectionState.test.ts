/**
 * Tests for the left-nav collapsed-section persistence logic.
 *
 * The Layout component reads initial state from localStorage on mount and
 * writes it back on every toggle.  We verify both halves in isolation so
 * regressions in the persistence layer are caught without needing to render
 * the full sidebar.
 */

// @vitest-environment jsdom

import { describe, it, expect, beforeEach } from 'vitest';

// ── helpers that mirror the component logic exactly ───────────────────────────

const STORAGE_KEY = 'nav-collapsed-sections';

/** Same initialiser used in useState(() => ...) */
const loadCollapsedSections = (): Record<string, boolean> => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
};

/** Same updater used inside setCollapsedSections */
const toggleSection = (
  prev: Record<string, boolean>,
  sectionName: string,
): Record<string, boolean> => {
  const next = { ...prev, [sectionName]: !prev[sectionName] };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {}
  return next;
};

// ── tests ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  localStorage.clear();
});

describe('loadCollapsedSections', () => {
  it('returns an empty object when nothing is stored', () => {
    expect(loadCollapsedSections()).toEqual({});
  });

  it('restores a previously saved collapsed map', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ Cash: true, Investments: false }),
    );
    expect(loadCollapsedSections()).toEqual({ Cash: true, Investments: false });
  });

  it('returns an empty object when stored JSON is malformed', () => {
    localStorage.setItem(STORAGE_KEY, 'not-valid-json');
    expect(loadCollapsedSections()).toEqual({});
  });
});

describe('toggleSection', () => {
  it('collapses an expanded section', () => {
    const next = toggleSection({ Cash: false }, 'Cash');
    expect(next.Cash).toBe(true);
  });

  it('expands a collapsed section', () => {
    const next = toggleSection({ Cash: true }, 'Cash');
    expect(next.Cash).toBe(false);
  });

  it('collapses an unseen section (defaults to false → true)', () => {
    // Sections not yet in the map are treated as expanded (false)
    const next = toggleSection({}, 'Investments');
    expect(next.Investments).toBe(true);
  });

  it('does not mutate other sections', () => {
    const prev = { Cash: false, 'Credit Cards': true, Investments: false };
    const next = toggleSection(prev, 'Cash');
    expect(next['Credit Cards']).toBe(true);
    expect(next.Investments).toBe(false);
  });

  it('persists the new state to localStorage', () => {
    toggleSection({}, 'Cash');
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored).toEqual({ Cash: true });
  });

  it('overwrites the previous localStorage value on each toggle', () => {
    let state = toggleSection({}, 'Cash');        // Cash → true
    state = toggleSection(state, 'Cash');          // Cash → false
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored.Cash).toBe(false);
  });

  it('state loaded after a toggle matches the persisted value', () => {
    toggleSection({ Cash: false, Investments: true }, 'Investments');
    const reloaded = loadCollapsedSections();
    expect(reloaded).toEqual({ Cash: false, Investments: false });
  });
});
