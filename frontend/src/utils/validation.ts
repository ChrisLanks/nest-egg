/**
 * Shared validation utilities.
 */

export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(email: string): {
  valid: boolean;
  error: string;
} {
  if (!email) {
    return { valid: false, error: "Email is required" };
  }
  if (!EMAIL_REGEX.test(email)) {
    return { valid: false, error: "Invalid email address" };
  }
  return { valid: true, error: "" };
}
