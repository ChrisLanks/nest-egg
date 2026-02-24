/**
 * Rules page - list and manage transaction automation rules
 */

import {
  Box,
  Button,
  Container,
  Heading,
  HStack,
  VStack,
  Text,
  Badge,
  IconButton,
  Switch,
  useDisclosure,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Center,
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import api from '../../../services/api';
import type { Rule } from '../../../types/rule';
import { RuleBuilder } from '../components/RuleBuilder';

export const RulesPage = () => {
  const [selectedRule, setSelectedRule] = useState<Rule | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();
  const queryClient = useQueryClient();

  // Fetch rules
  const { data: rules, isLoading } = useQuery({
    queryKey: ['rules'],
    queryFn: async () => {
      const response = await api.get<Rule[]>('/rules/');
      return response.data;
    },
  });

  // Toggle rule active status
  const toggleMutation = useMutation({
    mutationFn: async ({ ruleId, isActive }: { ruleId: string; isActive: boolean }) => {
      await api.patch(`/rules/${ruleId}`, { is_active: isActive });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      toast({
        title: 'Rule updated',
        status: 'success',
        duration: 3000,
      });
    },
  });

  // Delete rule
  const deleteMutation = useMutation({
    mutationFn: async (ruleId: string) => {
      await api.delete(`/rules/${ruleId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      toast({
        title: 'Rule deleted',
        status: 'success',
        duration: 3000,
      });
    },
  });

  // Apply rule
  const applyMutation = useMutation({
    mutationFn: async (ruleId: string) => {
      const response = await api.post<{ applied_count: number }>(`/rules/${ruleId}/apply`, {
        transaction_ids: null, // Apply to all transactions
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      toast({
        title: `Rule applied to ${data.applied_count} transaction(s)`,
        status: 'success',
        duration: 3000,
      });
    },
  });

  const handleCreate = () => {
    setSelectedRule(null);
    onOpen();
  };

  const handleEdit = (rule: Rule) => {
    setSelectedRule(rule);
    onOpen();
  };

  const handleClose = () => {
    setSelectedRule(null);
    onClose();
  };

  const handleToggle = (rule: Rule) => {
    toggleMutation.mutate({ ruleId: rule.id, isActive: !rule.is_active });
  };

  const handleDelete = (ruleId: string) => {
    if (confirm('Are you sure you want to delete this rule?')) {
      deleteMutation.mutate(ruleId);
    }
  };

  const handleApply = (ruleId: string) => {
    if (confirm('Apply this rule to all existing transactions?')) {
      applyMutation.mutate(ruleId);
    }
  };

  if (isLoading) {
    return (
      <Center h="200px">
        <Spinner size="xl" />
      </Center>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between">
          <Box>
            <Heading size="lg">Transaction Rules</Heading>
            <Text color="text.secondary" mt={1}>
              Automatically categorize and label transactions based on conditions
            </Text>
          </Box>
          <Button leftIcon={<AddIcon />} colorScheme="brand" onClick={handleCreate}>
            Create Rule
          </Button>
        </HStack>

        {rules && rules.length > 0 ? (
          <Box overflowX="auto" bg="bg.surface" borderRadius="lg" shadow="sm">
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>Active</Th>
                  <Th>Name</Th>
                  <Th>Conditions</Th>
                  <Th>Actions</Th>
                  <Th>Applied</Th>
                  <Th>Priority</Th>
                  <Th></Th>
                </Tr>
              </Thead>
              <Tbody>
                {rules.map((rule) => (
                  <Tr key={rule.id}>
                    <Td>
                      <Switch
                        isChecked={rule.is_active}
                        onChange={() => handleToggle(rule)}
                        colorScheme="brand"
                      />
                    </Td>
                    <Td>
                      <VStack align="start" spacing={1}>
                        <Text fontWeight="medium">{rule.name}</Text>
                        {rule.description && (
                          <Text fontSize="sm" color="text.secondary">
                            {rule.description}
                          </Text>
                        )}
                      </VStack>
                    </Td>
                    <Td>
                      <Badge colorScheme="blue">
                        {rule.conditions.length} condition(s)
                      </Badge>
                    </Td>
                    <Td>
                      <Badge colorScheme="green">
                        {rule.actions.length} action(s)
                      </Badge>
                    </Td>
                    <Td>
                      <Text fontSize="sm">{rule.times_applied}x</Text>
                    </Td>
                    <Td>
                      <Badge>{rule.priority}</Badge>
                    </Td>
                    <Td>
                      <HStack spacing={1} justify="flex-end">
                        <IconButton
                          icon={<EditIcon />}
                          aria-label="Edit rule"
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEdit(rule)}
                        />
                        <Button
                          size="sm"
                          colorScheme="blue"
                          variant="ghost"
                          onClick={() => handleApply(rule.id)}
                          isLoading={applyMutation.isPending}
                        >
                          Apply
                        </Button>
                        <IconButton
                          icon={<DeleteIcon />}
                          aria-label="Delete rule"
                          size="sm"
                          variant="ghost"
                          colorScheme="red"
                          onClick={() => handleDelete(rule.id)}
                          isLoading={deleteMutation.isPending}
                        />
                      </HStack>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        ) : (
          <Box textAlign="center" py={12} bg="bg.subtle" borderRadius="lg">
            <Text color="text.secondary" mb={4}>
              No rules created yet. Create your first rule to automate transaction categorization.
            </Text>
            <Button leftIcon={<AddIcon />} colorScheme="brand" onClick={handleCreate}>
              Create Your First Rule
            </Button>
          </Box>
        )}
      </VStack>

      <RuleBuilder isOpen={isOpen} onClose={handleClose} rule={selectedRule} />
    </Container>
  );
};
