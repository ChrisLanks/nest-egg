/**
 * Chakra UI theme customization with dark mode support.
 *
 * Color mode is managed by useColorModePreference (light / dark / system).
 * Semantic tokens auto-switch values so most components need zero imports.
 */

import { extendTheme, type ThemeConfig } from '@chakra-ui/react';

const config: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: false, // managed by useColorModePreference hook
};

const colors = {
  brand: {
    50: '#e3f9e5',
    100: '#c1eac5',
    200: '#a3d9a5',
    300: '#7bc47f',
    400: '#57ae5b',
    500: '#3f9142', // Primary brand color
    600: '#2f8132',
    700: '#207227',
    800: '#0e5814',
    900: '#05400a',
  },
  finance: {
    positive: '#48BB78', // Green for gains
    negative: '#F56565', // Red for losses
    neutral: '#718096', // Gray for neutral
  },
};

const fonts = {
  heading: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  body: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
};

/* ── Semantic tokens ───────────────────────────────────────────────────── */
const semanticTokens = {
  colors: {
    // Surfaces
    'bg.canvas':  { default: 'gray.50',  _dark: 'gray.900' },
    'bg.surface': { default: 'white',    _dark: 'gray.800' },
    'bg.subtle':  { default: 'gray.50',  _dark: 'gray.700' },
    'bg.muted':   { default: 'gray.100', _dark: 'gray.700' },

    // Text
    'text.primary':   { default: 'gray.800', _dark: 'gray.100' },
    'text.secondary': { default: 'gray.600', _dark: 'gray.400' },
    'text.muted':     { default: 'gray.500', _dark: 'gray.500' },
    'text.heading':   { default: 'gray.700', _dark: 'gray.200' },

    // Borders
    'border.default': { default: 'gray.200', _dark: 'gray.600' },
    'border.subtle':  { default: 'gray.100', _dark: 'gray.700' },

    // Finance
    'finance.positive': { default: 'green.600',  _dark: 'green.300' },
    'finance.negative': { default: 'red.600',    _dark: 'red.300' },
    'finance.neutral':  { default: 'gray.600',   _dark: 'gray.400' },

    // Brand accent (readable on surface)
    'brand.accent': { default: 'brand.600', _dark: 'brand.300' },
    'brand.subtle': { default: 'brand.50',  _dark: 'brand.900' },

    // Status tint backgrounds
    'bg.info':    { default: 'blue.50',   _dark: 'blue.900' },
    'bg.success': { default: 'green.50',  _dark: 'green.900' },
    'bg.warning': { default: 'orange.50', _dark: 'orange.900' },
    'bg.error':   { default: 'red.50',    _dark: 'red.900' },
  },
};

/* ── Component style overrides ─────────────────────────────────────────── */
const components = {
  Button: {
    defaultProps: {
      colorScheme: 'brand',
    },
  },
  Card: {
    baseStyle: {
      container: {
        bg: 'bg.surface',
        borderColor: 'border.default',
      },
    },
  },
  Modal: {
    baseStyle: {
      dialog: {
        bg: 'bg.surface',
      },
    },
  },
  Drawer: {
    baseStyle: {
      dialog: {
        bg: 'bg.surface',
      },
    },
  },
  Table: {
    baseStyle: {
      th: { borderColor: 'border.default' },
      td: { borderColor: 'border.default' },
    },
  },
  Divider: {
    baseStyle: {
      borderColor: 'border.default',
    },
  },
  Menu: {
    baseStyle: {
      list: {
        bg: 'bg.surface',
        borderColor: 'border.default',
      },
      item: {
        bg: 'bg.surface',
        _hover: { bg: 'bg.subtle' },
      },
    },
  },
  Popover: {
    baseStyle: {
      content: {
        bg: 'bg.surface',
        borderColor: 'border.default',
      },
    },
  },
  Tooltip: {
    baseStyle: {
      bg: 'bg.surface',
      color: 'text.primary',
      borderColor: 'border.default',
    },
  },
};

export const theme = extendTheme({
  config,
  colors,
  fonts,
  semanticTokens,
  components,
  styles: {
    global: {
      body: {
        bg: 'bg.canvas',
        color: 'text.primary',
      },
    },
  },
});
