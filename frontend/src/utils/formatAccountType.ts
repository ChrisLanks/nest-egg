/**
 * Format account type for display
 * Converts snake_case to Title Case with overrides for special cases
 */

export const formatAccountType = (accountType: string, taxTreatment?: string | null): string => {
  // When tax_treatment is known, produce a more specific label
  if (taxTreatment === 'roth') {
    if (accountType === 'retirement_401k') return 'Roth 401(k)';
    if (accountType === 'retirement_403b') return 'Roth 403(b)';
    if (accountType === 'retirement_457b') return 'Roth 457(b)';
    if (accountType === 'retirement_ira') return 'Roth IRA';
  }

  // Special case overrides that don't follow the standard pattern
  const overrides: Record<string, string> = {
    'retirement_401k': '401(k)',
    'retirement_403b': '403(b)',
    'retirement_457b': '457(b)',
    'retirement_ira': 'IRA',
    'retirement_roth': 'Roth IRA',
    'retirement_sep_ira': 'SEP IRA',
    'retirement_simple_ira': 'SIMPLE IRA',
    'retirement_529': '529 Plan',
    'hsa': 'HSA',
    'cd': 'CD',
  };

  // Check if there's an override
  const base = overrides[accountType];
  if (base) {
    // Append "(Traditional)" for pre-tax retirement accounts
    if (taxTreatment === 'pre_tax' && ['retirement_401k', 'retirement_403b', 'retirement_457b', 'retirement_ira'].includes(accountType)) {
      return `${base} (Traditional)`;
    }
    return base;
  }

  // Default: Convert snake_case to Title Case
  return accountType
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};
