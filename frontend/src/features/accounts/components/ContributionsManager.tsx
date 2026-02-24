/**
 * Contributions manager component - displays and manages recurring contributions for an account
 */

import { useState } from 'react';
import {
  VStack,
  HStack,
  Box,
  Text,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  IconButton,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useToast,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contributionsApi } from '../../../api/contributions';
import { ContributionForm } from './ContributionForm';
import type { Contribution, ContributionCreate, ContributionUpdate } from '../../../types/contribution';
import { useRef } from 'react';

interface ContributionsManagerProps {
  accountId: string;
  accountName: string;
}

export const ContributionsManager = ({ accountId, accountName }: ContributionsManagerProps) => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { isOpen: isFormOpen, onOpen: onFormOpen, onClose: onFormClose } = useDisclosure();
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);

  const [selectedContribution, setSelectedContribution] = useState<Contribution | null>(null);
  const [contributionToDelete, setContributionToDelete] = useState<Contribution | null>(null);

  // Fetch contributions
  const { data: contributions, isLoading } = useQuery({
    queryKey: ['contributions', accountId],
    queryFn: () => contributionsApi.listContributions(accountId, false),
  });

  // Create contribution mutation
  const createMutation = useMutation({
    mutationFn: (data: ContributionCreate) => contributionsApi.createContribution(accountId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contributions', accountId] });
      toast({
        title: 'Contribution added',
        description: 'Recurring contribution has been added successfully.',
        status: 'success',
        duration: 3000,
      });
      onFormClose();
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to add contribution. Please try again.',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Update contribution mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ContributionUpdate }) =>
      contributionsApi.updateContribution(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contributions', accountId] });
      toast({
        title: 'Contribution updated',
        description: 'Recurring contribution has been updated successfully.',
        status: 'success',
        duration: 3000,
      });
      onFormClose();
      setSelectedContribution(null);
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update contribution. Please try again.',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Delete contribution mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => contributionsApi.deleteContribution(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contributions', accountId] });
      toast({
        title: 'Contribution deleted',
        description: 'Recurring contribution has been deleted successfully.',
        status: 'success',
        duration: 3000,
      });
      onDeleteClose();
      setContributionToDelete(null);
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to delete contribution. Please try again.',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleAddNew = () => {
    setSelectedContribution(null);
    onFormOpen();
  };

  const handleEdit = (contribution: Contribution) => {
    setSelectedContribution(contribution);
    onFormOpen();
  };

  const handleDelete = (contribution: Contribution) => {
    setContributionToDelete(contribution);
    onDeleteOpen();
  };

  const handleFormSubmit = (data: ContributionCreate | ContributionUpdate) => {
    if (selectedContribution) {
      updateMutation.mutate({ id: selectedContribution.id, data: data as ContributionUpdate });
    } else {
      createMutation.mutate(data as ContributionCreate);
    }
  };

  const handleConfirmDelete = () => {
    if (contributionToDelete) {
      deleteMutation.mutate(contributionToDelete.id);
    }
  };

  const formatContributionType = (type: string) => {
    switch (type) {
      case 'fixed_amount':
        return 'Fixed Amount';
      case 'shares':
        return 'Shares';
      case 'percentage_growth':
        return 'Growth %';
      default:
        return type;
    }
  };

  const formatFrequency = (freq: string) => {
    return freq.charAt(0).toUpperCase() + freq.slice(1).replace('_', '-');
  };

  const formatAmount = (amount: number, type: string) => {
    if (type === 'fixed_amount') {
      return `$${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } else if (type === 'percentage_growth') {
      return `${amount.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 3 })}%`;
    } else {
      return amount.toLocaleString();
    }
  };

  return (
    <Box>
      <HStack justify="space-between" mb={4}>
        <Text fontSize="lg" fontWeight="bold">
          Recurring Contributions
        </Text>
        <Button
          leftIcon={<AddIcon />}
          colorScheme="brand"
          size="sm"
          onClick={handleAddNew}
        >
          Add Contribution
        </Button>
      </HStack>

      {isLoading ? (
        <Text color="text.secondary">Loading contributions...</Text>
      ) : contributions && contributions.length > 0 ? (
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>Type</Th>
                <Th>Amount</Th>
                <Th>Frequency</Th>
                <Th>Start Date</Th>
                <Th>End Date</Th>
                <Th>Status</Th>
                <Th>Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {contributions.map((contribution) => (
                <Tr key={contribution.id}>
                  <Td>
                    <Badge colorScheme="blue" size="sm">
                      {formatContributionType(contribution.contribution_type)}
                    </Badge>
                  </Td>
                  <Td fontWeight="medium">
                    {formatAmount(contribution.amount, contribution.contribution_type)}
                  </Td>
                  <Td>{formatFrequency(contribution.frequency)}</Td>
                  <Td>{new Date(contribution.start_date).toLocaleDateString()}</Td>
                  <Td>
                    {contribution.end_date
                      ? new Date(contribution.end_date).toLocaleDateString()
                      : '—'}
                  </Td>
                  <Td>
                    <Badge colorScheme={contribution.is_active ? 'green' : 'gray'} size="sm">
                      {contribution.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </Td>
                  <Td>
                    <HStack spacing={1}>
                      <IconButton
                        icon={<EditIcon />}
                        size="sm"
                        variant="ghost"
                        aria-label="Edit contribution"
                        onClick={() => handleEdit(contribution)}
                      />
                      <IconButton
                        icon={<DeleteIcon />}
                        size="sm"
                        variant="ghost"
                        colorScheme="red"
                        aria-label="Delete contribution"
                        onClick={() => handleDelete(contribution)}
                      />
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      ) : (
        <Box p={8} textAlign="center" bg="bg.subtle" borderRadius="md" borderWidth={1}>
          <Text color="text.secondary" mb={4}>
            No recurring contributions set up for this account yet.
          </Text>
          <Text fontSize="sm" color="text.muted" mb={4}>
            Add recurring contributions to track regular deposits, share purchases, or growth rates.
          </Text>
          <Button
            leftIcon={<AddIcon />}
            colorScheme="brand"
            size="sm"
            onClick={handleAddNew}
          >
            Add Your First Contribution
          </Button>
        </Box>
      )}

      {/* Add/Edit Contribution Modal */}
      <Modal isOpen={isFormOpen} onClose={onFormClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {selectedContribution ? 'Edit' : 'Add'} Recurring Contribution
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <ContributionForm
              onSubmit={handleFormSubmit}
              onCancel={onFormClose}
              defaultValues={
                selectedContribution
                  ? {
                      contribution_type: selectedContribution.contribution_type,
                      amount: selectedContribution.amount,
                      frequency: selectedContribution.frequency,
                      start_date: selectedContribution.start_date,
                      end_date: selectedContribution.end_date || undefined,
                      notes: selectedContribution.notes || undefined,
                    }
                  : undefined
              }
              isLoading={createMutation.isPending || updateMutation.isPending}
              isEdit={!!selectedContribution}
            />
          </ModalBody>
        </ModalContent>
      </Modal>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        isOpen={isDeleteOpen}
        leastDestructiveRef={cancelRef}
        onClose={onDeleteClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Contribution
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to delete this recurring contribution? This action cannot be
              undone.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteClose}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={handleConfirmDelete}
                ml={3}
                isLoading={deleteMutation.isPending}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Box>
  );
};
