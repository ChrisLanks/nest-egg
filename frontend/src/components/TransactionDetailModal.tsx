/**
 * Transaction detail modal with editing and labeling
 */

import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  FormControl,
  FormLabel,
  Input,
  useToast,
  Divider,
  Box,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { Transaction } from '../types/transaction';
import api from '../services/api';

interface TransactionDetailModalProps {
  transaction: Transaction | null;
  isOpen: boolean;
  onClose: () => void;
}

export const TransactionDetailModal = ({
  transaction,
  isOpen,
  onClose,
}: TransactionDetailModalProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [merchantName, setMerchantName] = useState('');
  const [category, setCategory] = useState('');
  const toast = useToast();
  const queryClient = useQueryClient();

  const updateMutation = useMutation({
    mutationFn: async (data: { merchant_name?: string; category_primary?: string }) => {
      const response = await api.patch(`/transactions/${transaction?.id}`, data);
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Transaction updated',
        status: 'success',
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setIsEditing(false);
    },
    onError: () => {
      toast({
        title: 'Failed to update transaction',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleEdit = () => {
    setMerchantName(transaction?.merchant_name || '');
    setCategory(transaction?.category_primary || '');
    setIsEditing(true);
  };

  const handleSave = () => {
    updateMutation.mutate({
      merchant_name: merchantName,
      category_primary: category,
    });
  };

  const handleCancel = () => {
    setIsEditing(false);
    setMerchantName('');
    setCategory('');
  };

  if (!transaction) return null;

  const formatCurrency = (amount: number) => {
    const isNegative = amount < 0;
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(amount));
    return { formatted, isNegative };
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const { formatted, isNegative } = formatCurrency(transaction.amount);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Transaction Details</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <VStack spacing={4} align="stretch">
            {/* Amount and Status */}
            <HStack justify="space-between">
              <Text
                fontSize="2xl"
                fontWeight="bold"
                color={isNegative ? 'red.600' : 'green.600'}
              >
                {isNegative ? '-' : '+'}
                {formatted}
              </Text>
              {transaction.is_pending && (
                <Badge colorScheme="orange" fontSize="md">
                  Pending
                </Badge>
              )}
            </HStack>

            {/* Date */}
            <Box>
              <Text fontSize="sm" color="gray.600">
                Date
              </Text>
              <Text fontWeight="medium">{formatDate(transaction.date)}</Text>
            </Box>

            <Divider />

            {/* Merchant Name */}
            {isEditing ? (
              <FormControl>
                <FormLabel>Merchant Name</FormLabel>
                <Input
                  value={merchantName}
                  onChange={(e) => setMerchantName(e.target.value)}
                  placeholder="Enter merchant name"
                />
              </FormControl>
            ) : (
              <Box>
                <Text fontSize="sm" color="gray.600">
                  Merchant
                </Text>
                <Text fontWeight="medium" fontSize="lg">
                  {transaction.merchant_name || 'Unknown'}
                </Text>
              </Box>
            )}

            {/* Category */}
            {isEditing ? (
              <FormControl>
                <FormLabel>Category</FormLabel>
                <Input
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="Enter category"
                />
              </FormControl>
            ) : (
              <Box>
                <Text fontSize="sm" color="gray.600">
                  Category
                </Text>
                {transaction.category_primary ? (
                  <Badge colorScheme="blue">{transaction.category_primary}</Badge>
                ) : (
                  <Text color="gray.500">No category</Text>
                )}
              </Box>
            )}

            {/* Account */}
            <Box>
              <Text fontSize="sm" color="gray.600">
                Account
              </Text>
              <Text fontWeight="medium">
                {transaction.account_name}
                {transaction.account_mask && ` ****${transaction.account_mask}`}
              </Text>
            </Box>

            {/* Description */}
            {transaction.description && (
              <Box>
                <Text fontSize="sm" color="gray.600">
                  Description
                </Text>
                <Text>{transaction.description}</Text>
              </Box>
            )}

            <Divider />

            {/* Action Buttons */}
            <VStack spacing={2}>
              {isEditing ? (
                <HStack w="full" spacing={2}>
                  <Button
                    colorScheme="brand"
                    flex={1}
                    onClick={handleSave}
                    isLoading={updateMutation.isPending}
                  >
                    Save Changes
                  </Button>
                  <Button
                    variant="outline"
                    flex={1}
                    onClick={handleCancel}
                    isDisabled={updateMutation.isPending}
                  >
                    Cancel
                  </Button>
                </HStack>
              ) : (
                <>
                  <Button w="full" onClick={handleEdit}>
                    Edit Transaction
                  </Button>
                  <Button
                    w="full"
                    variant="outline"
                    onClick={() => {
                      toast({
                        title: 'Coming soon',
                        description: 'Label management will be added next!',
                        status: 'info',
                        duration: 3000,
                      });
                    }}
                  >
                    Add Label
                  </Button>
                  <Button
                    w="full"
                    variant="outline"
                    colorScheme="blue"
                    onClick={() => {
                      toast({
                        title: 'Coming soon',
                        description: `Create a rule for all "${transaction.merchant_name}" transactions`,
                        status: 'info',
                        duration: 3000,
                      });
                    }}
                  >
                    Create Rule for "{transaction.merchant_name}"
                  </Button>
                </>
              )}
            </VStack>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};
