/**
 * Age thresholds used across the frontend.
 * Mirrors backend app/constants/financial.py RETIREMENT class.
 */

/** Age at which 401k/IRA catch-up contributions become available (IRS). */
export const CATCH_UP_AGE_401K = 50;

/** Age at which HSA catch-up contributions become available (IRS). */
export const CATCH_UP_AGE_HSA = 55;

/** Age at which SECURE 2.0 super catch-up (401k) begins. */
export const CATCH_UP_AGE_SUPER_401K_START = 60;

/** Age at which SECURE 2.0 super catch-up (401k) ends. */
export const CATCH_UP_AGE_SUPER_401K_END = 63;

/** Minimum age to begin Social Security claiming. */
export const SS_MIN_CLAIMING_AGE = 62;

/** Maximum age for Social Security delayed credits. */
export const SS_MAX_CLAIMING_AGE = 70;

/** Minimum age at which the Social Security estimator/planner is shown. */
export const SS_SHOW_AGE = 50;

/** Age at which the full Social Security retirement section is shown. */
export const SS_RETIREMENT_SHOW_AGE = 55;
