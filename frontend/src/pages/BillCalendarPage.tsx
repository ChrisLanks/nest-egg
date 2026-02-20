/**
 * Bill Calendar Page — monthly grid view of recurring bills
 */

import { useState, useMemo } from 'react';
import {
  Box,
  Button,
  Grid,
  GridItem,
  Heading,
  HStack,
  Popover,
  PopoverArrow,
  PopoverBody,
  PopoverCloseButton,
  PopoverContent,
  PopoverHeader,
  PopoverTrigger,
  Spinner,
  Center,
  Text,
  VStack,
  Badge,
} from '@chakra-ui/react';
import { FiChevronLeft, FiChevronRight } from 'react-icons/fi';
import { useQuery } from '@tanstack/react-query';
import { recurringTransactionsApi, type CalendarEntry } from '../api/recurring-transactions';

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const amountColor = (amount: number) => {
  if (amount < 50) return 'gray';
  if (amount < 200) return 'yellow';
  return 'red';
};

export default function BillCalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth()); // 0-indexed

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['bill-calendar'],
    queryFn: () => recurringTransactionsApi.getCalendar(365),
    staleTime: 5 * 60 * 1000,
  });

  // Group entries by ISO date string
  const byDate = useMemo(() => {
    const map = new Map<string, CalendarEntry[]>();
    for (const entry of entries) {
      const key = entry.date;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(entry);
    }
    return map;
  }, [entries]);

  const prevMonth = () => {
    if (month === 0) { setMonth(11); setYear(y => y - 1); }
    else setMonth(m => m - 1);
  };

  const nextMonth = () => {
    if (month === 11) { setMonth(0); setYear(y => y + 1); }
    else setMonth(m => m + 1);
  };

  // Build calendar grid
  const firstDay = new Date(year, month, 1).getDay(); // 0=Sun
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  // Cells: leading empty + day cells
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  // Pad to complete final row
  while (cells.length % 7 !== 0) cells.push(null);

  // Month total
  const monthTotal = useMemo(() => {
    let total = 0;
    for (let d = 1; d <= daysInMonth; d++) {
      const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      for (const entry of byDate.get(key) ?? []) total += entry.amount;
    }
    return total;
  }, [byDate, year, month, daysInMonth]);

  const monthName = new Date(year, month, 1).toLocaleString('en-US', { month: 'long', year: 'numeric' });

  return (
    <Box p={8}>
      <VStack align="stretch" spacing={6}>
        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={0}>
            <Heading size="lg">Bill Calendar</Heading>
            <Text color="gray.600" fontSize="sm">
              {monthName} · Total: <strong>{formatCurrency(monthTotal)}</strong>
            </Text>
          </VStack>
          <HStack>
            <Button size="sm" variant="outline" onClick={prevMonth} leftIcon={<FiChevronLeft />}>Prev</Button>
            <Button size="sm" variant="outline" onClick={() => { setMonth(today.getMonth()); setYear(today.getFullYear()); }}>Today</Button>
            <Button size="sm" variant="outline" onClick={nextMonth} rightIcon={<FiChevronRight />}>Next</Button>
          </HStack>
        </HStack>

        {isLoading ? (
          <Center py={12}><Spinner size="xl" /></Center>
        ) : (
          <Box borderWidth="1px" borderRadius="lg" overflow="hidden">
            {/* Day-of-week header */}
            <Grid templateColumns="repeat(7, 1fr)">
              {DAYS_OF_WEEK.map(d => (
                <GridItem key={d} bg="gray.50" p={2} textAlign="center">
                  <Text fontSize="xs" fontWeight="bold" color="gray.500">{d}</Text>
                </GridItem>
              ))}
            </Grid>

            {/* Calendar rows */}
            <Grid templateColumns="repeat(7, 1fr)">
              {cells.map((day, idx) => {
                if (day === null) {
                  return <GridItem key={`empty-${idx}`} minH="90px" bg="gray.50" borderTop="1px solid" borderColor="gray.100" />;
                }

                const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const dayEntries = byDate.get(key) ?? [];
                const isToday = day === today.getDate() && month === today.getMonth() && year === today.getFullYear();

                return (
                  <GridItem
                    key={key}
                    minH="90px"
                    p={1.5}
                    borderTop="1px solid"
                    borderLeft={idx % 7 !== 0 ? '1px solid' : undefined}
                    borderColor="gray.100"
                    bg={isToday ? 'blue.50' : 'white'}
                  >
                    <Text
                      fontSize="sm"
                      fontWeight={isToday ? 'bold' : 'normal'}
                      color={isToday ? 'blue.600' : 'gray.700'}
                      mb={1}
                    >
                      {day}
                    </Text>

                    {/* Up to 2 bill chips, then +N more */}
                    {dayEntries.slice(0, 2).map((entry, i) => (
                      <Popover key={i} trigger="hover" placement="top" isLazy>
                        <PopoverTrigger>
                          <Badge
                            display="block"
                            mb="1px"
                            colorScheme={amountColor(entry.amount)}
                            fontSize="2xs"
                            isTruncated
                            cursor="pointer"
                          >
                            {entry.merchant_name}
                          </Badge>
                        </PopoverTrigger>
                        <PopoverContent width="200px">
                          <PopoverArrow />
                          <PopoverCloseButton />
                          <PopoverHeader fontSize="sm" fontWeight="bold">{entry.merchant_name}</PopoverHeader>
                          <PopoverBody fontSize="sm">
                            <Text>{formatCurrency(entry.amount)}</Text>
                            <Text color="gray.500" fontSize="xs">{entry.frequency}</Text>
                          </PopoverBody>
                        </PopoverContent>
                      </Popover>
                    ))}

                    {dayEntries.length > 2 && (
                      <Popover trigger="hover" placement="top" isLazy>
                        <PopoverTrigger>
                          <Badge fontSize="2xs" colorScheme="purple" cursor="pointer">
                            +{dayEntries.length - 2} more
                          </Badge>
                        </PopoverTrigger>
                        <PopoverContent width="220px">
                          <PopoverArrow />
                          <PopoverCloseButton />
                          <PopoverHeader fontSize="sm" fontWeight="bold">All bills on {key}</PopoverHeader>
                          <PopoverBody>
                            <VStack align="stretch" spacing={1}>
                              {dayEntries.map((e, i) => (
                                <HStack key={i} justify="space-between" fontSize="sm">
                                  <Text noOfLines={1}>{e.merchant_name}</Text>
                                  <Text fontWeight="bold" flexShrink={0}>{formatCurrency(e.amount)}</Text>
                                </HStack>
                              ))}
                            </VStack>
                          </PopoverBody>
                        </PopoverContent>
                      </Popover>
                    )}
                  </GridItem>
                );
              })}
            </Grid>
          </Box>
        )}
      </VStack>
    </Box>
  );
}
