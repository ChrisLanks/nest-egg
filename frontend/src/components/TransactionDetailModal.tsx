/**
 * Transaction detail modal with editing and rule creation
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
  Input,
  useToast,
  Divider,
  Box,
  ButtonGroup,
  Wrap,
  WrapItem,
  IconButton,
  useDisclosure,
  Tooltip,
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import { useState, useEffect } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import type { Transaction } from '../types/transaction';
import api from '../services/api';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useUserView } from '../contexts/UserViewContext';
import { CategorySelect } from './CategorySelect';
import { MerchantSelect } from './MerchantSelect';
import { RuleBuilder } from '../features/rules/components/RuleBuilder';

interface TransactionDetailModalProps {
  transaction: Transaction | null;
  isOpen: boolean;
  onClose: () => void;
  onCreateRule?: (transaction: Transaction) => void;
}

interface Label {
  id: string;
  name: string;
  color?: string;
  is_income: boolean;
}

export const TransactionDetailModal = ({
  transaction,
  isOpen,
  onClose,
  onCreateRule: _onCreateRule,
}: TransactionDetailModalProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [merchantName, setMerchantName] = useState('');
  const [category, setCategory] = useState('');
  const [newLabelName, setNewLabelName] = useState('');
  const [pendingLabelsToAdd, setPendingLabelsToAdd] = useState<string[]>([]);
  const [pendingLabelsToRemove, setPendingLabelsToRemove] = useState<string[]>([]);
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const { isSelfView, isOtherUserView } = useUserView();

  // Rule builder modal
  const { isOpen: isRuleBuilderOpen, onOpen: onRuleBuilderOpen, onClose: onRuleBuilderClose } = useDisclosure();

  // Fetch account to check ownership — only needed for combined household view
  // (in self-view all shown transactions are ours; in other-user-view never editable)
  const { data: account } = useQuery({
    queryKey: ['account', transaction?.account_id],
    queryFn: async () => {
      if (!transaction?.account_id) return null;
      const response = await api.get(`/accounts/${transaction.account_id}`);
      return response.data;
    },
    enabled: !!transaction?.account_id && isOpen && !isSelfView && !isOtherUserView,
  });

  // Determine edit permission:
  // - Self view: all displayed transactions belong to the current user → always editable
  // - Other-user view: read-only → never editable
  // - Combined household view: check account ownership
  const canEdit = isSelfView
    ? true
    : isOtherUserView
      ? false
      : !!(account && account.user_id === user?.id);

  // Fetch available labels
  const { data: availableLabels } = useQuery({
    queryKey: ['labels'],
    queryFn: async () => {
      const response = await api.get<Label[]>('/labels/');
      return response.data;
    },
    enabled: isOpen,
  });

  // Fetch current transaction to get live updates when labels change
  const { data: liveTransaction } = useQuery({
    queryKey: ['transaction', transaction?.id],
    queryFn: async () => {
      const response = await api.get<Transaction>(`/transactions/${transaction?.id}`);
      return response.data;
    },
    enabled: isOpen && !!transaction?.id,
    initialData: transaction || undefined,
  });

  // Use live transaction data if available, otherwise fall back to prop
  const currentTransaction = liveTransaction || transaction;

  // Reset editing state when transaction changes or modal opens
  useEffect(() => {
    if (isOpen) {
      setIsEditing(false);
      setMerchantName('');
      setCategory('');
      setNewLabelName('');
      setPendingLabelsToAdd([]);
      setPendingLabelsToRemove([]);
    }
  }, [transaction?.id, isOpen]);

  const updateMutation = useMutation({
    mutationFn: async (data: { merchant_name?: string; category_primary?: string; is_transfer?: boolean }) => {
      // First update the transaction fields
      const response = await api.patch(`/transactions/${transaction?.id}`, data);

      // Then apply label changes
      for (const labelId of pendingLabelsToRemove) {
        await api.delete(`/transactions/${transaction?.id}/labels/${labelId}`);
      }
      for (const labelId of pendingLabelsToAdd) {
        await api.post(`/transactions/${transaction?.id}/labels/${labelId}`);
      }

      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Transaction updated',
        status: 'success',
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['transaction', transaction?.id] });
      setPendingLabelsToAdd([]);
      setPendingLabelsToRemove([]);
      setIsEditing(false);
      onClose();
    },
    onError: () => {
      toast({
        title: 'Failed to update transaction',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Separate mutation for transfer toggle that doesn't close the modal
  const toggleTransferMutation = useMutation({
    mutationFn: async (isTransfer: boolean) => {
      const response = await api.patch(`/transactions/${transaction?.id}`, { is_transfer: isTransfer });
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Transfer status updated',
        status: 'success',
        duration: 2000,
      });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      queryClient.invalidateQueries({ queryKey: ['transaction', transaction?.id] });
    },
    onError: () => {
      toast({
        title: 'Failed to update transfer status',
        status: 'error',
        duration: 3000,
      });
    },
  });


  const createLabelMutation = useMutation({
    mutationFn: async (name: string) => {
      const response = await api.post<Label>('/labels/', { name });
      return response.data;
    },
    onSuccess: (newLabel) => {
      queryClient.invalidateQueries({ queryKey: ['labels'] });
      // Add to pending additions
      setPendingLabelsToAdd([...pendingLabelsToAdd, newLabel.id]);
      setNewLabelName('');
      toast({
        title: 'Label created and will be added on save',
        status: 'success',
        duration: 3000,
      });
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.detail || 'Failed to create label';
      toast({
        title: errorMessage,
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleEdit = () => {
    setMerchantName(currentTransaction?.merchant_name || '');
    setCategory(currentTransaction?.category_primary || '');
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
    setPendingLabelsToAdd([]);
    setPendingLabelsToRemove([]);
  };

  const handleCreateRule = () => {
    onRuleBuilderOpen();
  };

  const handleAddLabel = (labelId: string) => {
    // If this label was pending removal, cancel that
    if (pendingLabelsToRemove.includes(labelId)) {
      setPendingLabelsToRemove(pendingLabelsToRemove.filter(id => id !== labelId));
    } else {
      // Otherwise, add it to pending additions
      setPendingLabelsToAdd([...pendingLabelsToAdd, labelId]);
    }
  };

  const handleRemoveLabel = (labelId: string) => {
    // If this label was pending addition, just cancel that
    if (pendingLabelsToAdd.includes(labelId)) {
      setPendingLabelsToAdd(pendingLabelsToAdd.filter(id => id !== labelId));
    } else {
      // Otherwise, add it to pending removals
      setPendingLabelsToRemove([...pendingLabelsToRemove, labelId]);
    }
  };

  const handleCreateAndAddLabel = () => {
    if (!newLabelName.trim()) return;

    // Prevent creating "Transfer" label (reserved for system)
    if (newLabelName.trim().toLowerCase() === 'transfer') {
      toast({
        title: 'Cannot create label named "Transfer"',
        description: 'This is a reserved system label. Use the "Mark as Transfer" button instead.',
        status: 'warning',
        duration: 5000,
      });
      return;
    }

    createLabelMutation.mutate(newLabelName.trim());
  };

  const handleToggleTransfer = () => {
    toggleTransferMutation.mutate(!currentTransaction!.is_transfer);
  };

  if (!currentTransaction) return null;

  // Calculate current labels accounting for pending changes
  const currentLabels = currentTransaction.labels || [];
  const displayedLabels = [
    ...currentLabels.filter(label => !pendingLabelsToRemove.includes(label.id)),
    ...(availableLabels?.filter(label => pendingLabelsToAdd.includes(label.id)) || [])
  ];

  // Get labels not already on this transaction (including pending additions)
  const allCurrentLabelIds = [
    ...currentLabels.map(l => l.id),
    ...pendingLabelsToAdd
  ].filter(id => !pendingLabelsToRemove.includes(id));

  const unusedLabels = availableLabels?.filter(
    (label) => !allCurrentLabelIds.includes(label.id)
  ) || [];

  const formatCurrency = (amount: number) => {
    const isNegative = amount < 0;
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(amount));
    return { formatted, isNegative };
  };

  const formatDate = (dateStr: string) => {
    // Parse as local date to avoid timezone conversion issues
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const { formatted, isNegative } = formatCurrency(currentTransaction.amount);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          {isEditing ? 'Edit Transaction' : 'Transaction Details'}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <VStack spacing={4} align="stretch">
            {/* Amount and Status */}
            <HStack justify="space-between">
              <Text
                fontSize="2xl"
                fontWeight="bold"
                color={isNegative ? 'finance.negative' : 'finance.positive'}
              >
                {isNegative ? '-' : '+'}
                {formatted}
              </Text>
              <HStack spacing={2}>
                {currentTransaction.is_pending && (
                  <Badge colorScheme="orange" fontSize="md">
                    Pending
                  </Badge>
                )}
                {currentTransaction.is_transfer && (
                  <Tooltip label="Excluded from cash flow">
                    <Badge colorScheme="purple" fontSize="md">
                      Transfer
                    </Badge>
                  </Tooltip>
                )}
              </HStack>
            </HStack>

            {/* Transfer Toggle */}
            <Box>
              <HStack justify="space-between" align="center">
                <Box>
                  <Text fontSize="sm" fontWeight="medium" color="text.heading">
                    Transfer Transaction
                  </Text>
                  <Text fontSize="xs" color="text.muted">
                    Transfers are excluded from cash flow and budgets
                  </Text>
                </Box>
                <Tooltip label={!canEdit ? "You can only edit your own transactions" : ""}>
                  <Button
                    size="sm"
                    colorScheme={currentTransaction.is_transfer ? "purple" : "gray"}
                    variant={currentTransaction.is_transfer ? "solid" : "outline"}
                    onClick={handleToggleTransfer}
                    isDisabled={!canEdit}
                    isLoading={toggleTransferMutation.isPending}
                  >
                    {currentTransaction.is_transfer ? "✓ Is Transfer" : "Mark as Transfer"}
                  </Button>
                </Tooltip>
              </HStack>
            </Box>

            <Divider />

            {/* Date */}
            <Box>
              <Text fontSize="sm" color="text.secondary">
                Date
              </Text>
              <Text fontWeight="medium">{formatDate(currentTransaction.date)}</Text>
            </Box>

            <Divider />

            {/* Merchant Name */}
            {isEditing ? (
              <MerchantSelect
                value={merchantName}
                onChange={setMerchantName}
                placeholder="Type or select merchant"
              />
            ) : (
              <Box>
                <Text fontSize="sm" color="text.secondary">
                  Merchant
                </Text>
                <Text fontWeight="medium" fontSize="lg">
                  {currentTransaction.merchant_name || 'Unknown'}
                </Text>
              </Box>
            )}

            {/* Category */}
            {isEditing ? (
              <CategorySelect
                value={category}
                onChange={setCategory}
                placeholder="Type or select category"
              />
            ) : (
              <Box>
                <Text fontSize="sm" color="text.secondary">
                  Category
                </Text>
                {currentTransaction.category_primary ? (
                  <Badge colorScheme="blue">{currentTransaction.category_primary}</Badge>
                ) : (
                  <Text color="text.muted">No category</Text>
                )}
              </Box>
            )}

            {/* Labels */}
            <Box>
              <Text fontSize="sm" color="text.secondary" mb={2}>
                Labels
              </Text>
              {displayedLabels.length > 0 ? (
                <Wrap spacing={2}>
                  {displayedLabels.map((label) => (
                    <WrapItem key={label.id}>
                      <Badge
                        colorScheme={label.is_income ? 'green' : 'purple'}
                        fontSize="sm"
                        px={3}
                        py={1}
                        borderRadius="md"
                      >
                        <HStack spacing={2}>
                          <Text>{label.name}</Text>
                          {isEditing && (
                            <IconButton
                              icon={<CloseIcon />}
                              aria-label="Remove label"
                              size="xs"
                              variant="ghost"
                              colorScheme="whiteAlpha"
                              onClick={() => handleRemoveLabel(label.id)}
                            />
                          )}
                        </HStack>
                      </Badge>
                    </WrapItem>
                  ))}
                </Wrap>
              ) : (
                <Text color="text.muted" fontSize="sm">
                  No labels
                </Text>
              )}

              {/* Add label in edit mode */}
              {isEditing && (
                <VStack align="stretch" mt={3} spacing={3} p={3} bg="bg.subtle" borderRadius="md">
                  {unusedLabels && unusedLabels.length > 0 ? (
                    <Box>
                      <Text fontSize="sm" fontWeight="medium" color="text.heading" mb={2}>
                        Add existing label:
                      </Text>
                      <Wrap spacing={2}>
                        {unusedLabels.map((label) => (
                          <WrapItem key={label.id}>
                            <Button
                              size="sm"
                              variant="outline"
                              colorScheme={label.is_income ? 'green' : 'purple'}
                              onClick={() => handleAddLabel(label.id)}
                            >
                              + {label.name}
                            </Button>
                          </WrapItem>
                        ))}
                      </Wrap>
                    </Box>
                  ) : (
                    <Text fontSize="sm" color="text.secondary">
                      {availableLabels && availableLabels.length > 0
                        ? 'All labels already added'
                        : 'No labels created yet'}
                    </Text>
                  )}

                  <Divider />

                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color="text.heading" mb={2}>
                      Create new label:
                    </Text>
                    <HStack>
                      <Input
                        size="sm"
                        placeholder="Enter label name..."
                        value={newLabelName}
                        onChange={(e) => setNewLabelName(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            handleCreateAndAddLabel();
                          }
                        }}
                      />
                      <Button
                        size="sm"
                        colorScheme="purple"
                        onClick={handleCreateAndAddLabel}
                        isLoading={createLabelMutation.isPending}
                        isDisabled={!newLabelName.trim()}
                        minW="100px"
                      >
                        Create
                      </Button>
                    </HStack>
                  </Box>
                </VStack>
              )}
            </Box>

            {/* Account */}
            <Box>
              <Text fontSize="sm" color="text.secondary">
                Account
              </Text>
              <Text fontWeight="medium">
                {currentTransaction.account_name}
                {currentTransaction.account_mask && ` ****${currentTransaction.account_mask}`}
              </Text>
            </Box>

            {/* Description */}
            {currentTransaction.description && (
              <Box>
                <Text fontSize="sm" color="text.secondary">
                  Description
                </Text>
                <Text>{currentTransaction.description}</Text>
              </Box>
            )}

            <Divider />

            {/* Action Buttons */}
            {isEditing ? (
              <ButtonGroup w="full" spacing={2}>
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
              </ButtonGroup>
            ) : (
              <VStack spacing={2}>
                <Tooltip
                  label={!canEdit ? "You can only edit transactions from your own accounts" : ""}
                  placement="top"
                  isDisabled={canEdit}
                >
                  <Button
                    w="full"
                    colorScheme="brand"
                    onClick={handleEdit}
                    isDisabled={!canEdit}
                  >
                    Edit Transaction
                  </Button>
                </Tooltip>
                <Button
                  w="full"
                  colorScheme="blue"
                  variant="outline"
                  onClick={handleCreateRule}
                >
                  Create Rule for "{currentTransaction.merchant_name}"
                </Button>
                {!canEdit && (
                  <Text fontSize="xs" color="text.muted" textAlign="center">
                    Read-only: This transaction belongs to another household member
                  </Text>
                )}
              </VStack>
            )}
          </VStack>
        </ModalBody>
      </ModalContent>

      {/* Rule Builder Modal */}
      <RuleBuilder
        isOpen={isRuleBuilderOpen}
        onClose={onRuleBuilderClose}
        prefillMerchant={currentTransaction?.merchant_name || undefined}
      />
    </Modal>
  );
};
