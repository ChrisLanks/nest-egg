// @vitest-environment jsdom
/**
 * Unit tests for the widget registry and default layout.
 *
 * Uses jsdom because widgetRegistry imports component files that transitively
 * import api.ts, which reads localStorage at module load time.
 */

import { describe, it, expect } from 'vitest';
import { WIDGET_REGISTRY, DEFAULT_LAYOUT } from '../widgetRegistry';

// ── WIDGET_REGISTRY shape ─────────────────────────────────────────────────────

describe('WIDGET_REGISTRY', () => {
  const widgets = Object.values(WIDGET_REGISTRY);

  it('contains at least one widget', () => {
    expect(widgets.length).toBeGreaterThan(0);
  });

  it('every entry has an id that matches its key', () => {
    for (const [key, def] of Object.entries(WIDGET_REGISTRY)) {
      expect(def.id, `id mismatch for key "${key}"`).toBe(key);
    }
  });

  it('every entry has a non-empty title', () => {
    for (const def of widgets) {
      expect(def.title.trim(), `empty title for "${def.id}"`).not.toBe('');
    }
  });

  it('every entry has a non-empty description', () => {
    for (const def of widgets) {
      expect(def.description.trim(), `empty description for "${def.id}"`).not.toBe('');
    }
  });

  it('every defaultSpan is 1 or 2', () => {
    for (const def of widgets) {
      expect([1, 2], `invalid span for "${def.id}"`).toContain(def.defaultSpan);
    }
  });

  it('every entry has a component', () => {
    for (const def of widgets) {
      expect(def.component, `missing component for "${def.id}"`).toBeDefined();
    }
  });

  it('no duplicate IDs across the registry', () => {
    const ids = widgets.map((d) => d.id);
    const unique = new Set(ids);
    expect(unique.size).toBe(ids.length);
  });

  it('registers expected widget IDs', () => {
    const expectedIds = [
      'summary-stats',
      'net-worth-chart',
      'spending-insights',
      'cash-flow-trend',
      'cash-flow-forecast',
      'top-expenses',
      'recent-transactions',
      'account-balances',
      'savings-goals',
      'budgets',
      'debt-summary',
      'upcoming-bills',
      'subscriptions',
      'investment-performance',
      'asset-allocation',
    ];
    for (const id of expectedIds) {
      expect(WIDGET_REGISTRY[id], `missing widget "${id}"`).toBeDefined();
    }
  });
});

// ── DEFAULT_LAYOUT ────────────────────────────────────────────────────────────

describe('DEFAULT_LAYOUT', () => {
  it('is a non-empty array', () => {
    expect(DEFAULT_LAYOUT.length).toBeGreaterThan(0);
  });

  it('every id in DEFAULT_LAYOUT exists in WIDGET_REGISTRY', () => {
    for (const item of DEFAULT_LAYOUT) {
      expect(WIDGET_REGISTRY[item.id], `"${item.id}" not found in registry`).toBeDefined();
    }
  });

  it('every span is 1 or 2', () => {
    for (const item of DEFAULT_LAYOUT) {
      expect([1, 2], `invalid span for "${item.id}"`).toContain(item.span);
    }
  });

  it('no duplicate IDs', () => {
    const ids = DEFAULT_LAYOUT.map((i) => i.id);
    const unique = new Set(ids);
    expect(unique.size).toBe(ids.length);
  });

  it('opt-in widgets are NOT in the default layout', () => {
    const ids = new Set(DEFAULT_LAYOUT.map((i) => i.id));
    expect(ids.has('savings-goals')).toBe(false);
    expect(ids.has('budgets')).toBe(false);
    expect(ids.has('debt-summary')).toBe(false);
    expect(ids.has('upcoming-bills')).toBe(false);
    expect(ids.has('subscriptions')).toBe(false);
    expect(ids.has('investment-performance')).toBe(false);
    expect(ids.has('asset-allocation')).toBe(false);
  });

  it('core widgets ARE in the default layout', () => {
    const ids = new Set(DEFAULT_LAYOUT.map((i) => i.id));
    expect(ids.has('summary-stats')).toBe(true);
    expect(ids.has('net-worth-chart')).toBe(true);
    expect(ids.has('account-balances')).toBe(true);
  });

  it('summary-stats defaults to full width (span 2)', () => {
    const item = DEFAULT_LAYOUT.find((i) => i.id === 'summary-stats');
    expect(item?.span).toBe(2);
  });
});
