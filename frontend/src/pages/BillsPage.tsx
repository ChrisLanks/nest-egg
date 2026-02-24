import React, { useState, useMemo, useRef, useEffect } from 'react';
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
  Divider,
  FormControl,
  FormHelperText,
  FormLabel,
  Grid,
  GridItem,
  Heading,
  HStack,
  Icon,
  Input,
  List,
  ListItem,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  NumberInput,
  NumberInputField,
  Popover,
  PopoverArrow,
  PopoverBody,
  PopoverCloseButton,
  PopoverContent,
  PopoverHeader,
  PopoverTrigger,
  Select,
  Spinner,
  Switch,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
  Tooltip,
  useDisclosure,
  useToast,
  VStack,
} from '@chakra-ui/react';
import { AddIcon, BellIcon, CalendarIcon } from '@chakra-ui/icons';
import { FiChevronLeft, FiChevronRight, FiRefreshCw, FiArchive, FiRotateCcw, FiUser, FiZap, FiTag } from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { recurringTransactionsApi, type CalendarEntry } from '../api/recurring-transactions';
import type { RecurringTransaction, UpcomingBill } from '../types/recurring-transaction';
import { labelsApi } from '../api/labels';
import type { Label } from '../types/transaction';
import api from '../services/api';
import { useUserView } from '../contexts/UserViewContext';

interface Account {
  id: string;
  name: string;
}

// ─── Calendar helpers ─────────────────────────────────────────────────────────

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const formatCurrencyShort = (amount: number) =>
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

// ─── Main page ────────────────────────────────────────────────────────────────

const BillsPage: React.FC = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { canWriteResource } = useUserView();
  const canEdit = canWriteResource('recurring_transaction');
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedRecurring, setSelectedRecurring] = useState<RecurringTransaction | null>(null);

  // Outer tab: bills list vs calendar — persisted in URL
  const [searchParams, setSearchParams] = useSearchParams();
  const outerTabIndex = searchParams.get('tab') === 'calendar' ? 1 : 0;
  const handleOuterTabChange = (index: number) => {
    setSearchParams(index === 1 ? { tab: 'calendar' } : {});
  };

  // Inner tab: active vs archive — local state only
  const [innerTabIndex, setInnerTabIndex] = useState(0);

  // Calendar state
  const today = new Date();
  const [calYear, setCalYear] = useState(today.getFullYear());
  const [calMonth, setCalMonth] = useState(today.getMonth());

  // ── Queries ──────────────────────────────────────────────────────────────────

  const { data: upcomingBills, isLoading: billsLoading } = useQuery<UpcomingBill[]>({
    queryKey: ['upcoming-bills'],
    queryFn: () => recurringTransactionsApi.getUpcomingBills(30),
  });

  const { data: recurringTransactions = [], isLoading: recurringLoading } = useQuery<RecurringTransaction[]>({
    queryKey: ['recurring-transactions'],
    queryFn: () => recurringTransactionsApi.getAll(),
  });

  const { data: accounts } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: async () => {
      const response = await api.get('/accounts/');
      return response.data;
    },
  });

  const { data: calendarEntries = [], isLoading: calendarLoading } = useQuery<CalendarEntry[]>({
    queryKey: ['bill-calendar'],
    queryFn: () => recurringTransactionsApi.getCalendar(365),
    staleTime: 5 * 60 * 1000,
  });

  const { data: labels = [] } = useQuery<Label[]>({
    queryKey: ['labels'],
    queryFn: () => labelsApi.getAll(),
    staleTime: 60 * 1000,
  });

  // Fetch all unique merchant names once — filtered client-side in the modal
  const { data: merchantData } = useQuery<{ merchants: string[] }>({
    queryKey: ['transaction-merchants'],
    queryFn: async () => {
      const response = await api.get('/transactions/merchants');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
  const allMerchants = merchantData?.merchants ?? [];

  const labelMap = useMemo(
    () => new Map(labels.map((l) => [l.id, l])),
    [labels]
  );

  // Partition active vs archived
  const activeRecurring = useMemo(
    () => recurringTransactions.filter((r) => !r.is_archived),
    [recurringTransactions]
  );
  const archivedRecurring = useMemo(
    () => recurringTransactions.filter((r) => r.is_archived),
    [recurringTransactions]
  );

  // ── Auto-detect mutation ──────────────────────────────────────────────────────

  const detectMutation = useMutation({
    mutationFn: () => recurringTransactionsApi.detectPatterns(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['upcoming-bills'] });
      queryClient.invalidateQueries({ queryKey: ['bill-calendar'] });
      toast({
        title: 'Auto-detection complete',
        description: `Found ${data.detected_patterns} pattern${data.detected_patterns !== 1 ? 's' : ''}`,
        status: 'success',
        duration: 4000,
      });
    },
    onError: () => {
      toast({ title: 'Auto-detection failed', status: 'error', duration: 3000 });
    },
  });

  // ── CRUD mutations ────────────────────────────────────────────────────────────

  const updateRecurringMutation = useMutation({
    mutationFn: async (data: { id: string; updates: any }) =>
      recurringTransactionsApi.update(data.id, data.updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['upcoming-bills'] });
      queryClient.invalidateQueries({ queryKey: ['bill-calendar'] });
      toast({ title: 'Bill updated', status: 'success', duration: 3000 });
      onClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Error updating bill',
        description: error.response?.data?.detail || 'Failed to update bill',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const createRecurringMutation = useMutation({
    mutationFn: async (data: any) => recurringTransactionsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['upcoming-bills'] });
      queryClient.invalidateQueries({ queryKey: ['bill-calendar'] });
      toast({ title: 'Bill created', status: 'success', duration: 3000 });
      onClose();
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail;
      const description = typeof detail === 'string' ? detail : 'Failed to create bill';
      toast({
        title: 'Error creating bill',
        description,
        status: 'error',
        duration: 5000,
      });
    },
  });

  const applyLabelMutation = useMutation({
    mutationFn: ({ id, retroactive }: { id: string; retroactive: boolean }) =>
      recurringTransactionsApi.applyLabel(id, retroactive),
    onSuccess: (data, _variables) => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['labels'] });
      toast({
        title: 'Label applied',
        description: `Tagged ${data.applied_count} transaction${data.applied_count !== 1 ? 's' : ''} as "Recurring Bill"`,
        status: 'success',
        duration: 4000,
      });
    },
    onError: () => {
      toast({ title: 'Failed to apply label', status: 'error', duration: 3000 });
    },
  });

  // ── Handlers ─────────────────────────────────────────────────────────────────

  const handleEditRecurring = (recurring: RecurringTransaction) => {
    setSelectedRecurring(recurring);
    onOpen();
  };

  const handleCreateNew = () => {
    setSelectedRecurring(null);
    onOpen();
  };

  const handleSave = (formData: any, tagTransactions: boolean = false) => {
    // Sanitize numeric fields — NumberInput returns NaN when empty
    const sanitized = {
      ...formData,
      average_amount: isNaN(formData.average_amount) ? 0 : formData.average_amount,
      amount_variance: isNaN(formData.amount_variance) ? 0 : formData.amount_variance,
    };
    if (selectedRecurring) {
      updateRecurringMutation.mutate({ id: selectedRecurring.id, updates: sanitized });
    } else {
      createRecurringMutation.mutate(sanitized, {
        onSuccess: (created) => {
          if (tagTransactions) {
            applyLabelMutation.mutate({ id: created.id, retroactive: true });
          }
        },
      });
    }
  };

  const handleArchive = (id: string) => {
    updateRecurringMutation.mutate({ id, updates: { is_archived: true } });
  };

  const handleRestore = (id: string) => {
    updateRecurringMutation.mutate({ id, updates: { is_archived: false } });
  };

  // ── Formatters ────────────────────────────────────────────────────────────────

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });

  const getDueDateColor = (daysUntilDue: number, isOverdue: boolean) => {
    if (isOverdue) return 'red';
    if (daysUntilDue <= 3) return 'orange';
    if (daysUntilDue <= 7) return 'yellow';
    return 'green';
  };

  // ── Calendar helpers ──────────────────────────────────────────────────────────

  const prevMonth = () => {
    if (calMonth === 0) { setCalMonth(11); setCalYear(y => y - 1); }
    else setCalMonth(m => m - 1);
  };

  const nextMonth = () => {
    if (calMonth === 11) { setCalMonth(0); setCalYear(y => y + 1); }
    else setCalMonth(m => m + 1);
  };

  const byDate = useMemo(() => {
    const map = new Map<string, CalendarEntry[]>();
    for (const entry of calendarEntries) {
      if (!map.has(entry.date)) map.set(entry.date, []);
      map.get(entry.date)!.push(entry);
    }
    return map;
  }, [calendarEntries]);

  const firstDay = new Date(calYear, calMonth, 1).getDay();
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const monthTotal = useMemo(() => {
    let total = 0;
    for (let d = 1; d <= daysInMonth; d++) {
      const key = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      for (const entry of byDate.get(key) ?? []) total += entry.amount;
    }
    return total;
  }, [byDate, calYear, calMonth, daysInMonth]);

  const monthName = new Date(calYear, calMonth, 1).toLocaleString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  // ── Render ────────────────────────────────────────────────────────────────────

  if (billsLoading || recurringLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Center><Spinner /></Center>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between">
          <Heading size="lg">Bills</Heading>
          <Button leftIcon={<AddIcon />} colorScheme="blue" isDisabled={!canEdit} onClick={handleCreateNew}>
            Add Bill
          </Button>
        </HStack>

        <Tabs index={outerTabIndex} onChange={handleOuterTabChange} isLazy>
          <TabList>
            <Tab>Upcoming Bills</Tab>
            <Tab>Calendar</Tab>
          </TabList>

          <TabPanels>
            {/* ── Tab 0: Upcoming Bills ── */}
            <TabPanel px={0}>
              <VStack spacing={6} align="stretch">
                {/* Upcoming Bills (next 30 days) */}
                <Box>
                  <Heading size="md" mb={4}>
                    <Icon as={BellIcon} mr={2} />
                    Upcoming (Next 30 Days)
                  </Heading>

                  {upcomingBills && upcomingBills.length > 0 ? (
                    <VStack spacing={3} align="stretch">
                      {upcomingBills.map((bill) => (
                        <Card key={bill.recurring_transaction_id} variant="outline">
                          <CardBody>
                            <HStack justify="space-between">
                              <VStack align="start" spacing={1}>
                                <Text fontWeight="bold" fontSize="lg">
                                  {bill.merchant_name}
                                </Text>
                                <HStack>
                                  <Icon as={CalendarIcon} color="text.muted" />
                                  <Text fontSize="sm" color="text.secondary">
                                    Due: {formatDate(bill.next_expected_date)}
                                  </Text>
                                </HStack>
                              </VStack>
                              <HStack spacing={4}>
                                <VStack align="end" spacing={0}>
                                  <Text fontWeight="bold" fontSize="xl">
                                    {formatCurrency(bill.average_amount)}
                                  </Text>
                                  <Badge
                                    colorScheme={getDueDateColor(bill.days_until_due, bill.is_overdue)}
                                    fontSize="sm"
                                  >
                                    {bill.is_overdue
                                      ? `${Math.abs(bill.days_until_due)} days overdue`
                                      : bill.days_until_due === 0
                                      ? 'Due today'
                                      : `${bill.days_until_due} days`}
                                  </Badge>
                                </VStack>
                              </HStack>
                            </HStack>
                          </CardBody>
                        </Card>
                      ))}
                    </VStack>
                  ) : (
                    <Alert status="info">
                      <AlertIcon />
                      <AlertTitle>No upcoming bills</AlertTitle>
                      <AlertDescription>
                        No bills due in the next 30 days. Mark a recurring transaction as a bill to track it here.
                      </AlertDescription>
                    </Alert>
                  )}
                </Box>

                <Divider />

                {/* All Recurring Transactions — inner tabs */}
                <Box>
                  <HStack justify="space-between" mb={4}>
                    <Heading size="md">All Recurring Transactions</Heading>
                    <Tooltip label="Scan your transaction history to automatically find recurring bills and subscriptions">
                      <Button
                        size="sm"
                        variant="outline"
                        leftIcon={<FiRefreshCw />}
                        isLoading={detectMutation.isPending}
                        loadingText="Detecting…"
                        onClick={() => detectMutation.mutate()}
                      >
                        Auto-detect
                      </Button>
                    </Tooltip>
                  </HStack>

                  <Tabs index={innerTabIndex} onChange={setInnerTabIndex} size="sm" variant="soft-rounded" colorScheme="gray">
                    <TabList mb={4}>
                      <Tab>
                        Active
                        {activeRecurring.length > 0 && (
                          <Badge ml={2} colorScheme="blue" borderRadius="full">
                            {activeRecurring.length}
                          </Badge>
                        )}
                      </Tab>
                      <Tab>
                        Archive
                        {archivedRecurring.length > 0 && (
                          <Badge ml={2} colorScheme="gray" borderRadius="full">
                            {archivedRecurring.length}
                          </Badge>
                        )}
                      </Tab>
                    </TabList>

                    <TabPanels>
                      {/* Active recurring */}
                      <TabPanel px={0} pt={0}>
                        {activeRecurring.length > 0 ? (
                          <VStack spacing={3} align="stretch">
                            {activeRecurring.map((recurring) => (
                              <RecurringCard
                                key={recurring.id}
                                recurring={recurring}
                                formatCurrency={formatCurrency}
                                formatDate={formatDate}
                                onEdit={handleEditRecurring}
                                onArchive={handleArchive}
                                onApplyLabel={(id) => applyLabelMutation.mutate({ id, retroactive: true })}
                                isUpdating={updateRecurringMutation.isPending}
                                isApplyingLabel={applyLabelMutation.isPending}
                                labelMap={labelMap}
                                canEdit={canEdit}
                              />
                            ))}
                          </VStack>
                        ) : (
                          <Alert status="info">
                            <AlertIcon />
                            <AlertTitle>No recurring transactions</AlertTitle>
                            <AlertDescription>
                              Click <strong>Auto-detect</strong> to find patterns in your transactions, or add one manually.
                            </AlertDescription>
                          </Alert>
                        )}
                      </TabPanel>

                      {/* Archived recurring */}
                      <TabPanel px={0} pt={0}>
                        {archivedRecurring.length > 0 ? (
                          <VStack spacing={3} align="stretch">
                            {archivedRecurring.map((recurring) => (
                              <RecurringCard
                                key={recurring.id}
                                recurring={recurring}
                                formatCurrency={formatCurrency}
                                formatDate={formatDate}
                                onRestore={handleRestore}
                                isUpdating={updateRecurringMutation.isPending}
                                labelMap={labelMap}
                                isArchiveView
                                canEdit={canEdit}
                              />
                            ))}
                          </VStack>
                        ) : (
                          <Alert status="info">
                            <AlertIcon />
                            <AlertDescription>No archived bills.</AlertDescription>
                          </Alert>
                        )}
                      </TabPanel>
                    </TabPanels>
                  </Tabs>
                </Box>
              </VStack>
            </TabPanel>

            {/* ── Tab 1: Calendar ── */}
            <TabPanel px={0}>
              {calendarLoading ? (
                <Center py={12}><Spinner size="xl" /></Center>
              ) : (
                <VStack align="stretch" spacing={4}>
                  <HStack justify="space-between">
                    <Text color="text.secondary" fontSize="sm">
                      {monthName} · Total: <strong>{formatCurrencyShort(monthTotal)}</strong>
                    </Text>
                    <HStack>
                      <Button size="sm" variant="outline" onClick={prevMonth} leftIcon={<FiChevronLeft />}>
                        Prev
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => { setCalMonth(today.getMonth()); setCalYear(today.getFullYear()); }}
                      >
                        Today
                      </Button>
                      <Button size="sm" variant="outline" onClick={nextMonth} rightIcon={<FiChevronRight />}>
                        Next
                      </Button>
                    </HStack>
                  </HStack>

                  <Box borderWidth="1px" borderRadius="lg" overflow="hidden">
                    <Grid templateColumns="repeat(7, 1fr)">
                      {DAYS_OF_WEEK.map(d => (
                        <GridItem key={d} bg="bg.subtle" p={2} textAlign="center">
                          <Text fontSize="xs" fontWeight="bold" color="text.muted">{d}</Text>
                        </GridItem>
                      ))}
                    </Grid>
                    <Grid templateColumns="repeat(7, 1fr)">
                      {cells.map((day, idx) => {
                        if (day === null) {
                          return (
                            <GridItem
                              key={`empty-${idx}`}
                              minH="90px"
                              bg="bg.subtle"
                              borderTop="1px solid"
                              borderColor="border.subtle"
                            />
                          );
                        }
                        const key = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                        const dayEntries = byDate.get(key) ?? [];
                        const isToday =
                          day === today.getDate() &&
                          calMonth === today.getMonth() &&
                          calYear === today.getFullYear();

                        return (
                          <GridItem
                            key={key}
                            minH="90px"
                            p={1.5}
                            borderTop="1px solid"
                            borderLeft={idx % 7 !== 0 ? '1px solid' : undefined}
                            borderColor="border.subtle"
                            bg={isToday ? 'bg.info' : 'bg.surface'}
                          >
                            <Text
                              fontSize="sm"
                              fontWeight={isToday ? 'bold' : 'normal'}
                              color={isToday ? 'blue.600' : 'text.heading'}
                              mb={1}
                            >
                              {day}
                            </Text>

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
                                  <PopoverHeader fontSize="sm" fontWeight="bold">
                                    {entry.merchant_name}
                                  </PopoverHeader>
                                  <PopoverBody fontSize="sm">
                                    <Text>{formatCurrencyShort(entry.amount)}</Text>
                                    <Text color="text.muted" fontSize="xs">{entry.frequency}</Text>
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
                                  <PopoverHeader fontSize="sm" fontWeight="bold">
                                    All bills on {key}
                                  </PopoverHeader>
                                  <PopoverBody>
                                    <VStack align="stretch" spacing={1}>
                                      {dayEntries.map((e, i) => (
                                        <HStack key={i} justify="space-between" fontSize="sm">
                                          <Text noOfLines={1}>{e.merchant_name}</Text>
                                          <Text fontWeight="bold" flexShrink={0}>
                                            {formatCurrencyShort(e.amount)}
                                          </Text>
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
                </VStack>
              )}
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>

      <RecurringTransactionModal
        isOpen={isOpen}
        onClose={onClose}
        recurring={selectedRecurring}
        accounts={accounts || []}
        allMerchants={allMerchants}
        onSave={handleSave}
      />
    </Container>
  );
};

// ─── Recurring bill card ──────────────────────────────────────────────────────

interface RecurringCardProps {
  recurring: RecurringTransaction;
  formatCurrency: (n: number) => string;
  formatDate: (s: string) => string;
  onEdit?: (r: RecurringTransaction) => void;
  onArchive?: (id: string) => void;
  onRestore?: (id: string) => void;
  onApplyLabel?: (id: string) => void;
  isUpdating: boolean;
  isApplyingLabel?: boolean;
  labelMap: Map<string, Label>;
  isArchiveView?: boolean;
  canEdit?: boolean;
}

const RecurringCard: React.FC<RecurringCardProps> = ({
  recurring,
  formatCurrency,
  formatDate,
  onEdit,
  onArchive,
  onRestore,
  onApplyLabel,
  isUpdating,
  isApplyingLabel = false,
  labelMap,
  isArchiveView = false,
  canEdit = true,
}) => {
  const isManual = recurring.is_user_created;
  const isNoLongerFound = recurring.is_no_longer_found && !isManual;
  const attachedLabel = recurring.label_id ? labelMap.get(recurring.label_id) : undefined;

  return (
    <Card
      variant="outline"
      opacity={isArchiveView ? 0.75 : 1}
      borderColor={isNoLongerFound ? 'orange.200' : undefined}
      bg={isNoLongerFound ? 'orange.50' : isArchiveView ? 'gray.50' : 'white'}
    >
      <CardBody>
        <HStack justify="space-between" align="start">
          <VStack align="start" spacing={1} flex={1} minW={0}>
            <HStack flexWrap="wrap" spacing={2}>
              <Text fontWeight="bold" noOfLines={1}>{recurring.merchant_name}</Text>

              {/* Manual vs Auto badge */}
              <Tooltip label={isManual ? 'Manually created' : 'Auto-detected from transactions'}>
                <Badge
                  colorScheme={isManual ? 'purple' : 'blue'}
                  variant="subtle"
                  fontSize="2xs"
                  display="flex"
                  alignItems="center"
                  gap="1"
                >
                  <Icon as={isManual ? FiUser : FiZap} boxSize="2.5" />
                  {isManual ? 'Manual' : 'Auto-synced'}
                </Badge>
              </Tooltip>

              {/* Bill badge */}
              {recurring.is_bill && (
                <Badge colorScheme="orange" variant="subtle" fontSize="2xs">
                  <Icon as={BellIcon} mr="1" />
                  Bill
                </Badge>
              )}

              {/* Label tag */}
              {attachedLabel && (
                <Tooltip label={`Matching transactions tagged "${attachedLabel.name}"`}>
                  <Badge
                    colorScheme="teal"
                    variant="subtle"
                    fontSize="2xs"
                    display="flex"
                    alignItems="center"
                    gap="1"
                    style={{ backgroundColor: attachedLabel.color ? `${attachedLabel.color}22` : undefined,
                             color: attachedLabel.color ?? undefined }}
                  >
                    <Icon as={FiTag} boxSize="2.5" />
                    {attachedLabel.name}
                  </Badge>
                </Tooltip>
              )}

              {/* No longer found */}
              {isNoLongerFound && (
                <Tooltip label="This pattern was not found in your recent transactions. It may have been cancelled.">
                  <Badge colorScheme="orange" variant="solid" fontSize="2xs">
                    No longer found
                  </Badge>
                </Tooltip>
              )}

              {/* Inactive */}
              {!recurring.is_active && !isArchiveView && (
                <Badge colorScheme="gray" fontSize="2xs">Inactive</Badge>
              )}
            </HStack>

            <Text fontSize="sm" color={isArchiveView ? 'gray.500' : 'gray.600'}>
              {recurring.frequency === 'on_demand' ? 'On Demand' : recurring.frequency.charAt(0).toUpperCase() + recurring.frequency.slice(1)} · {formatCurrency(recurring.average_amount)}
            </Text>

            {recurring.next_expected_date && !isArchiveView && (
              <Text fontSize="xs" color="text.muted">
                Next: {formatDate(recurring.next_expected_date)}
              </Text>
            )}

            {isArchiveView && recurring.last_occurrence && (
              <Text fontSize="xs" color="text.muted">
                Last seen: {formatDate(recurring.last_occurrence)}
              </Text>
            )}
          </VStack>

          <HStack spacing={2} flexShrink={0}>
            {isArchiveView ? (
              canEdit && (
                <Tooltip label="Move back to active">
                  <Button
                    size="sm"
                    variant="ghost"
                    leftIcon={<FiRotateCcw />}
                    onClick={() => onRestore?.(recurring.id)}
                    isLoading={isUpdating}
                    colorScheme="blue"
                  >
                    Restore
                  </Button>
                </Tooltip>
              )
            ) : (
              <>
                {canEdit && !attachedLabel && (
                  <Tooltip label='Tag matching transactions as "Recurring Bill"'>
                    <Button
                      size="sm"
                      variant="ghost"
                      leftIcon={<FiTag />}
                      onClick={() => onApplyLabel?.(recurring.id)}
                      isLoading={isApplyingLabel}
                      colorScheme="teal"
                    >
                      Tag
                    </Button>
                  </Tooltip>
                )}
                {canEdit && (
                  <Button size="sm" variant="outline" onClick={() => onEdit?.(recurring)}>
                    Edit
                  </Button>
                )}
                {canEdit && (
                  <Tooltip label="Archive this bill">
                    <Button
                      size="sm"
                      variant="ghost"
                      leftIcon={<FiArchive />}
                      onClick={() => onArchive?.(recurring.id)}
                      isLoading={isUpdating}
                      colorScheme="gray"
                      aria-label="Archive"
                    >
                      Archive
                    </Button>
                  </Tooltip>
                )}
              </>
            )}
          </HStack>
        </HStack>
      </CardBody>
    </Card>
  );
};

// ─── Edit / Create Modal ──────────────────────────────────────────────────────

interface RecurringTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  recurring: RecurringTransaction | null;
  accounts: Account[];
  allMerchants: string[];
  onSave: (data: any, tagTransactions: boolean) => void;
}

const RecurringTransactionModal: React.FC<RecurringTransactionModalProps> = ({
  isOpen,
  onClose,
  recurring,
  accounts,
  allMerchants,
  onSave,
}) => {
  const [formData, setFormData] = useState({
    merchant_name: recurring?.merchant_name || '',
    account_id: recurring?.account_id || '',
    frequency: recurring?.frequency || 'monthly',
    average_amount: recurring?.average_amount || 0,
    amount_variance: recurring?.amount_variance || 5,
    is_bill: recurring?.is_bill || false,
    reminder_days_before: recurring?.reminder_days_before || 3,
    is_active: recurring?.is_active !== undefined ? recurring.is_active : true,
  });
  // Only shown when creating (not editing) — auto-tag matching past transactions
  const [tagTransactions, setTagTransactions] = useState(true);

  // Merchant autocomplete state
  const [merchantQuery, setMerchantQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const merchantInputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Filter client-side — no API calls on each keystroke
  const merchantSuggestions = useMemo(() => {
    if (!merchantQuery.trim()) return [];
    const q = merchantQuery.toLowerCase();
    return allMerchants.filter((m) => m.toLowerCase().includes(q)).slice(0, 10);
  }, [merchantQuery, allMerchants]);

  // Close suggestions on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        !merchantInputRef.current?.contains(e.target as Node) &&
        !suggestionsRef.current?.contains(e.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  React.useEffect(() => {
    if (recurring) {
      setFormData({
        merchant_name: recurring.merchant_name,
        account_id: recurring.account_id,
        frequency: recurring.frequency,
        average_amount: recurring.average_amount,
        amount_variance: recurring.amount_variance,
        is_bill: recurring.is_bill,
        reminder_days_before: recurring.reminder_days_before,
        is_active: recurring.is_active,
      });
      setMerchantQuery(recurring.merchant_name);
    } else {
      setMerchantQuery('');
      setTagTransactions(true); // reset for new bill
    }
  }, [recurring]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          {recurring ? 'Edit Recurring Transaction' : 'Add Recurring Transaction'}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isRequired>
              <FormLabel>Merchant Name</FormLabel>
              <Box position="relative">
                <Input
                  ref={merchantInputRef}
                  value={merchantQuery}
                  onChange={(e) => {
                    setMerchantQuery(e.target.value);
                    setFormData({ ...formData, merchant_name: e.target.value });
                    setShowSuggestions(true);
                  }}
                  onFocus={() => { if (merchantQuery) setShowSuggestions(true); }}
                  placeholder="e.g., Netflix, Electric Company"
                  autoComplete="off"
                />
                {showSuggestions && merchantSuggestions.length > 0 && (
                  <Box
                    ref={suggestionsRef}
                    position="absolute"
                    top="100%"
                    left={0}
                    right={0}
                    zIndex={10}
                    mt={1}
                    bg="bg.surface"
                    borderWidth="1px"
                    borderRadius="md"
                    shadow="md"
                    maxH="200px"
                    overflowY="auto"
                  >
                    <List>
                      {merchantSuggestions.map((name) => (
                        <ListItem
                          key={name}
                          px={3}
                          py={2}
                          cursor="pointer"
                          fontSize="sm"
                          _hover={{ bg: 'bg.subtle' }}
                          onMouseDown={(e) => {
                            e.preventDefault(); // prevent blur before click
                            setMerchantQuery(name);
                            setFormData({ ...formData, merchant_name: name });
                            setShowSuggestions(false);
                          }}
                        >
                          {name}
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </Box>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Account</FormLabel>
              <Select
                value={formData.account_id}
                onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
              >
                <option value="">Select account</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </Select>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Frequency</FormLabel>
              <Select
                value={formData.frequency}
                onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
              >
                <option value="weekly">Weekly</option>
                <option value="biweekly">Biweekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="yearly">Yearly</option>
                <option value="on_demand">On Demand (irregular / as-needed)</option>
              </Select>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Average Amount</FormLabel>
              <NumberInput
                value={formData.average_amount}
                onChange={(_, value) => setFormData({ ...formData, average_amount: value })}
                min={0}
                precision={2}
              >
                <NumberInputField placeholder="0.00" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel>Amount Variance (±)</FormLabel>
              <NumberInput
                value={formData.amount_variance}
                onChange={(_, value) => setFormData({ ...formData, amount_variance: value })}
                min={0}
                precision={2}
              >
                <NumberInputField placeholder="5.00" />
              </NumberInput>
              <FormHelperText>
                Transactions within ±${formData.amount_variance || 5} of the average amount will match this pattern.
              </FormHelperText>
            </FormControl>

            <FormControl display="flex" alignItems="center">
              <FormLabel mb={0}>Enable Reminders</FormLabel>
              <Switch
                isChecked={formData.is_bill}
                onChange={(e) => setFormData({ ...formData, is_bill: e.target.checked })}
              />
            </FormControl>

            {formData.is_bill && (
              <FormControl>
                <FormLabel>Remind Me (Days Before Due)</FormLabel>
                <NumberInput
                  value={formData.reminder_days_before}
                  onChange={(_, value) => setFormData({ ...formData, reminder_days_before: value })}
                  min={0}
                  max={30}
                >
                  <NumberInputField />
                </NumberInput>
              </FormControl>
            )}

            {recurring && (
              <FormControl display="flex" alignItems="center">
                <FormLabel mb={0}>Active</FormLabel>
                <Switch
                  isChecked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
              </FormControl>
            )}

            {/* Transaction tagging — only for new manual bills */}
            {!recurring && (
              <Box w="full" borderWidth="1px" borderRadius="md" p={3} bg="teal.50" borderColor="teal.200">
                <FormControl display="flex" alignItems="start">
                  <Switch
                    mt="3px"
                    isChecked={tagTransactions}
                    onChange={(e) => setTagTransactions(e.target.checked)}
                    colorScheme="teal"
                  />
                  <Box ml={3}>
                    <FormLabel mb={0} fontWeight="semibold" fontSize="sm">
                      Tag matching transactions
                    </FormLabel>
                    <Text fontSize="xs" color="text.secondary" mt={0.5}>
                      {tagTransactions
                        ? 'Applies a "Recurring Bill" label to past and future transactions matching this merchant + account.'
                        : 'No label will be applied. You can tag transactions later from the bill card.'}
                    </Text>
                  </Box>
                </FormControl>
              </Box>
            )}
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={() => onSave(formData, tagTransactions)}
            isDisabled={!formData.merchant_name.trim() || !formData.account_id}
          >
            Save
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default BillsPage;
