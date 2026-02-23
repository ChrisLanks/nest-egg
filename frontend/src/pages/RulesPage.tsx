/**
 * Rules management page
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Center,
  Button,
  IconButton,
  Switch,
  useToast,
  Card,
  CardBody,
  Divider,
  Collapse,
  useDisclosure,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DeleteIcon, ChevronDownIcon, ChevronUpIcon, AddIcon, EditIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import { RuleBuilderModal } from '../components/RuleBuilderModal';
import type { Rule } from '../types/rule';
import api from '../services/api';
import { useUserView } from '../contexts/UserViewContext';

const FIELD_LABELS: Record<string, string> = {
  merchant_name: 'Merchant',
  amount: 'Amount',
  amount_exact: 'Amount (Exact)',
  category: 'Category',
  description: 'Description',
};

const OPERATOR_LABELS: Record<string, string> = {
  equals: '=',
  contains: 'contains',
  starts_with: 'starts with',
  ends_with: 'ends with',
  greater_than: '>',
  less_than: '<',
  between: 'between',
  regex: 'matches regex',
};

const ACTION_LABELS: Record<string, string> = {
  set_category: 'Set category',
  add_label: 'Add label',
  remove_label: 'Remove label',
  set_merchant: 'Set merchant',
};

export const RulesPage = () => {
  const [isRuleBuilderOpen, setIsRuleBuilderOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [expandedRule, setExpandedRule] = useState<string | null>(null);
  const toast = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { canWriteResource } = useUserView();
  const canEdit = canWriteResource('rule');

  const { data: rules, isLoading } = useQuery({
    queryKey: ['rules'],
    queryFn: async () => {
      const response = await api.get<Rule[]>('/rules');
      return response.data;
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: async ({ ruleId, isActive }: { ruleId: string; isActive: boolean }) => {
      const response = await api.patch(`/rules/${ruleId}`, { is_active: isActive });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      toast({
        title: 'Rule updated',
        status: 'success',
        duration: 2000,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to update rule',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: async (ruleId: string) => {
      await api.delete(`/rules/${ruleId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      toast({
        title: 'Rule deleted',
        status: 'success',
        duration: 2000,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to delete rule',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleToggleActive = (ruleId: string, isActive: boolean) => {
    toggleActiveMutation.mutate({ ruleId, isActive: !isActive });
  };

  const handleDelete = (ruleId: string, ruleName: string) => {
    if (window.confirm(`Are you sure you want to delete the rule "${ruleName}"?`)) {
      deleteRuleMutation.mutate(ruleId);
    }
  };

  const toggleExpanded = (ruleId: string) => {
    setExpandedRule(expandedRule === ruleId ? null : ruleId);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between" align="start">
          <Box>
            <Heading size="lg">Rules</Heading>
            <Text color="gray.600" mt={2}>
              Manage automation rules for transaction categorization. {rules?.length || 0} rule(s) total.
            </Text>
          </Box>
          <HStack>
            <Button
              variant="ghost"
              onClick={() => navigate('/transactions')}
            >
              Back to Transactions
            </Button>
            <Button
              colorScheme="brand"
              leftIcon={<AddIcon />}
              onClick={() => setIsRuleBuilderOpen(true)}
              isDisabled={!canEdit}
            >
              Create Rule
            </Button>
          </HStack>
        </HStack>

        {rules && rules.length === 0 ? (
          <Box
            bg="white"
            p={12}
            borderRadius="lg"
            boxShadow="sm"
            textAlign="center"
          >
            <Text fontSize="lg" color="gray.600" mb={4}>
              No rules created yet
            </Text>
            <Text color="gray.500" mb={6}>
              Create rules to automatically categorize and label transactions
            </Text>
            <Button
              colorScheme="brand"
              leftIcon={<AddIcon />}
              onClick={() => setIsRuleBuilderOpen(true)}
              isDisabled={!canEdit}
            >
              Create Your First Rule
            </Button>
          </Box>
        ) : (
          <VStack spacing={3} align="stretch">
            {rules?.map((rule) => {
              const isExpanded = expandedRule === rule.id;
              return (
                <Card key={rule.id}>
                  <CardBody py={3} px={4}>
                    <VStack spacing={3} align="stretch">
                      {/* Rule Header */}
                      <HStack justify="space-between">
                        <HStack spacing={3} flex={1}>
                          <IconButton
                            icon={isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
                            aria-label="Expand rule"
                            size="sm"
                            variant="ghost"
                            onClick={() => toggleExpanded(rule.id)}
                          />
                          <Box flex={1}>
                            <HStack spacing={2} mb={1}>
                              <Text fontWeight="bold" fontSize="lg">
                                {rule.name}
                              </Text>
                              <Badge colorScheme={rule.is_active ? 'green' : 'gray'}>
                                {rule.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                              <Badge colorScheme="purple">
                                {rule.match_type === 'all' ? 'ALL conditions' : 'ANY condition'}
                              </Badge>
                              <Badge colorScheme="blue">
                                {rule.apply_to === 'new_only' && 'New only'}
                                {rule.apply_to === 'existing_only' && 'Existing only'}
                                {rule.apply_to === 'both' && 'New & existing'}
                                {rule.apply_to === 'single' && 'Single use'}
                              </Badge>
                            </HStack>
                            {rule.description && (
                              <Text fontSize="sm" color="gray.600">
                                {rule.description}
                              </Text>
                            )}
                            <Text fontSize="xs" color="gray.500" mt={1}>
                              Applied {rule.times_applied} times
                              {rule.last_applied_at && ` • Last: ${formatDate(rule.last_applied_at)}`}
                            </Text>
                          </Box>
                        </HStack>

                        <HStack spacing={2}>
                          <HStack spacing={2}>
                            <Text fontSize="sm" color="gray.600">
                              {rule.is_active ? 'Enabled' : 'Disabled'}
                            </Text>
                            <Switch
                              colorScheme="green"
                              isChecked={rule.is_active}
                              onChange={() => handleToggleActive(rule.id, rule.is_active)}
                              isDisabled={!canEdit || toggleActiveMutation.isPending}
                            />
                          </HStack>
                          <IconButton
                            icon={<EditIcon />}
                            aria-label="Edit rule"
                            variant="ghost"
                            size="sm"
                            isDisabled={!canEdit}
                            onClick={() => {
                              setEditingRule(rule);
                              setIsRuleBuilderOpen(true);
                            }}
                          />
                          <IconButton
                            icon={<DeleteIcon />}
                            aria-label="Delete rule"
                            colorScheme="red"
                            variant="ghost"
                            size="sm"
                            isDisabled={!canEdit}
                            onClick={() => handleDelete(rule.id, rule.name)}
                            isLoading={deleteRuleMutation.isPending}
                          />
                        </HStack>
                      </HStack>

                      {/* Expanded Details */}
                      <Collapse in={isExpanded} animateOpacity>
                        <Box pl={10} pt={2}>
                          <Divider mb={4} />

                          {/* Conditions */}
                          <Box mb={4}>
                            <Text fontWeight="semibold" fontSize="sm" color="gray.700" mb={2}>
                              Conditions ({rule.conditions?.length || 0}):
                            </Text>
                            <VStack align="stretch" spacing={1}>
                              {rule.conditions?.map((condition, idx) => (
                                <HStack key={condition.id} spacing={2} fontSize="sm">
                                  <Badge colorScheme="blue" variant="subtle">
                                    {idx + 1}
                                  </Badge>
                                  <Text>
                                    {FIELD_LABELS[condition.field] || condition.field}
                                  </Text>
                                  <Text fontWeight="semibold">
                                    {OPERATOR_LABELS[condition.operator] || condition.operator}
                                  </Text>
                                  <Text fontWeight="medium" color="blue.600">
                                    "{condition.value}"
                                  </Text>
                                  {condition.value_max && (
                                    <>
                                      <Text>and</Text>
                                      <Text fontWeight="medium" color="blue.600">
                                        "{condition.value_max}"
                                      </Text>
                                    </>
                                  )}
                                </HStack>
                              ))}
                            </VStack>
                          </Box>

                          {/* Actions */}
                          <Box>
                            <Text fontWeight="semibold" fontSize="sm" color="gray.700" mb={2}>
                              Actions ({rule.actions?.length || 0}):
                            </Text>
                            <VStack align="stretch" spacing={1}>
                              {rule.actions?.map((action, idx) => (
                                <HStack key={action.id} spacing={2} fontSize="sm">
                                  <Badge colorScheme="green" variant="subtle">
                                    {idx + 1}
                                  </Badge>
                                  <Text>
                                    {ACTION_LABELS[action.action_type] || action.action_type}
                                  </Text>
                                  <Text>to</Text>
                                  <Text fontWeight="medium" color="green.600">
                                    "{action.action_value}"
                                  </Text>
                                </HStack>
                              ))}
                            </VStack>
                          </Box>

                          <Text fontSize="xs" color="gray.500" mt={4}>
                            Created {formatDate(rule.created_at)}
                          </Text>
                        </Box>
                      </Collapse>
                    </VStack>
                  </CardBody>
                </Card>
              );
            })}
          </VStack>
        )}

        <RuleBuilderModal
          isOpen={isRuleBuilderOpen}
          onClose={() => {
            setIsRuleBuilderOpen(false);
            setEditingRule(null);
          }}
          rule={editingRule ?? undefined}
        />
      </VStack>
    </Container>
  );
};
