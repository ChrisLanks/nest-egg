import React, { useState, useMemo, useCallback } from "react";
import { useUserView } from "../contexts/UserViewContext";
import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Center,
  Container,
  FormControl,
  FormLabel,
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
  Switch,
  Text,
  VStack,
  useColorModeValue,
} from "@chakra-ui/react";
import { FiChevronLeft, FiChevronRight } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import {
  financialCalendarApi,
  type FinancialCalendarResponse,
  type FinancialCalendarEvent,
} from "../api/recurring-transactions";

// ─── Calendar helpers ─────────────────────────────────────────────────────────

const DAYS_OF_WEEK = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const formatCurrencyShort = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const eventTypeColor = (type: string) => {
  if (type === "income") return "green";
  if (type === "subscription") return "orange";
  return "red"; // bill
};

const eventTypeLabel = (type: string) => {
  if (type === "income") return "Income";
  if (type === "subscription") return "Subscription";
  return "Bill";
};

// ─── Persisted toggle preferences ────────────────────────────────────────────

const CALENDAR_PREFS_KEY = "nest-egg-calendar-prefs";

interface CalendarPrefs {
  showBills: boolean;
  showSubscriptions: boolean;
  showIncome: boolean;
  showProjectedBalance: boolean;
}

const DEFAULT_PREFS: CalendarPrefs = {
  showBills: true,
  showSubscriptions: true,
  showIncome: true,
  showProjectedBalance: false,
};

function loadCalendarPrefs(): CalendarPrefs {
  try {
    const raw = localStorage.getItem(CALENDAR_PREFS_KEY);
    if (raw) return { ...DEFAULT_PREFS, ...JSON.parse(raw) };
  } catch {
    /* ignore corrupt data */
  }
  return DEFAULT_PREFS;
}

function saveCalendarPrefs(prefs: CalendarPrefs): void {
  try {
    localStorage.setItem(CALENDAR_PREFS_KEY, JSON.stringify(prefs));
  } catch {
    /* ignore */
  }
}

// ─── CalendarPage ─────────────────────────────────────────────────────────────

export const CalendarPage: React.FC = () => {
  const { selectedUserId } = useUserView();

  // Hoisted color mode value (cannot call hooks inside callbacks)
  const todayTextColor = useColorModeValue("blue.600", "blue.300");

  // Calendar state
  const today = new Date();
  const [calYear, setCalYear] = useState(today.getFullYear());
  const [calMonth, setCalMonth] = useState(today.getMonth());

  // Financial calendar toggle filters (persisted to localStorage)
  const [showBills, setShowBills] = useState(
    () => loadCalendarPrefs().showBills,
  );
  const [showSubscriptions, setShowSubscriptions] = useState(
    () => loadCalendarPrefs().showSubscriptions,
  );
  const [showIncome, setShowIncome] = useState(
    () => loadCalendarPrefs().showIncome,
  );
  const [showProjectedBalance, setShowProjectedBalance] = useState(
    () => loadCalendarPrefs().showProjectedBalance,
  );

  const updatePref = useCallback((key: keyof CalendarPrefs, value: boolean) => {
    const prefs = loadCalendarPrefs();
    prefs[key] = value;
    saveCalendarPrefs(prefs);
  }, []);

  // ── Query ───────────────────────────────────────────────────────────────────

  const calMonthStr = `${calYear}-${String(calMonth + 1).padStart(2, "0")}`;
  const { data: financialCalendar, isLoading: financialCalendarLoading } =
    useQuery<FinancialCalendarResponse>({
      queryKey: ["financial-calendar", calMonthStr, selectedUserId],
      queryFn: () => financialCalendarApi.getMonth(calMonthStr, selectedUserId),
      staleTime: 2 * 60 * 1000,
    });

  // ── Calendar helpers ────────────────────────────────────────────────────────

  const prevMonth = () => {
    if (calMonth === 0) {
      setCalMonth(11);
      setCalYear((y) => y - 1);
    } else setCalMonth((m) => m - 1);
  };

  const nextMonth = () => {
    if (calMonth === 11) {
      setCalMonth(0);
      setCalYear((y) => y + 1);
    } else setCalMonth((m) => m + 1);
  };

  // Filtered financial calendar events based on toggle state
  const filteredEvents = useMemo(() => {
    if (!financialCalendar) return [];
    return financialCalendar.events.filter((ev) => {
      if (ev.type === "bill" && !showBills) return false;
      if (ev.type === "subscription" && !showSubscriptions) return false;
      if (ev.type === "income" && !showIncome) return false;
      return true;
    });
  }, [financialCalendar, showBills, showSubscriptions, showIncome]);

  // Group financial events by date
  const financialByDate = useMemo(() => {
    const map = new Map<string, FinancialCalendarEvent[]>();
    for (const ev of filteredEvents) {
      if (!map.has(ev.date)) map.set(ev.date, []);
      map.get(ev.date)!.push(ev);
    }
    return map;
  }, [filteredEvents]);

  // Balance map for projected balance overlay
  const balanceByDate = useMemo(() => {
    const map = new Map<string, number>();
    if (financialCalendar) {
      for (const dp of financialCalendar.daily_projected_balance) {
        map.set(dp.date, dp.balance);
      }
    }
    return map;
  }, [financialCalendar]);

  const firstDay = new Date(calYear, calMonth, 1).getDay();
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const monthName = new Date(calYear, calMonth, 1).toLocaleString("en-US", {
    month: "long",
    year: "numeric",
  });

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <Heading size="lg">Financial Calendar</Heading>

        {financialCalendarLoading ? (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        ) : (
          <VStack align="stretch" spacing={4}>
            {/* Toggle filters */}
            <Card variant="outline" size="sm">
              <CardBody py={3}>
                <HStack spacing={6} flexWrap="wrap">
                  <FormControl display="flex" alignItems="center" w="auto">
                    <Switch
                      id="show-bills"
                      colorScheme="red"
                      isChecked={showBills}
                      onChange={(e) => {
                        setShowBills(e.target.checked);
                        updatePref("showBills", e.target.checked);
                      }}
                      size="sm"
                    />
                    <FormLabel
                      htmlFor="show-bills"
                      mb={0}
                      ml={2}
                      fontSize="sm"
                      cursor="pointer"
                    >
                      <Badge colorScheme="red" variant="subtle" mr={1}>
                        Bills
                      </Badge>
                    </FormLabel>
                  </FormControl>
                  <FormControl display="flex" alignItems="center" w="auto">
                    <Switch
                      id="show-subscriptions"
                      colorScheme="orange"
                      isChecked={showSubscriptions}
                      onChange={(e) => {
                        setShowSubscriptions(e.target.checked);
                        updatePref("showSubscriptions", e.target.checked);
                      }}
                      size="sm"
                    />
                    <FormLabel
                      htmlFor="show-subscriptions"
                      mb={0}
                      ml={2}
                      fontSize="sm"
                      cursor="pointer"
                    >
                      <Badge colorScheme="orange" variant="subtle" mr={1}>
                        Subscriptions
                      </Badge>
                    </FormLabel>
                  </FormControl>
                  <FormControl display="flex" alignItems="center" w="auto">
                    <Switch
                      id="show-income"
                      colorScheme="green"
                      isChecked={showIncome}
                      onChange={(e) => {
                        setShowIncome(e.target.checked);
                        updatePref("showIncome", e.target.checked);
                      }}
                      size="sm"
                    />
                    <FormLabel
                      htmlFor="show-income"
                      mb={0}
                      ml={2}
                      fontSize="sm"
                      cursor="pointer"
                    >
                      <Badge colorScheme="green" variant="subtle" mr={1}>
                        Income
                      </Badge>
                    </FormLabel>
                  </FormControl>
                  <FormControl display="flex" alignItems="center" w="auto">
                    <Switch
                      id="show-balance"
                      colorScheme="blue"
                      isChecked={showProjectedBalance}
                      onChange={(e) => {
                        setShowProjectedBalance(e.target.checked);
                        updatePref("showProjectedBalance", e.target.checked);
                      }}
                      size="sm"
                    />
                    <FormLabel
                      htmlFor="show-balance"
                      mb={0}
                      ml={2}
                      fontSize="sm"
                      cursor="pointer"
                    >
                      <Badge colorScheme="blue" variant="subtle" mr={1}>
                        Projected Balance
                      </Badge>
                    </FormLabel>
                  </FormControl>
                </HStack>
              </CardBody>
            </Card>

            {/* Month navigation */}
            <HStack justify="space-between">
              <Text color="text.secondary" fontSize="sm">
                {monthName}
              </Text>
              <HStack>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={prevMonth}
                  leftIcon={<FiChevronLeft />}
                >
                  Prev
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setCalMonth(today.getMonth());
                    setCalYear(today.getFullYear());
                  }}
                >
                  Today
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={nextMonth}
                  rightIcon={<FiChevronRight />}
                >
                  Next
                </Button>
              </HStack>
            </HStack>

            {/* Calendar grid */}
            <Box borderWidth="1px" borderRadius="lg" overflow="hidden">
              <Grid templateColumns="repeat(7, 1fr)">
                {DAYS_OF_WEEK.map((d) => (
                  <GridItem key={d} bg="bg.subtle" p={2} textAlign="center">
                    <Text fontSize="xs" fontWeight="bold" color="text.muted">
                      {d}
                    </Text>
                  </GridItem>
                ))}
              </Grid>
              <Grid templateColumns="repeat(7, 1fr)">
                {cells.map((day, idx) => {
                  if (day === null) {
                    return (
                      <GridItem
                        key={`empty-${idx}`}
                        minH="100px"
                        bg="bg.subtle"
                        borderTop="1px solid"
                        borderColor="border.subtle"
                      />
                    );
                  }
                  const key = `${calYear}-${String(calMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                  const dayEvents = financialByDate.get(key) ?? [];
                  const dayBalance = balanceByDate.get(key);
                  const isToday =
                    day === today.getDate() &&
                    calMonth === today.getMonth() &&
                    calYear === today.getFullYear();

                  // Sum amounts by type for the day
                  const dayTotal = dayEvents.reduce(
                    (sum, e) => sum + e.amount,
                    0,
                  );

                  return (
                    <GridItem
                      key={key}
                      minH="100px"
                      p={1.5}
                      borderTop="1px solid"
                      borderLeft={idx % 7 !== 0 ? "1px solid" : undefined}
                      borderColor="border.subtle"
                      bg={isToday ? "bg.info" : "bg.surface"}
                    >
                      <HStack justify="space-between" mb={1}>
                        <Text
                          fontSize="sm"
                          fontWeight={isToday ? "bold" : "normal"}
                          color={isToday ? todayTextColor : "text.heading"}
                        >
                          {day}
                        </Text>
                        {dayEvents.length > 0 && (
                          <Text
                            fontSize="2xs"
                            fontWeight="bold"
                            color={dayTotal >= 0 ? "green.500" : "red.500"}
                          >
                            {formatCurrencyShort(dayTotal)}
                          </Text>
                        )}
                      </HStack>

                      {dayEvents.slice(0, 3).map((ev, i) => (
                        <Popover key={i} trigger="hover" placement="top" isLazy>
                          <PopoverTrigger>
                            <Badge
                              display="block"
                              mb="1px"
                              colorScheme={eventTypeColor(ev.type)}
                              fontSize="2xs"
                              isTruncated
                              cursor="pointer"
                            >
                              {ev.name}
                            </Badge>
                          </PopoverTrigger>
                          <PopoverContent width="220px">
                            <PopoverArrow />
                            <PopoverCloseButton />
                            <PopoverHeader fontSize="sm" fontWeight="bold">
                              <HStack>
                                <Badge
                                  colorScheme={eventTypeColor(ev.type)}
                                  fontSize="2xs"
                                >
                                  {eventTypeLabel(ev.type)}
                                </Badge>
                                <Text>{ev.name}</Text>
                              </HStack>
                            </PopoverHeader>
                            <PopoverBody fontSize="sm">
                              <Text
                                fontWeight="bold"
                                color={ev.amount >= 0 ? "green.500" : "red.500"}
                              >
                                {formatCurrencyShort(ev.amount)}
                              </Text>
                              {ev.account && (
                                <Text color="text.muted" fontSize="xs">
                                  {ev.account}
                                </Text>
                              )}
                              {ev.frequency && (
                                <Text color="text.muted" fontSize="xs">
                                  {ev.frequency}
                                </Text>
                              )}
                            </PopoverBody>
                          </PopoverContent>
                        </Popover>
                      ))}

                      {dayEvents.length > 3 && (
                        <Popover trigger="hover" placement="top" isLazy>
                          <PopoverTrigger>
                            <Badge
                              fontSize="2xs"
                              colorScheme="purple"
                              cursor="pointer"
                            >
                              +{dayEvents.length - 3} more
                            </Badge>
                          </PopoverTrigger>
                          <PopoverContent width="240px">
                            <PopoverArrow />
                            <PopoverCloseButton />
                            <PopoverHeader fontSize="sm" fontWeight="bold">
                              All events on {key}
                            </PopoverHeader>
                            <PopoverBody>
                              <VStack align="stretch" spacing={1}>
                                {dayEvents.map((e, i) => (
                                  <HStack
                                    key={i}
                                    justify="space-between"
                                    fontSize="sm"
                                  >
                                    <HStack spacing={1} minW={0}>
                                      <Badge
                                        colorScheme={eventTypeColor(e.type)}
                                        fontSize="2xs"
                                        flexShrink={0}
                                      >
                                        {eventTypeLabel(e.type).charAt(0)}
                                      </Badge>
                                      <Text noOfLines={1}>{e.name}</Text>
                                    </HStack>
                                    <Text
                                      fontWeight="bold"
                                      flexShrink={0}
                                      color={
                                        e.amount >= 0 ? "green.500" : "red.500"
                                      }
                                    >
                                      {formatCurrencyShort(e.amount)}
                                    </Text>
                                  </HStack>
                                ))}
                              </VStack>
                            </PopoverBody>
                          </PopoverContent>
                        </Popover>
                      )}

                      {/* Projected balance line */}
                      {showProjectedBalance && dayBalance !== undefined && (
                        <Text
                          fontSize="2xs"
                          color="blue.500"
                          fontWeight="semibold"
                          mt="auto"
                          pt={0.5}
                          borderTop="1px dashed"
                          borderColor="blue.200"
                        >
                          {formatCurrencyShort(dayBalance)}
                        </Text>
                      )}
                    </GridItem>
                  );
                })}
              </Grid>
            </Box>

            {/* Summary bar */}
            {financialCalendar && (
              <Grid templateColumns="repeat(4, 1fr)" gap={4}>
                <Card variant="outline" size="sm">
                  <CardBody py={3} px={4}>
                    <Text fontSize="xs" color="text.muted" mb={1}>
                      Expected Income
                    </Text>
                    <Text fontSize="lg" fontWeight="bold" color="green.500">
                      {formatCurrencyShort(
                        financialCalendar.summary.total_income,
                      )}
                    </Text>
                  </CardBody>
                </Card>
                <Card variant="outline" size="sm">
                  <CardBody py={3} px={4}>
                    <Text fontSize="xs" color="text.muted" mb={1}>
                      Expected Bills
                    </Text>
                    <Text fontSize="lg" fontWeight="bold" color="red.500">
                      {formatCurrencyShort(
                        financialCalendar.summary.total_bills,
                      )}
                    </Text>
                  </CardBody>
                </Card>
                <Card variant="outline" size="sm">
                  <CardBody py={3} px={4}>
                    <Text fontSize="xs" color="text.muted" mb={1}>
                      Expected Subscriptions
                    </Text>
                    <Text fontSize="lg" fontWeight="bold" color="orange.500">
                      {formatCurrencyShort(
                        financialCalendar.summary.total_subscriptions,
                      )}
                    </Text>
                  </CardBody>
                </Card>
                <Card variant="outline" size="sm">
                  <CardBody py={3} px={4}>
                    <Text fontSize="xs" color="text.muted" mb={1}>
                      Projected End Balance
                    </Text>
                    <Text
                      fontSize="lg"
                      fontWeight="bold"
                      color={
                        financialCalendar.summary.projected_end_balance >= 0
                          ? "blue.500"
                          : "red.500"
                      }
                    >
                      {formatCurrencyShort(
                        financialCalendar.summary.projected_end_balance,
                      )}
                    </Text>
                  </CardBody>
                </Card>
              </Grid>
            )}
          </VStack>
        )}
      </VStack>
    </Container>
  );
};

export default CalendarPage;
