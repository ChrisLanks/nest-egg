/**
 * useLocalStorage — persist a state value in localStorage.
 *
 * Drop-in replacement for useState that survives page refreshes.
 * Safe: falls back to the initialValue if localStorage is unavailable
 * or the stored value cannot be parsed.
 */

import { useCallback, useState } from "react";

export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = localStorage.getItem(key);
      return item !== null ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const next =
          typeof value === "function" ? (value as (prev: T) => T)(prev) : value;
        try {
          localStorage.setItem(key, JSON.stringify(next));
        } catch {
          // localStorage quota exceeded or unavailable — state still updates
        }
        return next;
      });
    },
    [key],
  );

  return [storedValue, setValue];
}
