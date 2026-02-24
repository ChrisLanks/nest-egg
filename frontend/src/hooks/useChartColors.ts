/**
 * Shared chart color values that adapt to light/dark mode.
 *
 * Data fill colors (green, red, blue, etc.) are vibrant enough for both
 * modes and do NOT need switching. Only structural colors change.
 */

import { useColorModeValue } from '@chakra-ui/react';

export function useChartColors() {
  return {
    tooltipBg: useColorModeValue('#FFFFFF', '#2D3748'),
    tooltipBorder: useColorModeValue('#E2E8F0', '#4A5568'),
    gridStroke: useColorModeValue('#E2E8F0', '#4A5568'),
    axisStroke: useColorModeValue('#718096', '#A0AEC0'),
    labelColor: useColorModeValue('#4A5568', '#A0AEC0'),
    alternateRowBg: useColorModeValue('#F7FAFC', '#2D3748'),
  };
}
