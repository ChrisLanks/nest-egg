/**
 * Tests for dark-mode contrast fixes across multiple pages/widgets.
 *
 * Verifies that color-selection logic uses dark-mode-aware values
 * (semantic tokens or light/dark pairs) rather than hardcoded light-only
 * colors like blue.50, green.700, etc.
 */

import { describe, it, expect } from 'vitest';

// ── UpcomingBillsWidget — urgency badge colors ────────────────────────────────

type UpcomingBill = {
  is_overdue: boolean;
  days_until_due: number;
};

/**
 * Mirrors the urgencyProps logic from UpcomingBillsWidget.
 * isDark = useColorModeValue(false, true)
 */
const urgencyProps = (
  bill: UpcomingBill,
  isDark: boolean
): { badge: string; color: string; bg: string } => {
  if (bill.is_overdue)
    return { badge: 'Overdue', color: isDark ? 'red.200' : 'red.700', bg: isDark ? 'red.900' : 'red.50' };
  if (bill.days_until_due <= 3)
    return {
      badge: `${bill.days_until_due}d`,
      color: isDark ? 'orange.200' : 'orange.700',
      bg: isDark ? 'orange.900' : 'orange.50',
    };
  if (bill.days_until_due <= 7)
    return {
      badge: `${bill.days_until_due}d`,
      color: isDark ? 'yellow.200' : 'yellow.700',
      bg: isDark ? 'yellow.900' : 'yellow.50',
    };
  return { badge: `${bill.days_until_due}d`, color: 'text.secondary', bg: 'bg.subtle' };
};

describe('UpcomingBillsWidget — urgency badge dark mode contrast', () => {
  const overdueBill: UpcomingBill = { is_overdue: true, days_until_due: -2 };
  const urgentBill: UpcomingBill = { is_overdue: false, days_until_due: 2 };
  const soonBill: UpcomingBill = { is_overdue: false, days_until_due: 5 };
  const normalBill: UpcomingBill = { is_overdue: false, days_until_due: 14 };

  it('uses light text (.200) on dark backgrounds (.900) in dark mode for overdue', () => {
    const result = urgencyProps(overdueBill, true);
    expect(result.color).toBe('red.200');
    expect(result.bg).toBe('red.900');
  });

  it('uses dark text (.700) on light backgrounds (.50) in light mode for overdue', () => {
    const result = urgencyProps(overdueBill, false);
    expect(result.color).toBe('red.700');
    expect(result.bg).toBe('red.50');
  });

  it('uses orange.200/orange.900 in dark mode for urgent bills (<=3d)', () => {
    const result = urgencyProps(urgentBill, true);
    expect(result.color).toBe('orange.200');
    expect(result.bg).toBe('orange.900');
  });

  it('uses yellow.200/yellow.900 in dark mode for soon bills (<=7d)', () => {
    const result = urgencyProps(soonBill, true);
    expect(result.color).toBe('yellow.200');
    expect(result.bg).toBe('yellow.900');
  });

  it('uses semantic tokens for normal bills regardless of mode', () => {
    const light = urgencyProps(normalBill, false);
    const dark = urgencyProps(normalBill, true);
    expect(light.color).toBe('text.secondary');
    expect(light.bg).toBe('bg.subtle');
    expect(dark.color).toBe('text.secondary');
    expect(dark.bg).toBe('bg.subtle');
  });
});

// ── DebtPayoffPage — card border props ────────────────────────────────────────

type StrategyKey = 'snowball' | 'avalanche' | 'current_pace';

/**
 * Mirrors getCardBorderProps from DebtPayoffPage.
 * Key fix: selected card uses 'bg.info' semantic token instead of 'blue.50'.
 */
const getCardBorderProps = (
  key: StrategyKey,
  effectiveStrategyKey: StrategyKey | null,
  recommendation: string | undefined
) => {
  const KEY_TO_REC: Record<StrategyKey, string> = {
    snowball: 'SNOWBALL',
    avalanche: 'AVALANCHE',
    current_pace: 'CURRENT_PACE',
  };
  const isSel = effectiveStrategyKey === key;
  const isRec = recommendation === KEY_TO_REC[key];
  return {
    borderWidth: isSel || isRec ? 2 : 1,
    borderColor: isSel ? 'blue.500' : isRec ? 'blue.300' : 'border.default',
    bg: isSel ? 'bg.info' : undefined,
  };
};

describe('DebtPayoffPage — selected card uses semantic bg token', () => {
  it('selected card uses bg.info (not blue.50)', () => {
    const props = getCardBorderProps('snowball', 'snowball', undefined);
    expect(props.bg).toBe('bg.info');
  });

  it('non-selected card has no bg override', () => {
    const props = getCardBorderProps('avalanche', 'snowball', undefined);
    expect(props.bg).toBeUndefined();
  });

  it('selected card has blue.500 border and width 2', () => {
    const props = getCardBorderProps('snowball', 'snowball', undefined);
    expect(props.borderColor).toBe('blue.500');
    expect(props.borderWidth).toBe(2);
  });

  it('recommended (but not selected) card has blue.300 border', () => {
    const props = getCardBorderProps('avalanche', 'snowball', 'AVALANCHE');
    expect(props.borderColor).toBe('blue.300');
    expect(props.borderWidth).toBe(2);
    expect(props.bg).toBeUndefined();
  });

  it('non-selected, non-recommended card has default styling', () => {
    const props = getCardBorderProps('current_pace', 'snowball', 'AVALANCHE');
    expect(props.borderColor).toBe('border.default');
    expect(props.borderWidth).toBe(1);
    expect(props.bg).toBeUndefined();
  });
});

// ── DebtPayoffPage — text colors use mode-aware values ────────────────────────

/**
 * Mirrors the useColorModeValue calls in DebtPayoffPage.
 */
const getDebtTextColors = (isDark: boolean) => ({
  infoTextColor: isDark ? 'blue.200' : 'blue.700',
  successTextColor: isDark ? 'green.200' : 'green.700',
  accentColor: isDark ? 'blue.300' : 'blue.600',
  linkColor: isDark ? 'blue.300' : 'blue.500',
});

describe('DebtPayoffPage — text colors are dark-mode aware', () => {
  it('uses light blue/green text (.200) in dark mode', () => {
    const colors = getDebtTextColors(true);
    expect(colors.infoTextColor).toBe('blue.200');
    expect(colors.successTextColor).toBe('green.200');
    expect(colors.accentColor).toBe('blue.300');
    expect(colors.linkColor).toBe('blue.300');
  });

  it('uses dark blue/green text (.700/.600/.500) in light mode', () => {
    const colors = getDebtTextColors(false);
    expect(colors.infoTextColor).toBe('blue.700');
    expect(colors.successTextColor).toBe('green.700');
    expect(colors.accentColor).toBe('blue.600');
    expect(colors.linkColor).toBe('blue.500');
  });

  it('never returns hardcoded green.700 or blue.700 in dark mode', () => {
    const colors = getDebtTextColors(true);
    const values = Object.values(colors);
    expect(values).not.toContain('green.700');
    expect(values).not.toContain('blue.700');
    expect(values).not.toContain('blue.600');
    expect(values).not.toContain('blue.500');
  });
});

// ── BillsPage — RecurringCard backgrounds ─────────────────────────────────────

/**
 * Mirrors the useColorModeValue calls in RecurringCard.
 */
const getRecurringCardColors = (isDark: boolean) => ({
  noLongerFoundBg: isDark ? 'orange.900' : 'orange.50',
  noLongerFoundBorder: isDark ? 'orange.700' : 'orange.200',
  archiveBg: isDark ? 'gray.700' : 'gray.50',
  subtitleColor: isDark ? 'gray.400' : 'gray.600',
});

const getCardBg = (
  isNoLongerFound: boolean,
  isArchiveView: boolean,
  colors: ReturnType<typeof getRecurringCardColors>
) => {
  if (isNoLongerFound) return colors.noLongerFoundBg;
  if (isArchiveView) return colors.archiveBg;
  return 'bg.surface';
};

describe('BillsPage RecurringCard — dark mode backgrounds', () => {
  it('active card uses bg.surface semantic token', () => {
    const colors = getRecurringCardColors(true);
    expect(getCardBg(false, false, colors)).toBe('bg.surface');
  });

  it('"no longer found" card uses orange.900 bg in dark mode', () => {
    const colors = getRecurringCardColors(true);
    expect(getCardBg(true, false, colors)).toBe('orange.900');
  });

  it('"no longer found" card uses orange.50 bg in light mode', () => {
    const colors = getRecurringCardColors(false);
    expect(getCardBg(true, false, colors)).toBe('orange.50');
  });

  it('archived card uses gray.700 bg in dark mode (not gray.50)', () => {
    const colors = getRecurringCardColors(true);
    expect(getCardBg(false, true, colors)).toBe('gray.700');
  });

  it('subtitle uses gray.400 in dark mode for readability', () => {
    const colors = getRecurringCardColors(true);
    expect(colors.subtitleColor).toBe('gray.400');
  });

  it('never uses hardcoded white or gray.50 in dark mode', () => {
    const colors = getRecurringCardColors(true);
    const values = Object.values(colors);
    expect(values).not.toContain('white');
    expect(values).not.toContain('gray.50');
    expect(values).not.toContain('orange.50');
  });
});

// ── RothConversionAnalyzer — banner text colors ───────────────────────────────

const getRothBannerColors = (isDark: boolean) => ({
  successTextColor: isDark ? 'green.200' : 'green.700',
  warningTextColor: isDark ? 'yellow.200' : 'yellow.700',
});

const getRothBannerBg = (isConversionBeneficial: boolean) =>
  isConversionBeneficial ? 'bg.success' : 'bg.warning';

describe('RothConversionAnalyzer — banner dark mode contrast', () => {
  it('beneficial banner uses green.200 text in dark mode', () => {
    const colors = getRothBannerColors(true);
    expect(colors.successTextColor).toBe('green.200');
  });

  it('caution banner uses yellow.200 text in dark mode', () => {
    const colors = getRothBannerColors(true);
    expect(colors.warningTextColor).toBe('yellow.200');
  });

  it('beneficial banner bg uses bg.success semantic token', () => {
    expect(getRothBannerBg(true)).toBe('bg.success');
  });

  it('caution banner bg uses bg.warning semantic token (not yellow.50)', () => {
    expect(getRothBannerBg(false)).toBe('bg.warning');
  });

  it('never returns green.700 or yellow.700 in dark mode', () => {
    const colors = getRothBannerColors(true);
    const values = Object.values(colors);
    expect(values).not.toContain('green.700');
    expect(values).not.toContain('yellow.700');
  });
});
