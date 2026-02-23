/**
 * Recurring Transactions page - view and manage recurring patterns
 */

import {
  Box,
  Button,
  Heading,
  HStack,
  Text,
  VStack,
  Spinner,
  Center,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  IconButton,
  useToast,
  Card,
  CardBody,
  Tooltip,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  Select,
  NumberInput,
  NumberInputField,
  Switch,
  useDisclosure,
} from '@chakra-ui/react';
import { RepeatIcon, DeleteIcon, EditIcon, AddIcon } from '@chakra-ui/icons';
import { FiLock, FiRepeat, FiPause, FiPlay } from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useMemo, useRef, useEffect } from 'react';
import { recurringTransactionsApi } from '../api/recurring-transactions';
import { RecurringFrequency, type RecurringTransaction, type RecurringTransactionCreate } from '../types/recurring-transaction';
import { useUserView } from '../contexts/UserViewContext';
import { EmptyState } from '../components/EmptyState';
import { accountsApi } from '../api/accounts';
import api from '../services/api';

export default function RecurringTransactionsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { canWriteResource, isOtherUserView } = useUserView();
  const canEdit = canWriteResource('recurring_transaction');
  const [tabIndex, setTabIndex] = useState(0);

  // Edit modal
  const { isOpen: isEditOpen, onOpen: onEditOpen, onClose: onEditClose } = useDisclosure();
  const [editingPattern, setEditingPattern] = useState<RecurringTransaction | null>(null);
  const [editForm, setEditForm] = useState({
    merchant_name: '',
    frequency: RecurringFrequency.MONTHLY,
    average_amount: '',
    is_bill: false,
    reminder_days_before: 3,
  });

  // Add modal
  const { isOpen: isAddOpen, onOpen: onAddOpen, onClose: onAddClose } = useDisclosure();
  const [addForm, setAddForm] = useState({
    merchant_name: '',
    account_id: '',
    frequency: RecurringFrequency.MONTHLY,
    average_amount: '',
    is_bill: false,
    reminder_days_before: 3,
  });

  // Merchant autocomplete state — edit modal
  const [editMerchantQuery, setEditMerchantQuery] = useState('');
  const [editShowSuggestions, setEditShowSuggestions] = useState(false);
  const editMerchantInputRef = useRef<HTMLInputElement>(null);
  const editSuggestionsRef = useRef<HTMLDivElement>(null);

  // Merchant autocomplete state — add modal
  const [addMerchantQuery, setAddMerchantQuery] = useState('');
  const [addShowSuggestions, setAddShowSuggestions] = useState(false);
  const addMerchantInputRef = useRef<HTMLInputElement>(null);
  const addSuggestionsRef = useRef<HTMLDivElement>(null);

  // Fetch merchants for autocomplete
  const { data: allMerchants = [] } = useQuery({
    queryKey: ['transaction-merchants'],
    queryFn: () => api.get<{ merchants: string[] }>('/transactions/merchants').then((r) => r.data.merchants),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch accounts for the create modal account selector
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => accountsApi.getAccounts(),
  });

  // Filter merchant suggestions — edit modal
  const editMerchantSuggestions = useMemo(() => {
    if (!editMerchantQuery.trim()) return [];
    const q = editMerchantQuery.toLowerCase();
    return allMerchants.filter((m) => m.toLowerCase().includes(q)).slice(0, 10);
  }, [editMerchantQuery, allMerchants]);

  // Filter merchant suggestions — add modal
  const addMerchantSuggestions = useMemo(() => {
    if (!addMerchantQuery.trim()) return [];
    const q = addMerchantQuery.toLowerCase();
    return allMerchants.filter((m) => m.toLowerCase().includes(q)).slice(0, 10);
  }, [addMerchantQuery, allMerchants]);

  // Close edit modal suggestions on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        editMerchantInputRef.current &&
        !editMerchantInputRef.current.contains(e.target as Node) &&
        editSuggestionsRef.current &&
        !editSuggestionsRef.current.contains(e.target as Node)
      ) {
        setEditShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Close add modal suggestions on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        addMerchantInputRef.current &&
        !addMerchantInputRef.current.contains(e.target as Node) &&
        addSuggestionsRef.current &&
        !addSuggestionsRef.current.contains(e.target as Node)
      ) {
        setAddShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Get all recurring patterns
  const { data: patterns = [], isLoading } = useQuery({
    queryKey: ['recurring-transactions'],
    queryFn: () => recurringTransactionsApi.getAll(),
  });

  // Filter for subscriptions: active monthly/yearly with high confidence (>70%)
  // Matches the /subscriptions API definition — inactive patterns excluded here
  const subscriptions = useMemo(() => {
    return patterns.filter(
      (pattern) =>
        pattern.is_active &&
        (pattern.frequency === RecurringFrequency.MONTHLY ||
          pattern.frequency === RecurringFrequency.YEARLY) &&
        (pattern.confidence_score ?? 0) >= 0.7
    );
  }, [patterns]);

  // Calculate subscription summary
  const subscriptionSummary = useMemo(() => {
    const monthlyTotal = subscriptions.reduce((sum, sub) => {
      const amount = Math.abs(sub.average_amount);
      if (sub.frequency === RecurringFrequency.MONTHLY) {
        return sum + amount;
      } else if (sub.frequency === RecurringFrequency.YEARLY) {
        return sum + amount / 12;
      }
      return sum;
    }, 0);

    return {
      count: subscriptions.length,
      monthlyTotal,
      yearlyTotal: monthlyTotal * 12,
    };
  }, [subscriptions]);

  // Detect patterns mutation
  const detectMutation = useMutation({
    mutationFn: () => recurringTransactionsApi.detectPatterns(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      toast({
        title: `Detected ${data.detected_patterns} recurring patterns`,
        status: 'success',
        duration: 3000,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to detect patterns',
        status: 'error',
        duration: 3000,
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => recurringTransactionsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      toast({
        title: 'Pattern deleted',
        status: 'success',
        duration: 2000,
      });
    },
  });

  // Edit mutation
  const editMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: typeof editForm }) =>
      recurringTransactionsApi.update(id, {
        merchant_name: updates.merchant_name,
        frequency: updates.frequency,
        average_amount: parseFloat(updates.average_amount) || 0,
        is_bill: updates.is_bill,
        reminder_days_before: updates.reminder_days_before,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      toast({ title: 'Pattern updated', status: 'success', duration: 2000 });
      onEditClose();
    },
    onError: () => {
      toast({ title: 'Failed to update pattern', status: 'error', duration: 3000 });
    },
  });

  // Toggle active/inactive mutation
  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      recurringTransactionsApi.update(id, { is_active }),
    onSuccess: (_, { is_active }) => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
      queryClient.invalidateQueries({ queryKey: ['subscriptions-widget'] });
      toast({
        title: is_active ? 'Pattern reactivated' : 'Pattern deactivated',
        description: is_active
          ? 'This pattern will be included in forecasts again.'
          : 'This pattern is paused and excluded from forecasts.',
        status: is_active ? 'success' : 'info',
        duration: 3000,
      });
    },
    onError: () => {
      toast({ title: 'Failed to update pattern', status: 'error', duration: 3000 });
    },
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: RecurringTransactionCreate) => recurringTransactionsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      toast({ title: 'Recurring transaction added', status: 'success', duration: 2000 });
      onAddClose();
      setAddForm({
        merchant_name: '',
        account_id: '',
        frequency: RecurringFrequency.MONTHLY,
        average_amount: '',
        is_bill: false,
        reminder_days_before: 3,
      });
      setAddMerchantQuery('');
    },
    onError: () => {
      toast({ title: 'Failed to add recurring transaction', status: 'error', duration: 3000 });
    },
  });

  const openEdit = (pattern: RecurringTransaction) => {
    setEditingPattern(pattern);
    setEditForm({
      merchant_name: pattern.merchant_name,
      frequency: pattern.frequency,
      average_amount: String(Math.abs(pattern.average_amount)),
      is_bill: pattern.is_bill,
      reminder_days_before: pattern.reminder_days_before,
    });
    setEditMerchantQuery(pattern.merchant_name);
    onEditOpen();
  };

  const handleEditSave = () => {
    if (!editingPattern) return;
    editMutation.mutate({ id: editingPattern.id, updates: editForm });
  };

  const handleAddSave = () => {
    if (!addForm.merchant_name.trim() || !addForm.account_id) return;
    createMutation.mutate({
      merchant_name: addForm.merchant_name,
      account_id: addForm.account_id,
      frequency: addForm.frequency,
      average_amount: parseFloat(addForm.average_amount) || 0,
      is_bill: addForm.is_bill,
      reminder_days_before: addForm.reminder_days_before,
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatFrequency = (frequency: RecurringFrequency) => {
    switch (frequency) {
      case RecurringFrequency.WEEKLY:
        return 'Weekly';
      case RecurringFrequency.BIWEEKLY:
        return 'Bi-weekly';
      case RecurringFrequency.MONTHLY:
        return 'Monthly';
      case RecurringFrequency.QUARTERLY:
        return 'Quarterly';
      case RecurringFrequency.YEARLY:
        return 'Yearly';
      case RecurringFrequency.ON_DEMAND:
        return 'On Demand';
    }
  };

  const actionButtons = (pattern: RecurringTransaction) => (
    <HStack spacing={1}>
      <Tooltip
        label={!canEdit ? 'Read-only' : 'Edit pattern'}
        placement="top"
        isDisabled={canEdit}
      >
        <IconButton
          aria-label="Edit"
          icon={!canEdit ? <FiLock /> : <EditIcon />}
          size="sm"
          variant="ghost"
          colorScheme={!canEdit ? 'gray' : 'blue'}
          onClick={() => openEdit(pattern)}
          isDisabled={!canEdit}
        />
      </Tooltip>
      <Tooltip
        label={
          !canEdit
            ? 'Read-only'
            : pattern.is_active
            ? 'Deactivate (excludes from forecasts; auto-reactivates if transactions resume)'
            : 'Reactivate (include in forecasts again)'
        }
        placement="top"
        isDisabled={false}
      >
        <IconButton
          aria-label={pattern.is_active ? 'Deactivate' : 'Reactivate'}
          icon={pattern.is_active ? <FiPause /> : <FiPlay />}
          size="sm"
          variant="ghost"
          colorScheme={!canEdit ? 'gray' : pattern.is_active ? 'orange' : 'green'}
          onClick={() =>
            toggleActiveMutation.mutate({ id: pattern.id, is_active: !pattern.is_active })
          }
          isLoading={toggleActiveMutation.isPending}
          isDisabled={!canEdit}
        />
      </Tooltip>
      <Tooltip
        label={!canEdit ? 'Read-only: You can only delete your own patterns' : 'Delete pattern'}
        placement="top"
        isDisabled={canEdit}
      >
        <IconButton
          aria-label="Delete"
          icon={!canEdit ? <FiLock /> : <DeleteIcon />}
          size="sm"
          variant="ghost"
          colorScheme={!canEdit ? 'gray' : 'red'}
          onClick={() => deleteMutation.mutate(pattern.id)}
          isLoading={deleteMutation.isPending}
          isDisabled={!canEdit}
        />
      </Tooltip>
    </HStack>
  );

  // Shared merchant autocomplete dropdown renderer
  const MerchantSuggestions = ({
    suggestions,
    suggestionsRef: ref,
    onSelect,
  }: {
    suggestions: string[];
    suggestionsRef: React.RefObject<HTMLDivElement>;
    onSelect: (merchant: string) => void;
  }) =>
    suggestions.length > 0 ? (
      <Box
        ref={ref}
        position="absolute"
        top="100%"
        left={0}
        right={0}
        zIndex={10}
        bg="white"
        border="1px solid"
        borderColor="gray.200"
        borderRadius="md"
        boxShadow="md"
        maxH="200px"
        overflowY="auto"
      >
        {suggestions.map((m) => (
          <Box
            key={m}
            px={3}
            py={2}
            cursor="pointer"
            _hover={{ bg: 'gray.100' }}
            onMouseDown={(e) => {
              e.preventDefault();
              onSelect(m);
            }}
          >
            {m}
          </Box>
        ))}
      </Box>
    ) : null;

  return (
    <Box p={8}>
      <VStack align="stretch" spacing={6}>
        {/* Read-only banner */}
        {isOtherUserView && !canEdit && (
          <Box p={4} bg="orange.50" borderRadius="md" borderWidth={1} borderColor="orange.200">
            <HStack>
              <FiLock size={16} color="orange.600" />
              <Text fontSize="sm" color="orange.800" fontWeight="medium">
                Read-only view: You can view patterns but cannot detect new ones or delete existing patterns for another household member.
              </Text>
            </HStack>
          </Box>
        )}

        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="lg">Recurring Transactions & Subscriptions</Heading>
            <Text color="gray.600">
              Auto-detected patterns and subscription charges
            </Text>
          </VStack>
          <HStack spacing={2}>
            <Tooltip
              label={!canEdit ? "Read-only: You can only add patterns for your own data" : ""}
              placement="top"
              isDisabled={canEdit}
            >
              <Button
                leftIcon={canEdit ? <AddIcon /> : <FiLock />}
                variant="outline"
                colorScheme="brand"
                onClick={onAddOpen}
                isDisabled={!canEdit}
              >
                Add Recurring
              </Button>
            </Tooltip>
            <Tooltip
              label={!canEdit ? "Read-only: You can only detect patterns for your own data" : ""}
              placement="top"
              isDisabled={canEdit}
            >
              <Button
                leftIcon={canEdit ? <RepeatIcon /> : <FiLock />}
                colorScheme="blue"
                onClick={() => detectMutation.mutate()}
                isLoading={detectMutation.isPending}
                isDisabled={!canEdit}
              >
                Detect Patterns
              </Button>
            </Tooltip>
          </HStack>
        </HStack>

        {/* Loading state */}
        {isLoading && (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        )}

        {/* Empty state */}
        {!isLoading && patterns.length === 0 && (
          <VStack spacing={4}>
            <EmptyState
              icon={FiRepeat}
              title={isOtherUserView
                ? "This user has no recurring patterns detected yet"
                : "No recurring patterns detected yet"}
              description="Automatically detect subscription payments, bills, and other recurring transactions in your history — or add one manually."
              actionLabel="Detect Patterns Now"
              onAction={() => detectMutation.mutate()}
              showAction={canEdit}
            />
            {canEdit && (
              <Button variant="outline" colorScheme="brand" leftIcon={<AddIcon />} onClick={onAddOpen}>
                Add Manually
              </Button>
            )}
          </VStack>
        )}

        {/* Tabs for All Recurring vs Subscriptions */}
        {!isLoading && patterns.length > 0 && (
          <Tabs index={tabIndex} onChange={setTabIndex} colorScheme="brand">
            <TabList>
              <Tab>All Recurring ({patterns.length})</Tab>
              <Tab>Active Subscriptions ({subscriptions.length})</Tab>
            </TabList>

            <TabPanels>
              {/* All Recurring Tab */}
              <TabPanel px={0}>
                <VStack align="stretch" spacing={6}>
                  <Card>
                    <CardBody p={0}>
                      <Box overflowX="auto">
                        <Table variant="simple">
                          <Thead>
                            <Tr>
                              <Th>Merchant</Th>
                              <Th>Frequency</Th>
                              <Th isNumeric>Amount</Th>
                              <Th>Occurrences</Th>
                              <Th>Next Expected</Th>
                              <Th>Confidence</Th>
                              <Th>Type</Th>
                              <Th>Actions</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {patterns.map((pattern) => (
                              <Tr
                                key={pattern.id}
                                opacity={pattern.is_active ? 1 : 0.5}
                                bg={pattern.is_active ? undefined : 'gray.50'}
                              >
                                <Td fontWeight="medium">{pattern.merchant_name}</Td>
                                <Td>
                                  <Badge colorScheme="blue">
                                    {formatFrequency(pattern.frequency)}
                                  </Badge>
                                </Td>
                                <Td isNumeric>{formatCurrency(pattern.average_amount)}</Td>
                                <Td>{pattern.occurrence_count}×</Td>
                                <Td>
                                  {pattern.next_expected_date
                                    ? new Date(pattern.next_expected_date).toLocaleDateString()
                                    : '—'}
                                </Td>
                                <Td>
                                  {pattern.confidence_score !== null && (
                                    <Badge
                                      colorScheme={
                                        pattern.confidence_score >= 0.8
                                          ? 'green'
                                          : pattern.confidence_score >= 0.6
                                          ? 'yellow'
                                          : 'orange'
                                      }
                                    >
                                      {(pattern.confidence_score * 100).toFixed(0)}%
                                    </Badge>
                                  )}
                                </Td>
                                <Td>
                                  <HStack spacing={1}>
                                    <Badge colorScheme={pattern.is_user_created ? 'purple' : 'gray'}>
                                      {pattern.is_user_created ? 'Manual' : 'Auto'}
                                    </Badge>
                                    {!pattern.is_active && (
                                      <Badge colorScheme="orange">Inactive</Badge>
                                    )}
                                  </HStack>
                                </Td>
                                <Td>{actionButtons(pattern)}</Td>
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                      </Box>
                    </CardBody>
                  </Card>

                  <Box p={4} bg="blue.50" borderRadius="md">
                    <Text fontSize="sm" color="gray.700">
                      💡 <strong>Tip:</strong> Patterns are auto-detected from your transaction history.
                      Use <strong>Add Recurring</strong> to add one manually. Click{' '}
                      <strong>pause</strong> to deactivate a pattern — it will be excluded from cash flow
                      forecasts and the Subscriptions tab. If transactions for a deactivated pattern are
                      detected again, it will be <strong>automatically reactivated</strong>.
                    </Text>
                  </Box>
                </VStack>
              </TabPanel>

              {/* Subscriptions Tab */}
              <TabPanel px={0}>
                <VStack align="stretch" spacing={6}>
                  {/* Summary Cards */}
                  <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
                    <Card>
                      <CardBody>
                        <Stat>
                          <StatLabel>Active Subscriptions</StatLabel>
                          <StatNumber>{subscriptionSummary.count}</StatNumber>
                          <StatHelpText>Monthly & yearly charges</StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>

                    <Card>
                      <CardBody>
                        <Stat>
                          <StatLabel>Monthly Cost</StatLabel>
                          <StatNumber color="red.600">
                            {formatCurrency(subscriptionSummary.monthlyTotal)}
                          </StatNumber>
                          <StatHelpText>Recurring charges</StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>

                    <Card>
                      <CardBody>
                        <Stat>
                          <StatLabel>Yearly Cost</StatLabel>
                          <StatNumber>
                            {formatCurrency(subscriptionSummary.yearlyTotal)}
                          </StatNumber>
                          <StatHelpText>Annual total</StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>
                  </SimpleGrid>

                  {/* Subscriptions table */}
                  {subscriptions.length > 0 ? (
                    <Card>
                      <CardBody p={0}>
                        <Box overflowX="auto">
                          <Table variant="simple">
                            <Thead>
                              <Tr>
                                <Th>Service</Th>
                                <Th>Frequency</Th>
                                <Th isNumeric>Amount</Th>
                                <Th>Next Charge</Th>
                                <Th>Confidence</Th>
                                <Th>Actions</Th>
                              </Tr>
                            </Thead>
                            <Tbody>
                              {subscriptions.map((sub) => (
                                <Tr key={sub.id}>
                                  <Td fontWeight="medium">{sub.merchant_name}</Td>
                                  <Td>
                                    <Badge colorScheme="purple">
                                      {formatFrequency(sub.frequency)}
                                    </Badge>
                                  </Td>
                                  <Td isNumeric>{formatCurrency(Math.abs(sub.average_amount))}</Td>
                                  <Td>
                                    {sub.next_expected_date
                                      ? new Date(sub.next_expected_date).toLocaleDateString()
                                      : '—'}
                                  </Td>
                                  <Td>
                                    <Badge
                                      colorScheme={(sub.confidence_score ?? 0) >= 0.85 ? 'green' : 'yellow'}
                                    >
                                      {((sub.confidence_score ?? 0) * 100).toFixed(0)}%
                                    </Badge>
                                  </Td>
                                  <Td>{actionButtons(sub)}</Td>
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                        </Box>
                      </CardBody>
                    </Card>
                  ) : (
                    <EmptyState
                      icon={FiRepeat}
                      title="No subscriptions detected"
                      description="We'll automatically detect recurring monthly and yearly charges as transactions are imported."
                    />
                  )}

                  <Box p={4} bg="purple.50" borderRadius="md">
                    <Text fontSize="sm" color="gray.700">
                      💡 <strong>Subscriptions</strong> are recurring charges that happen monthly or yearly
                      with high confidence (70%+). They are auto-detected from your transaction history.
                      To manually track a subscription not yet imported, use{' '}
                      <strong>Add Recurring</strong> (top-right) and set the frequency to Monthly or Yearly
                      — it will appear here once detected with high confidence.
                    </Text>
                  </Box>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        )}
      </VStack>

      {/* Edit Pattern Modal */}
      <Modal isOpen={isEditOpen} onClose={onEditClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Edit Recurring Pattern</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl position="relative">
                <FormLabel>Merchant / Service Name</FormLabel>
                <Input
                  ref={editMerchantInputRef}
                  value={editMerchantQuery}
                  onChange={(e) => {
                    setEditMerchantQuery(e.target.value);
                    setEditForm((f) => ({ ...f, merchant_name: e.target.value }));
                    setEditShowSuggestions(true);
                  }}
                  onFocus={() => setEditShowSuggestions(true)}
                  placeholder="e.g. Netflix"
                />
                {editShowSuggestions && (
                  <MerchantSuggestions
                    suggestions={editMerchantSuggestions}
                    suggestionsRef={editSuggestionsRef}
                    onSelect={(m) => {
                      setEditMerchantQuery(m);
                      setEditForm((f) => ({ ...f, merchant_name: m }));
                      setEditShowSuggestions(false);
                    }}
                  />
                )}
              </FormControl>

              <FormControl>
                <FormLabel>Frequency</FormLabel>
                <Select
                  value={editForm.frequency}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, frequency: e.target.value as RecurringFrequency }))
                  }
                >
                  <option value={RecurringFrequency.WEEKLY}>Weekly</option>
                  <option value={RecurringFrequency.BIWEEKLY}>Bi-weekly</option>
                  <option value={RecurringFrequency.MONTHLY}>Monthly</option>
                  <option value={RecurringFrequency.QUARTERLY}>Quarterly</option>
                  <option value={RecurringFrequency.YEARLY}>Yearly</option>
                  <option value={RecurringFrequency.ON_DEMAND}>On Demand</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Typical Amount ($)</FormLabel>
                <NumberInput
                  min={0}
                  precision={2}
                  value={editForm.average_amount}
                  onChange={(val) => setEditForm((f) => ({ ...f, average_amount: val }))}
                >
                  <NumberInputField placeholder="e.g. 15.99" />
                </NumberInput>
              </FormControl>

              <FormControl>
                <HStack justify="space-between">
                  <FormLabel mb={0}>Mark as Bill</FormLabel>
                  <Switch
                    isChecked={editForm.is_bill}
                    onChange={(e) => setEditForm((f) => ({ ...f, is_bill: e.target.checked }))}
                    colorScheme="brand"
                  />
                </HStack>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Bills appear in the upcoming bills calendar and trigger reminders.
                </Text>
              </FormControl>

              {editForm.is_bill && (
                <FormControl>
                  <FormLabel>Reminder (days before due)</FormLabel>
                  <NumberInput
                    min={0}
                    max={30}
                    value={editForm.reminder_days_before}
                    onChange={(_, val) =>
                      setEditForm((f) => ({ ...f, reminder_days_before: isNaN(val) ? 3 : val }))
                    }
                  >
                    <NumberInputField />
                  </NumberInput>
                </FormControl>
              )}
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onEditClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              onClick={handleEditSave}
              isLoading={editMutation.isPending}
              isDisabled={!editForm.merchant_name.trim()}
            >
              Save Changes
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Add Recurring Pattern Modal */}
      <Modal isOpen={isAddOpen} onClose={onAddClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Add Recurring Transaction</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl position="relative" isRequired>
                <FormLabel>Merchant / Service Name</FormLabel>
                <Input
                  ref={addMerchantInputRef}
                  value={addMerchantQuery}
                  onChange={(e) => {
                    setAddMerchantQuery(e.target.value);
                    setAddForm((f) => ({ ...f, merchant_name: e.target.value }));
                    setAddShowSuggestions(true);
                  }}
                  onFocus={() => setAddShowSuggestions(true)}
                  placeholder="e.g. Netflix"
                />
                {addShowSuggestions && (
                  <MerchantSuggestions
                    suggestions={addMerchantSuggestions}
                    suggestionsRef={addSuggestionsRef}
                    onSelect={(m) => {
                      setAddMerchantQuery(m);
                      setAddForm((f) => ({ ...f, merchant_name: m }));
                      setAddShowSuggestions(false);
                    }}
                  />
                )}
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Account</FormLabel>
                <Select
                  value={addForm.account_id}
                  onChange={(e) => setAddForm((f) => ({ ...f, account_id: e.target.value }))}
                  placeholder="Select account"
                >
                  {accounts.map((acct) => (
                    <option key={acct.id} value={acct.id}>
                      {acct.name}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Frequency</FormLabel>
                <Select
                  value={addForm.frequency}
                  onChange={(e) =>
                    setAddForm((f) => ({ ...f, frequency: e.target.value as RecurringFrequency }))
                  }
                >
                  <option value={RecurringFrequency.WEEKLY}>Weekly</option>
                  <option value={RecurringFrequency.BIWEEKLY}>Bi-weekly</option>
                  <option value={RecurringFrequency.MONTHLY}>Monthly</option>
                  <option value={RecurringFrequency.QUARTERLY}>Quarterly</option>
                  <option value={RecurringFrequency.YEARLY}>Yearly</option>
                  <option value={RecurringFrequency.ON_DEMAND}>On Demand</option>
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Typical Amount ($)</FormLabel>
                <NumberInput
                  min={0}
                  precision={2}
                  value={addForm.average_amount}
                  onChange={(val) => setAddForm((f) => ({ ...f, average_amount: val }))}
                >
                  <NumberInputField placeholder="e.g. 15.99" />
                </NumberInput>
              </FormControl>

              <FormControl>
                <HStack justify="space-between">
                  <FormLabel mb={0}>Mark as Bill</FormLabel>
                  <Switch
                    isChecked={addForm.is_bill}
                    onChange={(e) => setAddForm((f) => ({ ...f, is_bill: e.target.checked }))}
                    colorScheme="brand"
                  />
                </HStack>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Bills appear in the upcoming bills calendar and trigger reminders.
                </Text>
              </FormControl>

              {addForm.is_bill && (
                <FormControl>
                  <FormLabel>Reminder (days before due)</FormLabel>
                  <NumberInput
                    min={0}
                    max={30}
                    value={addForm.reminder_days_before}
                    onChange={(_, val) =>
                      setAddForm((f) => ({ ...f, reminder_days_before: isNaN(val) ? 3 : val }))
                    }
                  >
                    <NumberInputField />
                  </NumberInput>
                </FormControl>
              )}
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onAddClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              onClick={handleAddSave}
              isLoading={createMutation.isPending}
              isDisabled={!addForm.merchant_name.trim() || !addForm.account_id}
            >
              Add Recurring
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
