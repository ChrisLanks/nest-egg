/**
 * Chakra UI theme customization
 */

import { extendTheme, type ThemeConfig } from '@chakra-ui/react';

const config: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: false,
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

const components = {
  Button: {
    defaultProps: {
      colorScheme: 'brand',
    },
  },
};

export const theme = extendTheme({
  config,
  colors,
  fonts,
  components,
  styles: {
    global: {
      body: {
        bg: 'gray.50',
      },
    },
  },
});
