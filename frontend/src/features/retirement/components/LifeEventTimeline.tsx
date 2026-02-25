/**
 * Horizontal bar chart showing life events as colored bars on an age timeline.
 */

import {
  Box,
  HStack,
  IconButton,
  Text,
  Tooltip,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import { useMemo } from 'react';
import type { LifeEvent } from '../types/retirement';

const CATEGORY_COLORS: Record<string, string> = {
  child: '#ED64A6',
  pet: '#ED8936',
  home_purchase: '#38B2AC',
  home_downsize: '#0BC5EA',
  career_change: '#805AD5',
  bonus: '#48BB78',
  healthcare: '#F56565',
  travel: '#4299E1',
  vehicle: '#A0AEC0',
  elder_care: '#ECC94B',
  custom: '#718096',
};

interface LifeEventTimelineProps {
  events: LifeEvent[];
  currentAge?: number;
  retirementAge?: number;
  lifeExpectancy?: number;
  onEventClick?: (event: LifeEvent) => void;
  onDeleteEvent?: (eventId: string) => void;
}

export function LifeEventTimeline({
  events,
  currentAge = 30,
  retirementAge = 67,
  lifeExpectancy = 95,
  onEventClick,
  onDeleteEvent,
}: LifeEventTimelineProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const trackBg = useColorModeValue('gray.100', 'gray.700');
  const textColor = useColorModeValue('gray.600', 'gray.400');

  const minAge = currentAge;
  const maxAge = lifeExpectancy;
  const totalSpan = maxAge - minAge;

  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => a.start_age - b.start_age),
    [events]
  );

  if (events.length === 0) return null;

  const getPosition = (age: number) => {
    return Math.max(0, Math.min(100, ((age - minAge) / totalSpan) * 100));
  };

  const formatCost = (event: LifeEvent) => {
    if (event.annual_cost) return `$${(event.annual_cost / 1000).toFixed(0)}K/yr`;
    if (event.one_time_cost) return `$${(event.one_time_cost / 1000).toFixed(0)}K`;
    if (event.income_change) {
      const sign = event.income_change > 0 ? '+' : '';
      return `${sign}$${(event.income_change / 1000).toFixed(0)}K`;
    }
    return '';
  };

  return (
    <Box bg={bgColor} p={4} borderRadius="xl" shadow="sm">
      <Text fontSize="sm" fontWeight="semibold" mb={3}>
        Life Events Timeline
      </Text>

      <VStack spacing={2} align="stretch">
        {/* Age axis */}
        <Box position="relative" h="20px">
          <Box bg={trackBg} h="4px" borderRadius="full" position="absolute" top="8px" left={0} right={0} />
          {/* Retirement marker */}
          <Box
            position="absolute"
            left={`${getPosition(retirementAge)}%`}
            top={0}
            h="20px"
            w="2px"
            bg="orange.400"
          />
          {/* Age labels */}
          <Text position="absolute" left={0} top="-2px" fontSize="2xs" color={textColor}>
            {minAge}
          </Text>
          <Text
            position="absolute"
            left={`${getPosition(retirementAge)}%`}
            top="-2px"
            fontSize="2xs"
            color="orange.500"
            transform="translateX(-50%)"
          >
            {retirementAge}
          </Text>
          <Text position="absolute" right={0} top="-2px" fontSize="2xs" color={textColor}>
            {maxAge}
          </Text>
        </Box>

        {/* Event bars */}
        {sortedEvents.map((event) => {
          const startPct = getPosition(event.start_age);
          const endAge = event.end_age || event.start_age;
          const endPct = getPosition(endAge);
          const width = Math.max(endPct - startPct, 1); // Min 1% width for one-time events
          const color = CATEGORY_COLORS[event.category] || CATEGORY_COLORS.custom;

          return (
            <Tooltip
              key={event.id}
              label={`${event.name}: Age ${event.start_age}${event.end_age ? `-${event.end_age}` : ''} | ${formatCost(event)}`}
              fontSize="xs"
            >
              <HStack
                spacing={1}
                cursor={onEventClick ? 'pointer' : 'default'}
                onClick={() => onEventClick?.(event)}
                _hover={{ opacity: 0.8 }}
              >
                <Box position="relative" flex={1} h="24px">
                  <Box bg={trackBg} h="full" borderRadius="md" />
                  <Box
                    position="absolute"
                    left={`${startPct}%`}
                    top={0}
                    h="full"
                    w={`${width}%`}
                    bg={color}
                    borderRadius="md"
                    opacity={0.8}
                    display="flex"
                    alignItems="center"
                    px={1}
                    overflow="hidden"
                  >
                    <Text fontSize="2xs" color="white" fontWeight="medium" noOfLines={1}>
                      {event.name}
                    </Text>
                  </Box>
                </Box>
                {onDeleteEvent && (
                  <IconButton
                    aria-label="Delete event"
                    icon={<Text fontSize="xs">x</Text>}
                    size="xs"
                    variant="ghost"
                    colorScheme="red"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteEvent(event.id);
                    }}
                  />
                )}
              </HStack>
            </Tooltip>
          );
        })}
      </VStack>
    </Box>
  );
}
