/**
 * Shared error handling utilities for API error responses.
 */

/**
 * Safely extract a string message from an API error response.
 * Some endpoints (e.g. the rate limiter) return detail as an object
 * { message, retry_after } — passing that object to a Chakra toast
 * description crashes React ("Objects are not valid as a React child").
 */
export const getErrorMessage = (error: any): string => {
  const detail = error?.response?.data?.detail;
  if (!detail) return "An error occurred";
  if (typeof detail === "object")
    return (detail as any).message || "An error occurred";
  return String(detail);
};
