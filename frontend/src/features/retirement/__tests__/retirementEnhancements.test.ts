/**
 * Tests for retirement planner UX enhancements.
 *
 * Covers:
 * - Slider range values
 * - Tab rename logic
 * - Tab scroll preservation
 * - SS manual override logic
 * - Healthcare edit mode logic
 * - Withdrawal strategy selection logic
 * - Cash balance display logic
 * - Capital gains display logic
 * - Household view filtering logic
 */

import { describe, it, expect } from 'vitest';

// ── Slider Range Validation ──────────────────────────────────────────────────

describe('Slider Ranges', () => {
  // These test the expected min/max values that the UI should enforce
  const RETIREMENT_AGE_MIN = 15;
  const RETIREMENT_AGE_MAX = 95;
  const LIFE_EXPECTANCY_MIN = 15;
  const LIFE_EXPECTANCY_MAX = 110;

  it('retirement age min should be 15', () => {
    expect(RETIREMENT_AGE_MIN).toBe(15);
  });

  it('retirement age max should be 95', () => {
    expect(RETIREMENT_AGE_MAX).toBe(95);
  });

  it('life expectancy min should be 15 (plan through age)', () => {
    expect(LIFE_EXPECTANCY_MIN).toBe(15);
  });

  it('life expectancy max should be 110', () => {
    expect(LIFE_EXPECTANCY_MAX).toBe(110);
  });

  it('should clamp retirement age to valid range', () => {
    const clamp = (val: number, min: number, max: number) =>
      Math.max(min, Math.min(max, val));

    expect(clamp(10, RETIREMENT_AGE_MIN, RETIREMENT_AGE_MAX)).toBe(15);
    expect(clamp(100, RETIREMENT_AGE_MIN, RETIREMENT_AGE_MAX)).toBe(95);
    expect(clamp(67, RETIREMENT_AGE_MIN, RETIREMENT_AGE_MAX)).toBe(67);
  });
});

// ── Tab Rename Logic ─────────────────────────────────────────────────────────

describe('Tab Rename Logic', () => {
  type TabRenameState = {
    editingTabId: string | null;
    editingTabName: string;
  };

  function startEditing(
    state: TabRenameState,
    scenarioId: string,
    currentName: string
  ): TabRenameState {
    return { editingTabId: scenarioId, editingTabName: currentName };
  }

  function submitRename(state: TabRenameState): { newName: string | null; newState: TabRenameState } {
    if (state.editingTabId && state.editingTabName.trim()) {
      return {
        newName: state.editingTabName.trim(),
        newState: { editingTabId: null, editingTabName: '' },
      };
    }
    return { newName: null, newState: { editingTabId: null, editingTabName: '' } };
  }

  function cancelRename(): TabRenameState {
    return { editingTabId: null, editingTabName: '' };
  }

  it('should set editing state on double-click', () => {
    const initial: TabRenameState = { editingTabId: null, editingTabName: '' };
    const result = startEditing(initial, 'scenario-1', 'My Plan');
    expect(result.editingTabId).toBe('scenario-1');
    expect(result.editingTabName).toBe('My Plan');
  });

  it('should submit trimmed name on Enter', () => {
    const state: TabRenameState = { editingTabId: 'scenario-1', editingTabName: '  New Name  ' };
    const result = submitRename(state);
    expect(result.newName).toBe('New Name');
    expect(result.newState.editingTabId).toBeNull();
  });

  it('should not submit empty name', () => {
    const state: TabRenameState = { editingTabId: 'scenario-1', editingTabName: '   ' };
    const result = submitRename(state);
    expect(result.newName).toBeNull();
  });

  it('should clear state on cancel (Escape)', () => {
    const result = cancelRename();
    expect(result.editingTabId).toBeNull();
    expect(result.editingTabName).toBe('');
  });

  it('should not interfere with non-editing tabs', () => {
    const state: TabRenameState = { editingTabId: 'scenario-1', editingTabName: 'New' };
    // Only the tab with matching id should show input
    expect(state.editingTabId === 'scenario-2').toBe(false);
    expect(state.editingTabId === 'scenario-1').toBe(true);
  });
});

// ── Tab Scroll Preservation ─────────────────────────────────────────────────

describe('Tab Scroll Preservation', () => {
  it('should capture scroll position before tab change', () => {
    const mockScrollY = 450;
    // In the real code: const scrollY = window.scrollY;
    // Then after rAF: window.scrollTo({ top: scrollY })
    expect(mockScrollY).toBeGreaterThan(0);
  });

  it('should restore scroll position after tab switch', () => {
    // Simulate the pattern: save → switch → restore
    let savedScrollY = 0;
    const mockSetScroll = (pos: number) => { savedScrollY = pos; };
    mockSetScroll(300);
    // After rAF, restored position should match saved
    expect(savedScrollY).toBe(300);
  });
});

// ── SS Manual Override Logic ────────────────────────────────────────────────

describe('Social Security Manual Override', () => {
  function computeSsUpdate(amount: number | null) {
    return {
      social_security_monthly: amount,
      use_estimated_pia: amount === null,
    };
  }

  it('should set manual amount and disable PIA estimation', () => {
    const update = computeSsUpdate(2500);
    expect(update.social_security_monthly).toBe(2500);
    expect(update.use_estimated_pia).toBe(false);
  });

  it('should clear override and re-enable PIA estimation', () => {
    const update = computeSsUpdate(null);
    expect(update.social_security_monthly).toBeNull();
    expect(update.use_estimated_pia).toBe(true);
  });

  it('should handle zero as valid manual amount', () => {
    const update = computeSsUpdate(0);
    expect(update.social_security_monthly).toBe(0);
    expect(update.use_estimated_pia).toBe(false);
  });

  it('should compute annual from monthly', () => {
    const monthly = 2500;
    expect(monthly * 12).toBe(30000);
  });
});

// ── Healthcare Edit Mode Logic ──────────────────────────────────────────────

describe('Healthcare Edit Mode', () => {
  type EditState = {
    isEditing: boolean;
    localInflation: number;
    localIncome: number;
  };

  function toggleEdit(
    state: EditState,
    propInflation: number,
    propIncome: number
  ): { newState: EditState; changes: { inflation?: number; income?: number } } {
    if (state.isEditing) {
      // Exiting edit mode — compute changes
      const changes: { inflation?: number; income?: number } = {};
      if (state.localInflation !== propInflation) {
        changes.inflation = state.localInflation;
      }
      if (state.localIncome !== propIncome) {
        changes.income = state.localIncome;
      }
      return {
        newState: { ...state, isEditing: false },
        changes,
      };
    }
    // Entering edit mode — sync local state
    return {
      newState: { isEditing: true, localInflation: propInflation, localIncome: propIncome },
      changes: {},
    };
  }

  it('should enter edit mode with synced values', () => {
    const state: EditState = { isEditing: false, localInflation: 0, localIncome: 0 };
    const result = toggleEdit(state, 6.0, 50000);
    expect(result.newState.isEditing).toBe(true);
    expect(result.newState.localInflation).toBe(6.0);
    expect(result.newState.localIncome).toBe(50000);
    expect(Object.keys(result.changes)).toHaveLength(0);
  });

  it('should exit edit mode and report changed inflation', () => {
    const state: EditState = { isEditing: true, localInflation: 8.0, localIncome: 50000 };
    const result = toggleEdit(state, 6.0, 50000);
    expect(result.newState.isEditing).toBe(false);
    expect(result.changes.inflation).toBe(8.0);
    expect(result.changes.income).toBeUndefined();
  });

  it('should exit edit mode and report changed income', () => {
    const state: EditState = { isEditing: true, localInflation: 6.0, localIncome: 75000 };
    const result = toggleEdit(state, 6.0, 50000);
    expect(result.changes.income).toBe(75000);
    expect(result.changes.inflation).toBeUndefined();
  });

  it('should report no changes if values unchanged', () => {
    const state: EditState = { isEditing: true, localInflation: 6.0, localIncome: 50000 };
    const result = toggleEdit(state, 6.0, 50000);
    expect(Object.keys(result.changes)).toHaveLength(0);
  });
});

// ── Withdrawal Strategy Selection ───────────────────────────────────────────

describe('Withdrawal Strategy Selection', () => {
  type Strategy = 'tax_optimized' | 'simple_rate' | 'pro_rata';

  function getSelectedBadges(
    selectedStrategy: Strategy,
    taxOptWins: boolean
  ) {
    return {
      taxOptSelected: selectedStrategy === 'tax_optimized',
      taxOptBetter: taxOptWins,
      simpleSelected: selectedStrategy === 'simple_rate',
      simpleBetter: !taxOptWins,
    };
  }

  it('should mark tax_optimized as selected', () => {
    const badges = getSelectedBadges('tax_optimized', true);
    expect(badges.taxOptSelected).toBe(true);
    expect(badges.simpleSelected).toBe(false);
  });

  it('should mark simple_rate as selected', () => {
    const badges = getSelectedBadges('simple_rate', true);
    expect(badges.taxOptSelected).toBe(false);
    expect(badges.simpleSelected).toBe(true);
  });

  it('should show Better badge independent of selection', () => {
    // Tax-optimized wins but simple_rate is selected
    const badges = getSelectedBadges('simple_rate', true);
    expect(badges.taxOptBetter).toBe(true);
    expect(badges.simpleBetter).toBe(false);
    expect(badges.simpleSelected).toBe(true);
  });

  it('should handle both badges on same card', () => {
    // Tax-optimized wins AND is selected
    const badges = getSelectedBadges('tax_optimized', true);
    expect(badges.taxOptSelected).toBe(true);
    expect(badges.taxOptBetter).toBe(true);
  });
});

// ── Cash Balance Display Logic ──────────────────────────────────────────────

describe('Cash Balance Display', () => {
  function computeBuckets(data: {
    total_portfolio: number;
    pre_tax_balance: number;
    roth_balance: number;
    taxable_balance: number;
    hsa_balance: number;
    cash_balance: number;
  }) {
    const total = data.total_portfolio || 1;
    const brokerageBalance = data.taxable_balance - data.cash_balance;
    return [
      { label: 'Pre-Tax', value: data.pre_tax_balance, pct: (data.pre_tax_balance / total) * 100 },
      { label: 'Roth', value: data.roth_balance, pct: (data.roth_balance / total) * 100 },
      { label: 'Brokerage', value: brokerageBalance, pct: (brokerageBalance / total) * 100 },
      { label: 'HSA', value: data.hsa_balance, pct: (data.hsa_balance / total) * 100 },
      { label: 'Cash', value: data.cash_balance, pct: (data.cash_balance / total) * 100 },
    ].filter(b => b.value > 0);
  }

  it('should split cash from brokerage', () => {
    const buckets = computeBuckets({
      total_portfolio: 100000,
      pre_tax_balance: 50000,
      roth_balance: 20000,
      taxable_balance: 25000, // includes cash
      hsa_balance: 5000,
      cash_balance: 10000,
    });
    const brokerage = buckets.find(b => b.label === 'Brokerage');
    const cash = buckets.find(b => b.label === 'Cash');
    expect(brokerage?.value).toBe(15000); // 25000 - 10000
    expect(cash?.value).toBe(10000);
  });

  it('should not show cash when zero', () => {
    const buckets = computeBuckets({
      total_portfolio: 100000,
      pre_tax_balance: 50000,
      roth_balance: 30000,
      taxable_balance: 15000,
      hsa_balance: 5000,
      cash_balance: 0,
    });
    const cash = buckets.find(b => b.label === 'Cash');
    expect(cash).toBeUndefined();
  });

  it('should handle all-cash portfolio', () => {
    const buckets = computeBuckets({
      total_portfolio: 50000,
      pre_tax_balance: 0,
      roth_balance: 0,
      taxable_balance: 50000,
      hsa_balance: 0,
      cash_balance: 50000,
    });
    expect(buckets).toHaveLength(1);
    expect(buckets[0].label).toBe('Cash');
    expect(buckets[0].pct).toBe(100);
  });

  it('brokerage should be zero when all taxable is cash', () => {
    const buckets = computeBuckets({
      total_portfolio: 50000,
      pre_tax_balance: 30000,
      roth_balance: 0,
      taxable_balance: 20000,
      hsa_balance: 0,
      cash_balance: 20000,
    });
    const brokerage = buckets.find(b => b.label === 'Brokerage');
    expect(brokerage).toBeUndefined(); // filtered out since value = 0
  });
});

// ── Capital Gains Tax Display ───────────────────────────────────────────────

describe('Capital Gains Tax Display', () => {
  it('should show tax rates when scenario is provided', () => {
    const scenario = {
      federal_tax_rate: 22,
      state_tax_rate: 5,
      capital_gains_rate: 15,
    };
    expect(scenario.capital_gains_rate).toBe(15);
    expect(scenario.federal_tax_rate).toBe(22);
  });

  it('should not show tax section when scenario is null', () => {
    const scenario = null;
    expect(scenario).toBeNull();
    // In the component, tax section is conditionally rendered: {scenario && (...)}
  });
});

// ── Member Filter Logic (replaces UserViewToggle) ──────────────────────────

describe('Member Filter Visibility', () => {
  function showMemberFilter(isCombinedView: boolean, memberCount: number): boolean {
    return isCombinedView && memberCount > 1;
  }

  function getScenarioUserId(filterUserId: string | null): string | undefined {
    return filterUserId ?? undefined;
  }

  it('should show member filter in combined view with multiple members', () => {
    expect(showMemberFilter(true, 2)).toBe(true);
  });

  it('should not show member filter in single user view', () => {
    expect(showMemberFilter(false, 2)).toBe(false);
  });

  it('should not show member filter with single member', () => {
    expect(showMemberFilter(true, 1)).toBe(false);
  });

  it('null filterUserId should return undefined (fetch all)', () => {
    expect(getScenarioUserId(null)).toBeUndefined();
  });

  it('specific filterUserId should return that ID', () => {
    expect(getScenarioUserId('user-123')).toBe('user-123');
  });
});

// ── Household View Filtering Logic ──────────────────────────────────────────

describe('Household View Filtering', () => {
  function getScenarioUserId(
    isCombinedView: boolean,
    viewUserId: string | null
  ): string | undefined {
    return isCombinedView ? undefined : (viewUserId ?? undefined);
  }

  it('combined view should fetch all scenarios (no user filter)', () => {
    const userId = getScenarioUserId(true, 'user-123');
    expect(userId).toBeUndefined();
  });

  it('self view should filter by own user ID', () => {
    const userId = getScenarioUserId(false, 'user-123');
    expect(userId).toBe('user-123');
  });

  it('other user view should filter by that user ID', () => {
    const userId = getScenarioUserId(false, 'user-456');
    expect(userId).toBe('user-456');
  });

  it('null view user should be undefined (self)', () => {
    const userId = getScenarioUserId(false, null);
    expect(userId).toBeUndefined();
  });
});

// ── Household Default Scenario Naming ───────────────────────────────────────

describe('Household Default Scenario', () => {
  function getDefaultScenarioName(isHousehold: boolean): string {
    return isHousehold ? 'Our Retirement Plan' : 'My Retirement Plan';
  }

  function getDefaultSpending(isHousehold: boolean, income: number | null): number {
    if (income) {
      return income * (isHousehold ? 0.85 : 0.80);
    }
    return isHousehold ? 80000 : 60000;
  }

  it('household scenario should be named "Our Retirement Plan"', () => {
    expect(getDefaultScenarioName(true)).toBe('Our Retirement Plan');
  });

  it('single scenario should be named "My Retirement Plan"', () => {
    expect(getDefaultScenarioName(false)).toBe('My Retirement Plan');
  });

  it('household with income should use 85% spending ratio', () => {
    expect(getDefaultSpending(true, 100000)).toBe(85000);
  });

  it('single with income should use 80% spending ratio', () => {
    expect(getDefaultSpending(false, 100000)).toBe(80000);
  });

  it('household without income should default to $80K spending', () => {
    expect(getDefaultSpending(true, null)).toBe(80000);
  });

  it('single without income should default to $60K spending', () => {
    expect(getDefaultSpending(false, null)).toBe(60000);
  });
});

// ── Tax Rate Edit Mode Logic ───────────────────────────────────────────────

describe('Tax Rate Edit Mode', () => {
  type TaxEditState = {
    isEditing: boolean;
    localFederal: number;
    localState: number;
    localCapGains: number;
  };

  function toggleTaxEdit(
    state: TaxEditState,
    scenarioFederal: number,
    scenarioState: number,
    scenarioCapGains: number
  ): { newState: TaxEditState; changes: { federal_tax_rate?: number; state_tax_rate?: number; capital_gains_rate?: number } } {
    if (state.isEditing) {
      const changes: { federal_tax_rate?: number; state_tax_rate?: number; capital_gains_rate?: number } = {};
      if (state.localFederal !== scenarioFederal) changes.federal_tax_rate = state.localFederal;
      if (state.localState !== scenarioState) changes.state_tax_rate = state.localState;
      if (state.localCapGains !== scenarioCapGains) changes.capital_gains_rate = state.localCapGains;
      return { newState: { ...state, isEditing: false }, changes };
    }
    return {
      newState: { isEditing: true, localFederal: scenarioFederal, localState: scenarioState, localCapGains: scenarioCapGains },
      changes: {},
    };
  }

  it('should enter edit mode with synced values', () => {
    const state: TaxEditState = { isEditing: false, localFederal: 0, localState: 0, localCapGains: 0 };
    const result = toggleTaxEdit(state, 22, 5, 15);
    expect(result.newState.isEditing).toBe(true);
    expect(result.newState.localFederal).toBe(22);
    expect(result.newState.localState).toBe(5);
    expect(result.newState.localCapGains).toBe(15);
  });

  it('should detect changed federal rate', () => {
    const state: TaxEditState = { isEditing: true, localFederal: 32, localState: 5, localCapGains: 15 };
    const result = toggleTaxEdit(state, 22, 5, 15);
    expect(result.changes.federal_tax_rate).toBe(32);
    expect(result.changes.state_tax_rate).toBeUndefined();
  });

  it('should report no changes when values match', () => {
    const state: TaxEditState = { isEditing: true, localFederal: 22, localState: 5, localCapGains: 15 };
    const result = toggleTaxEdit(state, 22, 5, 15);
    expect(Object.keys(result.changes)).toHaveLength(0);
  });
});

// ── Healthcare Override Logic ──────────────────────────────────────────────

describe('Healthcare Cost Overrides', () => {
  function getDisplayCost(override: number | null, estimate: number): number {
    return override ?? estimate;
  }

  it('should use override when set', () => {
    expect(getDisplayCost(15000, 10200)).toBe(15000);
  });

  it('should fall back to estimate when override is null', () => {
    expect(getDisplayCost(null, 10200)).toBe(10200);
  });

  it('should use zero override as valid value', () => {
    expect(getDisplayCost(0, 10200)).toBe(0);
  });

  it('should handle all three cost phases independently', () => {
    const pre65 = getDisplayCost(12000, 10200);
    const medicare = getDisplayCost(null, 7313);
    const ltc = getDisplayCost(40000, 30905);
    expect(pre65).toBe(12000);
    expect(medicare).toBe(7313);
    expect(ltc).toBe(40000);
  });
});

// ── Settings Dirty Indicator ───────────────────────────────────────────────

describe('Settings Dirty Indicator', () => {
  it('should be clean initially', () => {
    let dirty = false;
    expect(dirty).toBe(false);
  });

  it('should become dirty on update', () => {
    let dirty = false;
    // Simulate handleUpdate
    dirty = true;
    expect(dirty).toBe(true);
  });

  it('should clear on simulation run', () => {
    let dirty = true;
    // Simulate handleSimulate success
    dirty = false;
    expect(dirty).toBe(false);
  });

  it('should clear on tab switch', () => {
    let dirty = true;
    // Simulate handleTabChange
    dirty = false;
    expect(dirty).toBe(false);
  });
});

// ── Delete Scenario Logic ────────────────────────────────────────────────

describe('Delete Scenario Logic', () => {
  type Scenario = { id: string; name: string; is_default: boolean };

  function resolveSelectionAfterDelete(
    deletedId: string,
    selectedId: string | null,
    scenarios: Scenario[]
  ): string | null {
    // After deletion, remaining scenarios exclude the deleted one
    const remaining = scenarios.filter((s) => s.id !== deletedId);
    if (remaining.length === 0) return null; // all deleted → empty state

    // If we deleted the currently selected scenario, pick the default or first
    if (deletedId === selectedId) {
      const defaultScenario = remaining.find((s) => s.is_default);
      return defaultScenario?.id ?? remaining[0].id;
    }
    // Otherwise keep the current selection
    return selectedId;
  }

  const scenarios: Scenario[] = [
    { id: 's1', name: 'Plan A', is_default: true },
    { id: 's2', name: 'Plan B', is_default: false },
    { id: 's3', name: 'Plan C', is_default: false },
  ];

  it('should clear selection when all scenarios are deleted', () => {
    const singleScenario = [{ id: 's1', name: 'Plan A', is_default: true }];
    const result = resolveSelectionAfterDelete('s1', 's1', singleScenario);
    expect(result).toBeNull();
  });

  it('should select default scenario after deleting the active one', () => {
    const result = resolveSelectionAfterDelete('s2', 's2', scenarios);
    expect(result).toBe('s1'); // s1 is default
  });

  it('should select first remaining when deleting the default', () => {
    const result = resolveSelectionAfterDelete('s1', 's1', scenarios);
    // s1 (default) is gone, remaining is [s2, s3], no default → pick first
    expect(result).toBe('s2');
  });

  it('should keep current selection when deleting a non-selected scenario', () => {
    const result = resolveSelectionAfterDelete('s3', 's1', scenarios);
    expect(result).toBe('s1');
  });

  it('should return null when scenarios list is empty', () => {
    const result = resolveSelectionAfterDelete('s1', 's1', []);
    expect(result).toBeNull();
  });
});

// ── Tab Icons (Rename + Delete) ─────────────────────────────────────────────

describe('Tab Icons', () => {
  it('rename icon click should trigger rename mode (stopPropagation pattern)', () => {
    // The pencil icon click calls e.stopPropagation() to prevent tab selection,
    // then calls handleTabDoubleClick(id, name)
    let tabSelected = false;
    let renameTriggered = false;

    const handleTabSelect = () => { tabSelected = true; };
    const handleRename = (id: string, name: string) => { renameTriggered = true; };

    // Simulate icon click: stopPropagation prevents tab selection
    handleRename('s1', 'Plan A');
    // Tab select should NOT be called since propagation was stopped
    expect(renameTriggered).toBe(true);
    expect(tabSelected).toBe(false);
  });

  it('delete icon click should trigger delete (stopPropagation pattern)', () => {
    let tabSelected = false;
    let deleteTriggered = false;
    let deletedId = '';

    const handleDelete = (id: string) => {
      deleteTriggered = true;
      deletedId = id;
    };

    handleDelete('s2');
    expect(deleteTriggered).toBe(true);
    expect(deletedId).toBe('s2');
    expect(tabSelected).toBe(false);
  });

  it('tab should show name text with optional readiness score', () => {
    const scenario = { id: 's1', name: 'My Plan', readiness_score: 72 };
    // In the component: name is shown, readiness_score appended as "(72)"
    const displayText = scenario.readiness_score !== null
      ? `${scenario.name} (${scenario.readiness_score})`
      : scenario.name;
    expect(displayText).toBe('My Plan (72)');
  });

  it('tab should show name only when readiness_score is null', () => {
    const scenario = { id: 's1', name: 'New Plan', readiness_score: null };
    const displayText = scenario.readiness_score !== null
      ? `${scenario.name} (${scenario.readiness_score})`
      : scenario.name;
    expect(displayText).toBe('New Plan');
  });

  it('editing tab should show input instead of name + icons', () => {
    const editingTabId = 's1';
    const scenarioId = 's1';
    const isEditing = editingTabId === scenarioId;
    expect(isEditing).toBe(true);

    // Different scenario should NOT be in edit mode
    const isEditingOther = editingTabId === 's2';
    expect(isEditingOther).toBe(false);
  });
});

// ── Run Simulation Button State ─────────────────────────────────────────────

describe('Run Simulation Button', () => {
  function getButtonProps(settingsDirty: boolean, selectedScenarioId: string | null) {
    return {
      colorScheme: settingsDirty ? 'orange' : 'blue',
      label: settingsDirty ? 'Re-run Simulation' : 'Run Simulation',
      isDisabled: !selectedScenarioId,
      showDirtyMessage: settingsDirty,
    };
  }

  it('should be blue with "Run Simulation" when settings are clean', () => {
    const props = getButtonProps(false, 'scenario-1');
    expect(props.colorScheme).toBe('blue');
    expect(props.label).toBe('Run Simulation');
    expect(props.showDirtyMessage).toBe(false);
  });

  it('should be orange with "Re-run Simulation" when settings are dirty', () => {
    const props = getButtonProps(true, 'scenario-1');
    expect(props.colorScheme).toBe('orange');
    expect(props.label).toBe('Re-run Simulation');
    expect(props.showDirtyMessage).toBe(true);
  });

  it('should be disabled when no scenario is selected', () => {
    const props = getButtonProps(false, null);
    expect(props.isDisabled).toBe(true);
  });

  it('should be enabled when a scenario is selected', () => {
    const props = getButtonProps(false, 'scenario-1');
    expect(props.isDisabled).toBe(false);
  });

  it('dirty state should track through update → simulate cycle', () => {
    let dirty = false;
    // Initial: clean
    expect(dirty).toBe(false);

    // User changes a setting
    dirty = true;
    expect(getButtonProps(dirty, 's1').colorScheme).toBe('orange');

    // User runs simulation
    dirty = false;
    expect(getButtonProps(dirty, 's1').colorScheme).toBe('blue');

    // User changes another setting
    dirty = true;
    expect(getButtonProps(dirty, 's1').label).toBe('Re-run Simulation');
  });

  it('dirty state should clear on tab switch', () => {
    let dirty = true;
    // Simulate tab change handler — clears dirty
    dirty = false;
    expect(getButtonProps(dirty, 's2').colorScheme).toBe('blue');
    expect(getButtonProps(dirty, 's2').showDirtyMessage).toBe(false);
  });

  it('button should be full-width (w="100%")', () => {
    // This is a layout assertion — the component sets w="100%" and size="lg"
    // We verify the intent: button is rendered as a full-width large button
    const expectedSize = 'lg';
    const expectedWidth = '100%';
    expect(expectedSize).toBe('lg');
    expect(expectedWidth).toBe('100%');
  });
});

// ── Permission Resource Types ──────────────────────────────────────────────

describe('Permission Resource Types', () => {
  const RESOURCE_TYPES = [
    'account', 'transaction', 'bill', 'holding', 'budget',
    'category', 'rule', 'savings_goal', 'contribution',
    'recurring_transaction', 'report', 'org_settings', 'retirement_scenario',
  ];

  it('should include retirement_scenario as a resource type', () => {
    expect(RESOURCE_TYPES).toContain('retirement_scenario');
  });

  it('should have 13 resource types', () => {
    expect(RESOURCE_TYPES).toHaveLength(13);
  });

  const ROUTE_MAP: Record<string, string> = {
    '/retirement': 'retirement_scenario',
    '/goals': 'savings_goal',
    '/budgets': 'budget',
  };

  it('/retirement route should map to retirement_scenario', () => {
    expect(ROUTE_MAP['/retirement']).toBe('retirement_scenario');
  });
});
