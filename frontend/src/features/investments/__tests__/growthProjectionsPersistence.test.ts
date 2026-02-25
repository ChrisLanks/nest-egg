/**
 * Tests for Growth Projections persistence and scenario protection logic.
 *
 * Covers:
 * - localStorage persistence (save / load / corrupt data handling)
 * - Base Case protection (cannot be removed)
 * - Smart default years calculation from birth year
 */

// @vitest-environment jsdom

import { describe, it, expect, beforeEach } from 'vitest';

// ── Mirror the component logic for testability ──────────────────────────────

const STORAGE_KEY = 'nest-egg-growth-projections';

interface ScenarioConfig {
  id: string;
  name: string;
  color: string;
  annualReturn: number;
  volatility: number;
  inflationRate: number;
  years: number;
  retirementYear?: number;
  annualWithdrawal?: number;
  withdrawalRate?: number;
  withdrawalStrategy: 'fixed' | 'percent';
  enableRetirement: boolean;
}

interface PersistedState {
  scenarios: ScenarioConfig[];
  activeScenarioIndex: number;
  showInflationAdjusted: boolean;
}

let scenarioCounter = 0;

const makeDefaultScenario = (overrides?: Partial<ScenarioConfig>): ScenarioConfig => ({
  id: `scenario-${++scenarioCounter}`,
  name: 'Base Case',
  color: '#4299E1',
  annualReturn: 7,
  volatility: 15,
  inflationRate: 3,
  years: 10,
  withdrawalStrategy: 'percent',
  enableRetirement: false,
  ...overrides,
});

function loadPersistedState(): PersistedState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && Array.isArray(parsed.scenarios) && parsed.scenarios.length > 0) {
      return parsed as PersistedState;
    }
  } catch { /* ignore corrupt localStorage */ }
  return null;
}

function savePersistedState(state: PersistedState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch { /* ignore */ }
}

function computeDefaultYears(birthYear: number | null | undefined): number {
  if (!birthYear) return 10;
  const currentYear = new Date().getFullYear();
  const age = currentYear - birthYear;
  const yearsUntilRetirement = Math.round(59.5 - age);
  return Math.max(1, yearsUntilRetirement);
}

/** Simulates removeScenario logic — Base Case (index 0) is protected */
function removeScenario(
  scenarios: ScenarioConfig[],
  idx: number,
): ScenarioConfig[] | null {
  if (scenarios.length <= 1 || idx === 0) return null; // rejected
  return scenarios.filter((_, i) => i !== idx);
}

// ── Tests ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  localStorage.clear();
  scenarioCounter = 0;
});

// ── Persistence ─────────────────────────────────────────────────────────────

describe('localStorage persistence', () => {
  it('returns null when nothing is stored', () => {
    expect(loadPersistedState()).toBeNull();
  });

  it('round-trips a persisted state', () => {
    const state: PersistedState = {
      scenarios: [makeDefaultScenario()],
      activeScenarioIndex: 0,
      showInflationAdjusted: true,
    };
    savePersistedState(state);
    const loaded = loadPersistedState();
    expect(loaded).not.toBeNull();
    expect(loaded!.scenarios).toHaveLength(1);
    expect(loaded!.scenarios[0].name).toBe('Base Case');
    expect(loaded!.activeScenarioIndex).toBe(0);
    expect(loaded!.showInflationAdjusted).toBe(true);
  });

  it('persists multiple scenarios with custom parameters', () => {
    const state: PersistedState = {
      scenarios: [
        makeDefaultScenario(),
        makeDefaultScenario({ name: 'Scenario 2', annualReturn: 10, color: '#ED8936' }),
      ],
      activeScenarioIndex: 1,
      showInflationAdjusted: false,
    };
    savePersistedState(state);
    const loaded = loadPersistedState();
    expect(loaded!.scenarios).toHaveLength(2);
    expect(loaded!.scenarios[1].name).toBe('Scenario 2');
    expect(loaded!.scenarios[1].annualReturn).toBe(10);
    expect(loaded!.activeScenarioIndex).toBe(1);
    expect(loaded!.showInflationAdjusted).toBe(false);
  });

  it('returns null for corrupt JSON', () => {
    localStorage.setItem(STORAGE_KEY, 'not valid json{{{');
    expect(loadPersistedState()).toBeNull();
  });

  it('returns null for empty scenarios array', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ scenarios: [], activeScenarioIndex: 0 }));
    expect(loadPersistedState()).toBeNull();
  });

  it('returns null for missing scenarios key', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ foo: 'bar' }));
    expect(loadPersistedState()).toBeNull();
  });
});

// ── Base Case protection ────────────────────────────────────────────────────

describe('Base Case scenario protection', () => {
  it('prevents removing the only scenario', () => {
    const scenarios = [makeDefaultScenario()];
    expect(removeScenario(scenarios, 0)).toBeNull();
  });

  it('prevents removing Base Case (index 0) even with multiple scenarios', () => {
    const scenarios = [
      makeDefaultScenario(),
      makeDefaultScenario({ name: 'Scenario 2', color: '#ED8936' }),
    ];
    expect(removeScenario(scenarios, 0)).toBeNull();
  });

  it('allows removing non-Base-Case scenarios (index > 0)', () => {
    const scenarios = [
      makeDefaultScenario(),
      makeDefaultScenario({ name: 'Scenario 2', color: '#ED8936' }),
      makeDefaultScenario({ name: 'Scenario 3', color: '#48BB78' }),
    ];
    const result = removeScenario(scenarios, 1);
    expect(result).not.toBeNull();
    expect(result).toHaveLength(2);
    expect(result![0].name).toBe('Base Case');
    expect(result![1].name).toBe('Scenario 3');
  });

  it('allows removing the last scenario (index 2)', () => {
    const scenarios = [
      makeDefaultScenario(),
      makeDefaultScenario({ name: 'Scenario 2', color: '#ED8936' }),
      makeDefaultScenario({ name: 'Scenario 3', color: '#48BB78' }),
    ];
    const result = removeScenario(scenarios, 2);
    expect(result).not.toBeNull();
    expect(result).toHaveLength(2);
    expect(result![1].name).toBe('Scenario 2');
  });
});

// ── Smart default years ─────────────────────────────────────────────────────

describe('computeDefaultYears', () => {
  const currentYear = new Date().getFullYear();

  it('returns 10 when birth year is null', () => {
    expect(computeDefaultYears(null)).toBe(10);
  });

  it('returns 10 when birth year is undefined', () => {
    expect(computeDefaultYears(undefined)).toBe(10);
  });

  it('calculates years until 59.5 for a 30-year-old', () => {
    const birthYear = currentYear - 30;
    // 59.5 - 30 = 29.5 → rounds to 30
    expect(computeDefaultYears(birthYear)).toBe(30);
  });

  it('calculates years until 59.5 for a 25-year-old', () => {
    const birthYear = currentYear - 25;
    // 59.5 - 25 = 34.5 → rounds to 35
    expect(computeDefaultYears(birthYear)).toBe(35);
  });

  it('calculates years until 59.5 for a 55-year-old', () => {
    const birthYear = currentYear - 55;
    // 59.5 - 55 = 4.5 → rounds to 5
    expect(computeDefaultYears(birthYear)).toBe(5);
  });

  it('returns 1 for someone already past 59.5', () => {
    const birthYear = currentYear - 65;
    // 59.5 - 65 = -5.5 → clamped to 1
    expect(computeDefaultYears(birthYear)).toBe(1);
  });

  it('returns 1 for someone exactly 59', () => {
    const birthYear = currentYear - 59;
    // 59.5 - 59 = 0.5 → rounds to 1
    expect(computeDefaultYears(birthYear)).toBe(1);
  });
});
