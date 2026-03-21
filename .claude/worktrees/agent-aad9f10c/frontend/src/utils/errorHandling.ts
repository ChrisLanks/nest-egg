/**
 * Shared error handling utilities for API error responses.
 */

const GENERIC_ERROR = "An error occurred";

/**
 * Sanitize an error message so it is safe to display to the user.
 *
 * Strips anything that looks like an internal stack trace, file path,
 * or excessively long detail string that the backend might leak in an
 * unhandled error scenario.  The goal is defence-in-depth — the backend
 * ErrorHandlerMiddleware already returns a generic message for unhandled
 * exceptions in production, but this protects against regressions.
 */
const sanitize = (msg: string): string => {
  // Reject messages that look like stack traces or file paths
  if (/Traceback|File ".*\.py"|at .*\(.*:\d+:\d+\)|node_modules/.test(msg)) {
    return GENERIC_ERROR;
  }
  // Cap length — legitimate user-facing messages are short
  if (msg.length > 300) {
    return GENERIC_ERROR;
  }
  return msg;
};

/**
 * Safely extract a string message from an API error response.
 * Some endpoints (e.g. the rate limiter) return detail as an object
 * { message, retry_after } — passing that object to a Chakra toast
 * description crashes React ("Objects are not valid as a React child").
 */
export const getErrorMessage = (error: any): string => {
  const detail = error?.response?.data?.detail;
  if (!detail) return GENERIC_ERROR;
  if (typeof detail === "object") {
    const msg = (detail as any).message;
    return msg ? sanitize(String(msg)) : GENERIC_ERROR;
  }
  return sanitize(String(detail));
};

/**
 * Validate that a URL token/code has a safe format before sending to the API.
 *
 * Accepts base64url tokens (from secrets.token_urlsafe), UUIDs, and short
 * alphanumeric codes.  Rejects anything that contains whitespace, angle
 * brackets, or other injection-prone characters.
 *
 * This is a lightweight client-side guard — the backend always validates
 * tokens independently.  Returns true if the format looks plausible.
 */
export const isValidTokenFormat = (token: string): boolean => {
  if (!token || token.length > 512) return false;
  // Allow base64url, hex, UUIDs, and alphanumeric codes
  return /^[A-Za-z0-9_\-=.]+$/.test(token);
};
