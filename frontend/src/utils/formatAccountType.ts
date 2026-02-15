/**
 * Format account type for display
 * Converts snake_case to Title Case with overrides for special cases
 */

export const formatAccountType = (accountType: string): string => {
  // Special case overrides that don't follow the standard pattern
  const overrides: Record<string, string> = {
    'retirement_401k': '401(k)',
    'retirement_ira': 'IRA',
    'retirement_roth': 'Roth IRA',
    'retirement_529': '529 Plan',
    'hsa': 'HSA',
    'cd': 'CD',
  };

  // Check if there's an override
  if (overrides[accountType]) {
    return overrides[accountType];
  }

  // Default: Convert snake_case to Title Case
  // e.g., 'money_market' -> 'Money Market'
  // e.g., 'student_loan' -> 'Student Loan'
  return accountType
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};
