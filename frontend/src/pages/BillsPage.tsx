import React, { useState } from 'react';
import {
  Box,
  Container,
  Heading,
  VStack,
  HStack,
  Card,
  CardBody,
  Text,
  Badge,
  Button,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  ModalFooter,
  FormControl,
  FormLabel,
  Input,
  Select,
  NumberInput,
  NumberInputField,
  Switch,
  useToast,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Divider,
  Icon,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
} from '@chakra-ui/react';
import { AddIcon, BellIcon, CalendarIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recurringTransactionsApi } from '../api/recurring-transactions';
import { RecurringTransaction, UpcomingBill } from '../types/recurring-transaction';
import api from '../services/api';

interface Account {
  id: string;
  name: string;
}

const BillsPage: React.FC = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedRecurring, setSelectedRecurring] = useState<RecurringTransaction | null>(null);

  // Fetch upcoming bills
  const { data: upcomingBills, isLoading: billsLoading } = useQuery<UpcomingBill[]>({
    queryKey: ['upcoming-bills'],
    queryFn: () => recurringTransactionsApi.getUpcomingBills(30),
  });

  // Fetch all recurring transactions
  const { data: recurringTransactions, isLoading: recurringLoading } = useQuery<RecurringTransaction[]>({
    queryKey: ['recurring-transactions'],
    queryFn: () => recurringTransactionsApi.getAll(),
  });

  // Fetch accounts for dropdown
  const { data: accounts } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: async () => {
      const response = await api.get('/accounts/');
      return response.data;
    },
  });

  // Update recurring transaction mutation
  const updateRecurringMutation = useMutation({
    mutationFn: async (data: { id: string; updates: any }) => {
      return recurringTransactionsApi.update(data.id, data.updates);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['upcoming-bills'] });
      toast({
        title: 'Bill updated',
        status: 'success',
        duration: 3000,
      });
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

  // Create manual recurring transaction mutation
  const createRecurringMutation = useMutation({
    mutationFn: async (data: any) => {
      return recurringTransactionsApi.create(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['upcoming-bills'] });
      toast({
        title: 'Bill created',
        status: 'success',
        duration: 3000,
      });
      onClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Error creating bill',
        description: error.response?.data?.detail || 'Failed to create bill',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleEditRecurring = (recurring: RecurringTransaction) => {
    setSelectedRecurring(recurring);
    onOpen();
  };

  const handleCreateNew = () => {
    setSelectedRecurring(null);
    onOpen();
  };

  const handleSave = (formData: any) => {
    if (selectedRecurring) {
      // Update existing
      updateRecurringMutation.mutate({
        id: selectedRecurring.id,
        updates: formData,
      });
    } else {
      // Create new
      createRecurringMutation.mutate(formData);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getDueDateColor = (daysUntilDue: number, isOverdue: boolean) => {
    if (isOverdue) return 'red';
    if (daysUntilDue <= 3) return 'orange';
    if (daysUntilDue <= 7) return 'yellow';
    return 'green';
  };

  if (billsLoading || recurringLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Spinner />
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between">
          <Heading size="lg">Bill Reminders</Heading>
          <Button leftIcon={<AddIcon />} colorScheme="blue" onClick={handleCreateNew}>
            Add Bill
          </Button>
        </HStack>

        {/* Upcoming Bills Section */}
        <Box>
          <Heading size="md" mb={4}>
            <Icon as={BellIcon} mr={2} />
            Upcoming Bills (Next 30 Days)
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
                          <Icon as={CalendarIcon} color="gray.500" />
                          <Text fontSize="sm" color="gray.600">
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
                You have no bills due in the next 30 days. Add recurring transactions and mark them as bills to track due dates.
              </AlertDescription>
            </Alert>
          )}
        </Box>

        <Divider />

        {/* All Recurring Transactions */}
        <Box>
          <Heading size="md" mb={4}>
            All Recurring Transactions
          </Heading>

          {recurringTransactions && recurringTransactions.length > 0 ? (
            <VStack spacing={3} align="stretch">
              {recurringTransactions.map((recurring) => (
                <Card key={recurring.id} variant="outline">
                  <CardBody>
                    <HStack justify="space-between">
                      <VStack align="start" spacing={1}>
                        <HStack>
                          <Text fontWeight="bold">{recurring.merchant_name}</Text>
                          {recurring.is_bill && (
                            <Badge colorScheme="purple">
                              <Icon as={BellIcon} mr={1} />
                              Bill
                            </Badge>
                          )}
                          {!recurring.is_active && <Badge colorScheme="gray">Inactive</Badge>}
                        </HStack>
                        <Text fontSize="sm" color="gray.600">
                          {recurring.frequency} • {formatCurrency(recurring.average_amount)}
                        </Text>
                        {recurring.next_expected_date && (
                          <Text fontSize="xs" color="gray.500">
                            Next: {formatDate(recurring.next_expected_date)}
                          </Text>
                        )}
                      </VStack>

                      <Button size="sm" variant="outline" onClick={() => handleEditRecurring(recurring)}>
                        Edit
                      </Button>
                    </HStack>
                  </CardBody>
                </Card>
              ))}
            </VStack>
          ) : (
            <Alert status="info">
              <AlertIcon />
              <AlertTitle>No recurring transactions</AlertTitle>
              <AlertDescription>
                Create recurring transactions to track bills and subscriptions. You can also run auto-detection to find patterns in your transactions.
              </AlertDescription>
            </Alert>
          )}
        </Box>
      </VStack>

      {/* Edit/Create Modal */}
      <RecurringTransactionModal
        isOpen={isOpen}
        onClose={onClose}
        recurring={selectedRecurring}
        accounts={accounts || []}
        onSave={handleSave}
      />
    </Container>
  );
};

// Modal Component
interface RecurringTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  recurring: RecurringTransaction | null;
  accounts: Account[];
  onSave: (data: any) => void;
}

const RecurringTransactionModal: React.FC<RecurringTransactionModalProps> = ({
  isOpen,
  onClose,
  recurring,
  accounts,
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
    }
  }, [recurring]);

  const handleSubmit = () => {
    onSave(formData);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{recurring ? 'Edit Recurring Transaction' : 'Add Recurring Transaction'}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isRequired>
              <FormLabel>Merchant Name</FormLabel>
              <Input
                value={formData.merchant_name}
                onChange={(e) => setFormData({ ...formData, merchant_name: e.target.value })}
                placeholder="e.g., Netflix, Electric Company"
              />
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
            </FormControl>

            <FormControl display="flex" alignItems="center">
              <FormLabel mb={0}>Mark as Bill (Enable Reminders)</FormLabel>
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
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button colorScheme="blue" onClick={handleSubmit}>
            Save
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default BillsPage;
