/**
 * Three-way color mode preference: light | dark | system.
 *
 * Wraps Chakra's useColorMode and adds "system" support by listening
 * to the OS prefers-color-scheme media query.
 */

import { useColorMode } from '@chakra-ui/react';
import { useCallback, useEffect, useState } from 'react';

export type ColorModePreference = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'color-mode-preference';

function getStoredPreference(): ColorModePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  } catch {
    // localStorage may be unavailable
  }
  return 'light';
}

function getSystemMode(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function useColorModePreference() {
  const { colorMode, setColorMode } = useColorMode();
  const [preference, setPreferenceState] = useState<ColorModePreference>(getStoredPreference);

  // Sync Chakra's color mode when preference or system theme changes
  useEffect(() => {
    const target = preference === 'system' ? getSystemMode() : preference;
    if (colorMode !== target) setColorMode(target);
  }, [preference]); // eslint-disable-line react-hooks/exhaustive-deps

  // Listen to OS theme changes when in "system" mode
  useEffect(() => {
    if (preference !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => setColorMode(e.matches ? 'dark' : 'light');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [preference, setColorMode]);

  const setPreference = useCallback(
    (pref: ColorModePreference) => {
      setPreferenceState(pref);
      try { localStorage.setItem(STORAGE_KEY, pref); } catch { /* noop */ }
      const target = pref === 'system' ? getSystemMode() : pref;
      setColorMode(target);
    },
    [setColorMode],
  );

  return { preference, setPreference, effectiveMode: colorMode } as const;
}
