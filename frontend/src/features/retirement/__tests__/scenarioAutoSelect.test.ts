/**
 * Tests for RetirementPage scenario auto-select logic.
 *
 * Covers:
 * - Auto-select default scenario when none is selected
 * - Auto-select first scenario when no default exists
 * - Reset stale localStorage ID that no longer matches any DB scenario
 * - Keep valid selection when it matches a fetched scenario
 */

// @vitest-environment jsdom

import { describe, it, expect, beforeEach } from 'vitest';

// ── Mirror the auto-select logic from RetirementPage ──────────────────────────

interface ScenarioSummary {
  id: string;
  name: string;
  is_default: boolean;
}

/**
 * Mirrors the useEffect in RetirementPage that auto-selects a scenario.
 * Returns the new selectedScenarioId (or null if no change needed).
 */
function resolveSelectedScenario(
  scenarios: ScenarioSummary[] | undefined,
  currentSelection: string | null,
): string | null {
  if (!scenarios?.length) return currentSelection; // no change

  // If current selection exists in the fetched list, keep it
  if (currentSelection && scenarios.find((s) => s.id === currentSelection)) {
    return currentSelection;
  }

  // Current ID is null or stale — pick a valid one
  const defaultScenario = scenarios.find((s) => s.is_default);
  return defaultScenario?.id ?? scenarios[0].id;
}

// ── Test data ─────────────────────────────────────────────────────────────────

const SCENARIO_A: ScenarioSummary = { id: 'aaa-111', name: 'My Retirement Plan', is_default: true };
const SCENARIO_B: ScenarioSummary = { id: 'bbb-222', name: 'Early Retirement', is_default: false };
const SCENARIO_C: ScenarioSummary = { id: 'ccc-333', name: 'Conservative', is_default: false };

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Retirement scenario auto-select', () => {
  describe('when no scenario is currently selected', () => {
    it('selects the default scenario', () => {
      const result = resolveSelectedScenario([SCENARIO_A, SCENARIO_B], null);
      expect(result).toBe('aaa-111');
    });

    it('selects the first scenario when none is marked default', () => {
      const noDefault = [
        { ...SCENARIO_A, is_default: false },
        SCENARIO_B,
      ];
      const result = resolveSelectedScenario(noDefault, null);
      expect(result).toBe('aaa-111');
    });
  });

  describe('when current selection is valid', () => {
    it('keeps the current selection if it exists in the list', () => {
      const result = resolveSelectedScenario([SCENARIO_A, SCENARIO_B], 'bbb-222');
      expect(result).toBe('bbb-222');
    });
  });

  describe('when current selection is stale', () => {
    it('resets to default when stale ID is not in the list', () => {
      const result = resolveSelectedScenario(
        [SCENARIO_A, SCENARIO_B],
        'stale-id-from-localstorage',
      );
      expect(result).toBe('aaa-111');
    });

    it('resets to first scenario when stale and no default', () => {
      const noDefault = [
        { ...SCENARIO_B, is_default: false },
        { ...SCENARIO_C, is_default: false },
      ];
      const result = resolveSelectedScenario(noDefault, 'stale-id');
      expect(result).toBe('bbb-222');
    });
  });

  describe('edge cases', () => {
    it('returns null (no change) when scenarios list is undefined', () => {
      expect(resolveSelectedScenario(undefined, 'some-id')).toBe('some-id');
    });

    it('returns null (no change) when scenarios list is empty', () => {
      expect(resolveSelectedScenario([], 'some-id')).toBe('some-id');
    });

    it('handles single scenario with no current selection', () => {
      const result = resolveSelectedScenario([SCENARIO_A], null);
      expect(result).toBe('aaa-111');
    });

    it('handles single scenario with stale selection', () => {
      const result = resolveSelectedScenario([SCENARIO_A], 'deleted-scenario-id');
      expect(result).toBe('aaa-111');
    });
  });
});

// ── localStorage persistence helper tests ─────────────────────────────────────

const STORAGE_KEY = 'retirement-active-scenario';

function loadPersistedScenarioId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function savePersistedScenarioId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch { /* ignore */ }
}

beforeEach(() => {
  localStorage.clear();
});

describe('Retirement localStorage persistence', () => {
  it('returns null when nothing is stored', () => {
    expect(loadPersistedScenarioId()).toBeNull();
  });

  it('round-trips a scenario ID', () => {
    savePersistedScenarioId('aaa-111');
    expect(loadPersistedScenarioId()).toBe('aaa-111');
  });

  it('overwrites previous value', () => {
    savePersistedScenarioId('aaa-111');
    savePersistedScenarioId('bbb-222');
    expect(loadPersistedScenarioId()).toBe('bbb-222');
  });
});
