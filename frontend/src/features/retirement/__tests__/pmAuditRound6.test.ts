/**
 * PM audit round 6 frontend logic tests.
 *
 * Tests for:
 * - is_stale scenario detection
 * - CSV filename sanitization pattern
 * - Fan chart empty-state message selection
 * - Error state visibility logic for AccountDataSummary
 */

import { describe, expect, it } from 'vitest';

// ---------------------------------------------------------------------------
// CSV filename sanitization (mirrors backend logic)
// ---------------------------------------------------------------------------

function sanitizeFilename(name: string): string {
  return name.replace(/[^\w\-]/g, '_').slice(0, 50);
}

describe('CSV filename sanitization', () => {
  it('replaces spaces', () => {
    expect(sanitizeFilename('my plan')).not.toContain(' ');
  });

  it('replaces slashes', () => {
    expect(sanitizeFilename('plan/2025')).not.toContain('/');
  });

  it('replaces colons', () => {
    expect(sanitizeFilename('plan:v2')).not.toContain(':');
  });

  it('replaces asterisks', () => {
    expect(sanitizeFilename('plan*name')).not.toContain('*');
  });

  it('replaces question marks', () => {
    expect(sanitizeFilename('plan?')).not.toContain('?');
  });

  it('replaces double-quotes', () => {
    expect(sanitizeFilename('plan"name')).not.toContain('"');
  });

  it('replaces pipe', () => {
    expect(sanitizeFilename('plan|name')).not.toContain('|');
  });

  it('truncates to 50 characters', () => {
    expect(sanitizeFilename('a'.repeat(100))).toHaveLength(50);
  });

  it('preserves normal alphanumeric and hyphens', () => {
    expect(sanitizeFilename('my_plan-2025')).toBe('my_plan-2025');
  });
});

// ---------------------------------------------------------------------------
// Fan chart empty state message
// ---------------------------------------------------------------------------

function getFanChartMessage(isLoading: boolean, hasProjections: boolean): string | null {
  if (isLoading) return 'Running simulation...';
  if (!hasProjections) return 'No projection data yet — click Run Simulation below to generate your forecast.';
  return null; // chart renders normally
}

describe('Fan chart empty state', () => {
  it('shows loading message when simulating', () => {
    expect(getFanChartMessage(true, false)).toBe('Running simulation...');
  });

  it('prompts user to run simulation when no projections', () => {
    const msg = getFanChartMessage(false, false);
    expect(msg).toContain('Run Simulation');
  });

  it('returns null when projections are present', () => {
    expect(getFanChartMessage(false, true)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// is_stale badge visibility logic
// ---------------------------------------------------------------------------

interface ScenarioSummary {
  id: string;
  is_stale: boolean;
  include_all_members: boolean;
  household_member_ids?: string[] | null;
}

function shouldShowStaleBadge(scenario: ScenarioSummary): boolean {
  return scenario.is_stale;
}

describe('is_stale badge visibility', () => {
  it('shows stale badge when is_stale is true', () => {
    const s: ScenarioSummary = {
      id: '1',
      is_stale: true,
      include_all_members: true,
    };
    expect(shouldShowStaleBadge(s)).toBe(true);
  });

  it('hides stale badge when is_stale is false', () => {
    const s: ScenarioSummary = {
      id: '1',
      is_stale: false,
      include_all_members: false,
    };
    expect(shouldShowStaleBadge(s)).toBe(false);
  });

  it('personal plan (no household) is never stale', () => {
    const s: ScenarioSummary = {
      id: '1',
      is_stale: false,
      include_all_members: false,
      household_member_ids: null,
    };
    expect(shouldShowStaleBadge(s)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Life events empty state logic
// ---------------------------------------------------------------------------

function shouldShowLifeEventsEmptyState(
  hasScenario: boolean,
  eventCount: number
): boolean {
  return hasScenario && eventCount === 0;
}

describe('Life events empty state', () => {
  it('shows empty state when scenario exists but has no events', () => {
    expect(shouldShowLifeEventsEmptyState(true, 0)).toBe(true);
  });

  it('hides empty state when events exist', () => {
    expect(shouldShowLifeEventsEmptyState(true, 3)).toBe(false);
  });

  it('hides empty state when no scenario is selected', () => {
    expect(shouldShowLifeEventsEmptyState(false, 0)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Healthcare upper bound validation check (schema logic mirrored)
// ---------------------------------------------------------------------------

function validateHealthcareOverride(value: number | null | undefined): string | null {
  if (value === null || value === undefined) return null;
  if (value < 0) return 'Must be >= 0';
  if (value > 500000) return 'Must be <= 500,000';
  return null;
}

describe('Healthcare override upper bounds', () => {
  it('accepts null (use estimate)', () => {
    expect(validateHealthcareOverride(null)).toBeNull();
  });

  it('accepts valid amount', () => {
    expect(validateHealthcareOverride(15000)).toBeNull();
  });

  it('accepts exactly 500000', () => {
    expect(validateHealthcareOverride(500000)).toBeNull();
  });

  it('rejects value over 500000', () => {
    expect(validateHealthcareOverride(500001)).not.toBeNull();
  });

  it('rejects negative amount', () => {
    expect(validateHealthcareOverride(-1)).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Error state visibility logic for AccountDataSummary
// ---------------------------------------------------------------------------

function getAccountDataDisplayState(
  isLoading: boolean,
  isError: boolean,
  hasData: boolean
): 'loading' | 'error' | 'data' | 'empty' {
  if (isLoading) return 'loading';
  if (isError) return 'error';
  if (hasData) return 'data';
  return 'empty';
}

describe('AccountDataSummary display state', () => {
  it('shows loading state while fetching', () => {
    expect(getAccountDataDisplayState(true, false, false)).toBe('loading');
  });

  it('shows error state on API failure', () => {
    expect(getAccountDataDisplayState(false, true, false)).toBe('error');
  });

  it('shows data when loaded successfully', () => {
    expect(getAccountDataDisplayState(false, false, true)).toBe('data');
  });

  it('shows empty state when loaded but no accounts', () => {
    expect(getAccountDataDisplayState(false, false, false)).toBe('empty');
  });
});
