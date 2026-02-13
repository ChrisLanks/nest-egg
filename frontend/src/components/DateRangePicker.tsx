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
}

export const DateRangePicker = ({ value, onChange }: DateRangePickerProps) => {
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

  const getDateRange = (preset: string): DateRange => {
    const now = new Date();
    const start = new Date();
    const end = new Date();

    switch (preset) {
      case 'this_month':
        start.setDate(1);
        start.setHours(0, 0, 0, 0);
        end.setMonth(end.getMonth() + 1, 0);
        end.setHours(23, 59, 59, 999);
        return {
          start: start.toISOString().split('T')[0],
          end: end.toISOString().split('T')[0],
          label: 'This Month',
        };

      case 'last_month':
        start.setMonth(start.getMonth() - 1, 1);
        start.setHours(0, 0, 0, 0);
        end.setMonth(end.getMonth(), 0);
        end.setHours(23, 59, 59, 999);
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
    <Box>
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
