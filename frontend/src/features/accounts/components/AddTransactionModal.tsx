import {
  Button,
  ButtonGroup,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  NumberInput,
  NumberInputField,
  Text,
  VStack,
  useToast,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../../services/api';

interface AddTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  accountId: string;
  accountName: string;
}

/**
 * Follows Plaid/system convention:
 *   positive amount = expense / charge (money leaving)
 *   negative amount = income / deposit (money arriving)
 */
export const AddTransactionModal = ({
  isOpen,
  onClose,
  accountId,
  accountName,
}: AddTransactionModalProps) => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const today = new Date().toISOString().split('T')[0];

  const [date, setDate] = useState(today);
  const [merchant, setMerchant] = useState('');
  const [amount, setAmount] = useState('');
  const [isExpense, setIsExpense] = useState(true);

  const mutation = useMutation({
    mutationFn: async () => {
      const value = parseFloat(amount);
      // Expenses are stored as positive; income as negative
      const signedAmount = isExpense ? Math.abs(value) : -Math.abs(value);
      const response = await api.post('/transactions/', {
        account_id: accountId,
        date,
        amount: signedAmount,
        merchant_name: merchant || undefined,
        description: merchant || undefined,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions', accountId] });
      queryClient.invalidateQueries({ queryKey: ['account', accountId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      toast({ title: 'Transaction added', status: 'success', duration: 3000 });
      setDate(today);
      setMerchant('');
      setAmount('');
      setIsExpense(true);
      onClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to add transaction',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Add Transaction — {accountName}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl>
              <FormLabel fontSize="sm">Type</FormLabel>
              <ButtonGroup size="sm" isAttached width="full">
                <Button
                  flex={1}
                  colorScheme={isExpense ? 'red' : 'gray'}
                  variant={isExpense ? 'solid' : 'outline'}
                  onClick={() => setIsExpense(true)}
                >
                  Expense / Charge
                </Button>
                <Button
                  flex={1}
                  colorScheme={!isExpense ? 'green' : 'gray'}
                  variant={!isExpense ? 'solid' : 'outline'}
                  onClick={() => setIsExpense(false)}
                >
                  Income / Deposit
                </Button>
              </ButtonGroup>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">Date</FormLabel>
              <Input
                type="date"
                size="sm"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Merchant / Description</FormLabel>
              <Input
                size="sm"
                value={merchant}
                onChange={(e) => setMerchant(e.target.value)}
                placeholder="e.g., Amazon, Paycheck"
                maxLength={100}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">Amount</FormLabel>
              <HStack>
                <Text fontSize="sm">$</Text>
                <NumberInput
                  value={amount}
                  onChange={setAmount}
                  min={0.01}
                  precision={2}
                  size="sm"
                >
                  <NumberInputField placeholder="0.00" />
                </NumberInput>
              </HStack>
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button
            variant="ghost"
            mr={3}
            onClick={onClose}
            isDisabled={mutation.isPending}
          >
            Cancel
          </Button>
          <Button
            colorScheme="brand"
            onClick={() => mutation.mutate()}
            isLoading={mutation.isPending}
            isDisabled={!date || !amount}
          >
            Add Transaction
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
