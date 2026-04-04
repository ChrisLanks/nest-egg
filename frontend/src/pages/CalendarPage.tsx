import React, { useState, useMemo, useCallback } from "react";
import { useUserView } from "../contexts/UserViewContext";
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
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
import api from "../services/api";
import {
  financialCalendarApi,
  type FinancialCalendarResponse,
  type FinancialCalendarEvent,
} from "../api/recurring-transactions";

// ─── Local extended event type (adds "dividend" to the API's union) ───────────

type CalendarEventWithDividend =
  | FinancialCalendarEvent
  | { date: string; type: "dividend"; name: string; amount: number; account?: string; frequency?: string };

// ─── Dividend calendar API types ──────────────────────────────────────────────

interface DividendEvent {
  ticker?: string;
  account_name: string;
  income_type: string;
  amount: number;
  ex_date?: string;
  pay_date?: string;
}

interface MonthlyDividend {
  month: number;
  month_name: string;
  total: number;
  events: DividendEvent[];
}

interface DividendCalendarResponse {
  year: number;
  months: MonthlyDividend[];
}

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
  if (type === "dividend") return "teal";
  return "red"; // bill
};

const eventTypeLabel = (type: string) => {
  if (type === "income") return "Income";
  if (type === "subscription") return "Subscription";
  if (type === "dividend") return "Dividend";
  return "Bill";
};

// ─── Persisted toggle preferences ────────────────────────────────────────────

const CALENDAR_PREFS_KEY = "nest-egg-calendar-prefs";

interface CalendarPrefs {
  showBills: boolean;
  showSubscriptions: boolean;
  showIncome: boolean;
  showProjectedBalance: boolean;
  showDividends: boolean;
}

const DEFAULT_PREFS: CalendarPrefs = {
  showBills: true,
  showSubscriptions: true,
  showIncome: true,
  showProjectedBalance: false,
  showDividends: false,
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
  const { selectedUserId, effectiveUserId } = useUserView();

  // Hoisted color mode value (cannot call hooks inside callbacks)
  const todayTextColor = useColorModeValue("blue.600", "blue.300");

  // Calendar state
  const today = new Date();
  const [calYear, setCalYear] = useState(today.getFullYear());
  const [calMonth, setCalMonth] = useState(today.getMonth());
  const [viewMode, setViewMode] = useState<"monthly" | "weekly">("monthly");
  // Weekly view: track which week (Sunday start)
  const [weekStart, setWeekStart] = useState<Date>(() => {
    const d = new Date(today);
    d.setDate(d.getDate() - d.getDay());
    d.setHours(0, 0, 0, 0);
    return d;
  });

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
  const [showDividends, setShowDividends] = useState(
    () => loadCalendarPrefs().showDividends ?? false,
  );

  const updatePref = useCallback((key: keyof CalendarPrefs, value: boolean) => {
    const prefs = loadCalendarPrefs();
    prefs[key] = value;
    saveCalendarPrefs(prefs);
  }, []);

  // ── Query ───────────────────────────────────────────────────────────────────

  const calMonthStr = `${calYear}-${String(calMonth + 1).padStart(2, "0")}`;
  const {
    data: financialCalendar,
    isLoading: financialCalendarLoading,
    isError: financialCalendarError,
    refetch: refetchCalendar,
  } = useQuery<FinancialCalendarResponse>({
    queryKey: ["financial-calendar", calMonthStr, effectiveUserId],
    queryFn: () => financialCalendarApi.getMonth(calMonthStr, selectedUserId),
    staleTime: 2 * 60 * 1000,
  });

  const { data: dividendCalendar } = useQuery<DividendCalendarResponse>({
    queryKey: ["dividend-calendar", calYear, effectiveUserId],
    queryFn: async () => {
      const params: Record<string, string | number> = { year: calYear };
      if (selectedUserId) params.user_id = effectiveUserId;
      const { data } = await api.get<DividendCalendarResponse>(
        "/holdings/dividend-calendar",
        { params },
      );
      return data;
    },
    enabled: showDividends,
    staleTime: 5 * 60 * 1000,
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

  // Filtered financial calendar events based on toggle state (with dividend events merged in)
  const filteredEvents = useMemo<CalendarEventWithDividend[]>(() => {
    const base: CalendarEventWithDividend[] = financialCalendar
      ? financialCalendar.events.filter((ev) => {
          if (ev.type === "bill" && !showBills) return false;
          if (ev.type === "subscription" && !showSubscriptions) return false;
          if (ev.type === "income" && !showIncome) return false;
          return true;
        })
      : [];

    if (!showDividends || !dividendCalendar) return base;

    const dividendEvents: CalendarEventWithDividend[] = [];
    for (const month of dividendCalendar.months) {
      for (const ev of month.events) {
        const date = ev.pay_date ?? ev.ex_date;
        if (!date) continue;
        dividendEvents.push({
          date,
          type: "dividend",
          name: ev.ticker ?? ev.income_type,
          amount: ev.amount,
          account: ev.account_name,
        });
      }
    }

    return [...base, ...dividendEvents];
  }, [financialCalendar, showBills, showSubscriptions, showIncome, showDividends, dividendCalendar]);

  // Group financial events by date
  const financialByDate = useMemo(() => {
    const map = new Map<string, CalendarEventWithDividend[]>();
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
        <Text color="text.secondary" mt={-4} fontSize="sm">
          Upcoming bills, pay dates, and financial deadlines — so nothing catches you off guard.
        </Text>

        {financialCalendarLoading ? (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        ) : financialCalendarError ? (
          <Center py={16}>
            <VStack spacing={4}>
              <Alert status="error" borderRadius="md">
                <AlertIcon />
                <AlertTitle>Failed to load calendar.</AlertTitle>
                <AlertDescription>Please try again.</AlertDescription>
              </Alert>
              <Button colorScheme="blue" onClick={() => refetchCalendar()}>
                Retry
              </Button>
            </VStack>
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
                  <FormControl display="flex" alignItems="center" w="auto">
                    <Switch
                      id="show-dividends"
                      colorScheme="teal"
                      isChecked={showDividends}
                      onChange={(e) => {
                        setShowDividends(e.target.checked);
                        updatePref("showDividends", e.target.checked);
                      }}
                      size="sm"
                    />
                    <FormLabel
                      htmlFor="show-dividends"
                      mb={0}
                      ml={2}
                      fontSize="sm"
                      cursor="pointer"
                    >
                      <Badge colorScheme="teal" variant="subtle" mr={1}>
                        Dividends
                      </Badge>
                    </FormLabel>
                  </FormControl>
                </HStack>
              </CardBody>
            </Card>

            {/* View mode toggle + navigation */}
            <HStack justify="space-between" flexWrap="wrap" gap={2}>
              <HStack>
                <Button
                  size="sm"
                  variant={viewMode === "monthly" ? "solid" : "outline"}
                  colorScheme={viewMode === "monthly" ? "brand" : "gray"}
                  onClick={() => setViewMode("monthly")}
                >
                  Monthly
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === "weekly" ? "solid" : "outline"}
                  colorScheme={viewMode === "weekly" ? "brand" : "gray"}
                  onClick={() => setViewMode("weekly")}
                >
                  Weekly
                </Button>
              </HStack>
              {viewMode === "monthly" ? (
                <HStack>
                  <Text color="text.secondary" fontSize="sm" mr={2}>{monthName}</Text>
                  <Button size="sm" variant="outline" onClick={prevMonth} leftIcon={<FiChevronLeft />}>Prev</Button>
                  <Button size="sm" variant="outline" onClick={() => { setCalMonth(today.getMonth()); setCalYear(today.getFullYear()); }}>Today</Button>
                  <Button size="sm" variant="outline" onClick={nextMonth} rightIcon={<FiChevronRight />}>Next</Button>
                </HStack>
              ) : (
                <HStack>
                  <Text color="text.secondary" fontSize="sm" mr={2}>
                    {weekStart.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    {" – "}
                    {new Date(weekStart.getTime() + 6 * 86400000).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </Text>
                  <Button size="sm" variant="outline" leftIcon={<FiChevronLeft />} onClick={() => setWeekStart(new Date(weekStart.getTime() - 7 * 86400000))}>Prev</Button>
                  <Button size="sm" variant="outline" onClick={() => { const d = new Date(today); d.setDate(d.getDate() - d.getDay()); d.setHours(0,0,0,0); setWeekStart(d); }}>This Week</Button>
                  <Button size="sm" variant="outline" rightIcon={<FiChevronRight />} onClick={() => setWeekStart(new Date(weekStart.getTime() + 7 * 86400000))}>Next</Button>
                </HStack>
              )}
            </HStack>

            {/* Weekly view */}
            {viewMode === "weekly" && (() => {
              const weekDays = Array.from({ length: 7 }, (_, i) => new Date(weekStart.getTime() + i * 86400000));
              const weekEnd = new Date(weekStart.getTime() + 7 * 86400000);
              const weekEvents = filteredEvents.filter((ev) => {
                // Parse YYYY-MM-DD as local midnight to avoid UTC offset shifting the date
                const [y, m, d] = ev.date.split("-").map(Number);
                const evDate = new Date(y, m - 1, d);
                return evDate >= weekStart && evDate < weekEnd;
              });
              const totalInflow = weekEvents.filter((e) => e.type === "income").reduce((s, e) => s + Math.abs(e.amount), 0);
              const totalOutflow = weekEvents.filter((e) => e.type !== "income").reduce((s, e) => s + Math.abs(e.amount), 0);
              return (
                <VStack align="stretch" spacing={3}>
                  <Grid templateColumns="repeat(7, 1fr)" gap={2}>
                    {weekDays.map((day) => {
                      const dateStr = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
                      const dayEvents = filteredEvents.filter((ev) => ev.date === dateStr);
                      const isToday = day.toDateString() === today.toDateString();
                      const dayInflow = dayEvents.filter((e) => e.type === "income").reduce((s, e) => s + Math.abs(e.amount), 0);
                      const dayOutflow = dayEvents.filter((e) => e.type !== "income").reduce((s, e) => s + Math.abs(e.amount), 0);
                      const dayNet = dayInflow - dayOutflow;
                      return (
                        <GridItem key={dateStr} borderWidth="1px" borderRadius="md" p={2} bg={isToday ? "brand.50" : undefined} _dark={{ bg: isToday ? "brand.900" : undefined }} minH="120px">
                          <Text fontSize="xs" fontWeight="bold" color={isToday ? "brand.500" : "text.secondary"} mb={1}>
                            {day.toLocaleDateString("en-US", { weekday: "short", month: "numeric", day: "numeric" })}
                          </Text>
                          <VStack align="stretch" spacing={1}>
                            {dayEvents.slice(0, 4).map((ev, i) => (
                              <Badge key={i} colorScheme={eventTypeColor(ev.type)} fontSize="xs" noOfLines={1} textAlign="left" display="block">
                                {ev.merchant_name ?? ev.description ?? eventTypeLabel(ev.type)} {formatCurrencyShort(Math.abs(ev.amount))}
                              </Badge>
                            ))}
                            {dayEvents.length > 4 && <Text fontSize="xs" color="text.muted">+{dayEvents.length - 4} more</Text>}
                          </VStack>
                          {dayEvents.length > 0 && (
                            <Text fontSize="xs" mt={1} color={dayNet >= 0 ? "green.500" : "red.500"} fontWeight="bold">
                              Net: {dayNet >= 0 ? "+" : ""}{formatCurrencyShort(dayNet)}
                            </Text>
                          )}
                        </GridItem>
                      );
                    })}
                  </Grid>
                  {/* Weekly summary */}
                  <Card variant="outline" size="sm">
                    <CardBody py={2}>
                      <HStack spacing={6} flexWrap="wrap">
                        <Text fontSize="sm"><Text as="span" color="green.500" fontWeight="bold">+{formatCurrencyShort(totalInflow)}</Text> inflow</Text>
                        <Text fontSize="sm"><Text as="span" color="red.500" fontWeight="bold">−{formatCurrencyShort(totalOutflow)}</Text> outflow</Text>
                        <Text fontSize="sm">Net: <Text as="span" fontWeight="bold" color={(totalInflow - totalOutflow) >= 0 ? "green.500" : "red.500"}>{formatCurrencyShort(totalInflow - totalOutflow)}</Text></Text>
                      </HStack>
                    </CardBody>
                  </Card>
                </VStack>
              );
            })()}

            {/* Monthly calendar (hidden in weekly mode) */}
            {viewMode === "monthly" && (<>

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
            </>)}
          </VStack>
        )}
      </VStack>
    </Container>
  );
};

export default CalendarPage;
