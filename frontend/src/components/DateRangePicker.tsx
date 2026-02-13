/**
 * Date range picker with presets
 */

import {
  Box,
  Button,
  HStack,
  VStack,
  Input,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Text,
  Divider,
  useOutsideClick,
} from '@chakra-ui/react';
import { ChevronDownIcon } from '@chakra-ui/icons';
import { useState, useRef } from 'react';

export interface DateRange {
  start: string; // ISO date string
  end: string; // ISO date string
  label: string;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  customMonthStartDay?: number; // Day of month to start custom months (e.g., 16)
}

export const DateRangePicker = ({ value, onChange, customMonthStartDay = 1 }: DateRangePickerProps) => {
  const [isCustom, setIsCustom] = useState(false);
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const customRef = useRef<HTMLDivElement>(null);

  useOutsideClick({
    ref: customRef,
    handler: () => {
      if (isCustom && customStart && customEnd) {
        handleApplyCustom();
      }
    },
  });

  const getCustomMonthDates = (monthOffset: number = 0) => {
    const now = new Date();
    const currentDay = now.getDate();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    let startMonth = currentMonth;
    let startYear = currentYear;

    // Determine which custom month period we're in
    if (currentDay >= customMonthStartDay) {
      // We're past the boundary in current calendar month
      // Current custom month: customMonthStartDay of this month to customMonthStartDay of next month
      // Do nothing, use current month
    } else {
      // We haven't reached the boundary yet
      // Current custom month: customMonthStartDay of last month to customMonthStartDay of this month
      startMonth = currentMonth - 1;
      if (startMonth < 0) {
        startMonth = 11;
        startYear = currentYear - 1;
      }
    }

    // Apply the month offset
    startMonth = startMonth + monthOffset;
    while (startMonth < 0) {
      startMonth += 12;
      startYear--;
    }
    while (startMonth > 11) {
      startMonth -= 12;
      startYear++;
    }

    // Create start date
    const start = new Date(startYear, startMonth, customMonthStartDay);

    // End date is one month later
    let endMonth = startMonth + 1;
    let endYear = startYear;
    if (endMonth > 11) {
      endMonth = 0;
      endYear++;
    }
    const end = new Date(endYear, endMonth, customMonthStartDay);

    return { start, end };
  };

  const getDateRange = (preset: string): DateRange => {
    const now = new Date();
    const start = new Date();
    const end = new Date();

    switch (preset) {
      case 'this_month':
        if (customMonthStartDay === 1) {
          // Standard calendar month - from 1st to today
          start.setDate(1);
          start.setHours(0, 0, 0, 0);
          // End is today, not end of month
          end.setHours(23, 59, 59, 999);
        } else {
          // Custom month boundary - from custom start day to today
          const currentDay = now.getDate();
          if (currentDay >= customMonthStartDay) {
            // We're past the boundary in current month
            start.setDate(customMonthStartDay);
          } else {
            // We haven't reached the boundary yet, use previous month's boundary
            start.setMonth(start.getMonth() - 1);
            start.setDate(customMonthStartDay);
          }
          // End is always today for "This Month"
          end.setHours(23, 59, 59, 999);
        }
        return {
          start: start.toISOString().split('T')[0],
          end: end.toISOString().split('T')[0],
          label: 'This Month',
        };

      case 'last_month':
        if (customMonthStartDay === 1) {
          // Standard calendar month
          start.setMonth(start.getMonth() - 1, 1);
          start.setHours(0, 0, 0, 0);
          end.setMonth(end.getMonth(), 0);
          end.setHours(23, 59, 59, 999);
        } else {
          // Custom month boundary
          const { start: customStart, end: customEnd } = getCustomMonthDates(-1);
          return {
            start: customStart.toISOString().split('T')[0],
            end: customEnd.toISOString().split('T')[0],
            label: 'Last Month',
          };
        }
        return {
          start: start.toISOString().split('T')[0],
          end: end.toISOString().split('T')[0],
          label: 'Last Month',
        };

      case 'this_year':
        start.setMonth(0, 1);
        start.setHours(0, 0, 0, 0);
        end.setMonth(11, 31);
        end.setHours(23, 59, 59, 999);
        return {
          start: start.toISOString().split('T')[0],
          end: end.toISOString().split('T')[0],
          label: 'This Year',
        };

      case 'last_year':
        start.setFullYear(start.getFullYear() - 1, 0, 1);
        start.setHours(0, 0, 0, 0);
        end.setFullYear(end.getFullYear() - 1, 11, 31);
        end.setHours(23, 59, 59, 999);
        return {
          start: start.toISOString().split('T')[0],
          end: end.toISOString().split('T')[0],
          label: 'Last Year',
        };

      case 'all_time':
        start.setFullYear(start.getFullYear() - 10);
        start.setHours(0, 0, 0, 0);
        return {
          start: start.toISOString().split('T')[0],
          end: end.toISOString().split('T')[0],
          label: 'All Time',
        };

      default:
        return value;
    }
  };

  const handlePresetClick = (preset: string) => {
    const range = getDateRange(preset);
    onChange(range);
    setIsCustom(false);
  };

  const handleCustomClick = () => {
    setIsCustom(true);
    setCustomStart(value.start);
    setCustomEnd(value.end);
  };

  const handleApplyCustom = () => {
    if (customStart && customEnd) {
      onChange({
        start: customStart,
        end: customEnd,
        label: 'Custom Range',
      });
      setIsCustom(false);
    }
  };

  return (
    <Box position="relative">
      <Menu>
        <MenuButton
          as={Button}
          rightIcon={<ChevronDownIcon />}
          size="sm"
          variant="outline"
        >
          {value.label}
        </MenuButton>
        <MenuList>
          <MenuItem onClick={() => handlePresetClick('this_month')}>
            This Month
          </MenuItem>
          <MenuItem onClick={() => handlePresetClick('last_month')}>
            Last Month
          </MenuItem>
          <MenuItem onClick={() => handlePresetClick('this_year')}>
            This Year
          </MenuItem>
          <MenuItem onClick={() => handlePresetClick('last_year')}>
            Last Year
          </MenuItem>
          <MenuItem onClick={() => handlePresetClick('all_time')}>
            All Time
          </MenuItem>
          <Divider />
          <MenuItem onClick={handleCustomClick}>Custom Range...</MenuItem>
        </MenuList>
      </Menu>

      {isCustom && (
        <Box
          ref={customRef}
          position="absolute"
          right={0}
          mt={2}
          p={4}
          bg="white"
          borderWidth={1}
          borderRadius="md"
          boxShadow="lg"
          zIndex={1000}
        >
          <VStack spacing={3} align="stretch">
            <Text fontWeight="medium" fontSize="sm">
              Custom Date Range
            </Text>
            <HStack spacing={2}>
              <Box>
                <Text fontSize="xs" color="gray.600" mb={1}>
                  Start Date
                </Text>
                <Input
                  type="date"
                  size="sm"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                />
              </Box>
              <Box>
                <Text fontSize="xs" color="gray.600" mb={1}>
                  End Date
                </Text>
                <Input
                  type="date"
                  size="sm"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                />
              </Box>
            </HStack>
            <Button
              size="sm"
              colorScheme="brand"
              onClick={handleApplyCustom}
              isDisabled={!customStart || !customEnd}
            >
              Apply
            </Button>
          </VStack>
        </Box>
      )}
    </Box>
  );
};
