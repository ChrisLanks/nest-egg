/**
 * Rule builder component for creating and editing rules
 */

import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  ModalFooter,
  Button,
  VStack,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Select,
  HStack,
  IconButton,
  Box,
  Text,
  Divider,
  NumberInput,
  NumberInputField,
  useToast,
  Badge,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { useState, useEffect } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import api from '../../../services/api';
import type {
  Rule,
  RuleCreate,
  RuleCondition,
  RuleAction,
  RuleMatchType,
  RuleApplyTo,
  ConditionField,
  ConditionOperator,
  ActionType,
} from '../../../types/rule';
import type { Label } from '../../../types/transaction';

interface RuleBuilderProps {
  isOpen: boolean;
  onClose: () => void;
  rule?: Rule | null;
  prefillMerchant?: string;
}

export const RuleBuilder = ({ isOpen, onClose, rule, prefillMerchant }: RuleBuilderProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [matchType, setMatchType] = useState<RuleMatchType>('all');
  const [applyTo, setApplyTo] = useState<RuleApplyTo>('new_only');
  const [priority, setPriority] = useState(0);
  const [isActive, setIsActive] = useState(true);
  const [conditions, setConditions] = useState<Omit<RuleCondition, 'id' | 'rule_id' | 'created_at'>[]>([]);
  const [actions, setActions] = useState<Omit<RuleAction, 'id' | 'rule_id' | 'created_at'>[]>([]);

  const toast = useToast();
  const queryClient = useQueryClient();

  // Fetch labels for action options
  const { data: labels } = useQuery({
    queryKey: ['labels'],
    queryFn: async () => {
      const response = await api.get<Label[]>('/labels/');
      return response.data;
    },
    enabled: isOpen,
  });

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      if (rule) {
        // Edit mode
        setName(rule.name);
        setDescription(rule.description || '');
        setMatchType(rule.match_type);
        setApplyTo(rule.apply_to);
        setPriority(rule.priority);
        setIsActive(rule.is_active);
        setConditions(
          rule.conditions.map((c) => ({
            field: c.field,
            operator: c.operator,
            value: c.value,
            value_max: c.value_max,
          }))
        );
        setActions(
          rule.actions.map((a) => ({
            action_type: a.action_type,
            action_value: a.action_value,
          }))
        );
      } else {
        // Create mode
        setName('');
        setDescription('');
        setMatchType('all');
        setApplyTo('new_only');
        setPriority(0);
        setIsActive(true);
        
        // If prefillMerchant is provided, add a condition
        if (prefillMerchant) {
          setConditions([
            {
              field: 'merchant_name',
              operator: 'equals',
              value: prefillMerchant,
            },
          ]);
        } else {
          setConditions([]);
        }
        setActions([]);
      }
    }
  }, [isOpen, rule, prefillMerchant]);

  const createMutation = useMutation({
    mutationFn: async (data: RuleCreate) => {
      const response = await api.post<Rule>('/rules/', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      toast({
        title: 'Rule created',
        status: 'success',
        duration: 3000,
      });
      onClose();
    },
    onError: () => {
      toast({
        title: 'Failed to create rule',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: RuleCreate) => {
      // Note: Backend doesn't support updating conditions/actions yet, so we'll just update basic fields
      await api.patch(`/rules/${rule?.id}`, {
        name: data.name,
        description: data.description,
        is_active: data.is_active,
        priority: data.priority,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      toast({
        title: 'Rule updated',
        status: 'success',
        duration: 3000,
      });
      onClose();
    },
    onError: () => {
      toast({
        title: 'Failed to update rule',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleSave = () => {
    if (!name.trim()) {
      toast({
        title: 'Name is required',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    if (conditions.length === 0) {
      toast({
        title: 'At least one condition is required',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    if (actions.length === 0) {
      toast({
        title: 'At least one action is required',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    const ruleData: RuleCreate = {
      name,
      description: description || undefined,
      match_type: matchType,
      apply_to: applyTo,
      priority,
      is_active: isActive,
      conditions,
      actions,
    };

    if (rule) {
      updateMutation.mutate(ruleData);
    } else {
      createMutation.mutate(ruleData);
    }
  };

  const addCondition = () => {
    setConditions([
      ...conditions,
      {
        field: 'merchant_name',
        operator: 'contains',
        value: '',
      },
    ]);
  };

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };

  const updateCondition = (index: number, updates: Partial<RuleCondition>) => {
    const newConditions = [...conditions];
    newConditions[index] = { ...newConditions[index], ...updates };
    setConditions(newConditions);
  };

  const addAction = () => {
    setActions([
      ...actions,
      {
        action_type: 'add_label',
        action_value: '',
      },
    ]);
  };

  const removeAction = (index: number) => {
    setActions(actions.filter((_, i) => i !== index));
  };

  const updateAction = (index: number, updates: Partial<RuleAction>) => {
    const newActions = [...actions];
    newActions[index] = { ...newActions[index], ...updates };
    setActions(newActions);
  };

  const getOperatorsForField = (field: ConditionField): ConditionOperator[] => {
    if (field === 'amount' || field === 'amount_exact') {
      return ['equals', 'greater_than', 'less_than', 'between'];
    }
    return ['equals', 'contains', 'starts_with', 'ends_with', 'regex'];
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{rule ? 'Edit Rule' : 'Create Rule'}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            {/* Basic Info */}
            <FormControl isRequired>
              <FormLabel>Rule Name</FormLabel>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Categorize Starbucks purchases"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Description</FormLabel>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                rows={2}
              />
            </FormControl>

            <HStack spacing={4}>
              <FormControl>
                <FormLabel>Priority</FormLabel>
                <NumberInput
                  value={priority}
                  onChange={(_, num) => setPriority(num)}
                  min={0}
                  max={100}
                >
                  <NumberInputField />
                </NumberInput>
              </FormControl>

              <FormControl>
                <FormLabel>Apply To</FormLabel>
                <Select
                  value={applyTo}
                  onChange={(e) => setApplyTo(e.target.value as RuleApplyTo)}
                >
                  <option value="new_only">New Transactions Only</option>
                  <option value="existing_only">Existing Transactions Only</option>
                  <option value="both">All Transactions</option>
                </Select>
              </FormControl>
            </HStack>

            <Divider />

            {/* Conditions */}
            <Box>
              <HStack justify="space-between" mb={3}>
                <Text fontWeight="medium">Conditions</Text>
                <HStack>
                  <Select
                    size="sm"
                    value={matchType}
                    onChange={(e) => setMatchType(e.target.value as RuleMatchType)}
                    w="150px"
                  >
                    <option value="all">Match ALL</option>
                    <option value="any">Match ANY</option>
                  </Select>
                  <Button leftIcon={<AddIcon />} size="sm" onClick={addCondition}>
                    Add Condition
                  </Button>
                </HStack>
              </HStack>

              <VStack spacing={3} align="stretch">
                {conditions.map((condition, index) => (
                  <Box key={index} p={3} bg="gray.50" borderRadius="md">
                    <HStack spacing={2} mb={2}>
                      <Select
                        value={condition.field}
                        onChange={(e) =>
                          updateCondition(index, { field: e.target.value as ConditionField })
                        }
                        size="sm"
                      >
                        <option value="merchant_name">Merchant Name</option>
                        <option value="amount">Amount (absolute)</option>
                        <option value="amount_exact">Amount (exact)</option>
                        <option value="category">Category</option>
                        <option value="description">Description</option>
                      </Select>

                      <Select
                        value={condition.operator}
                        onChange={(e) =>
                          updateCondition(index, { operator: e.target.value as ConditionOperator })
                        }
                        size="sm"
                      >
                        {getOperatorsForField(condition.field).map((op) => (
                          <option key={op} value={op}>
                            {op.replace('_', ' ')}
                          </option>
                        ))}
                      </Select>

                      <IconButton
                        icon={<DeleteIcon />}
                        aria-label="Remove condition"
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => removeCondition(index)}
                      />
                    </HStack>

                    <HStack>
                      <Input
                        value={condition.value}
                        onChange={(e) => updateCondition(index, { value: e.target.value })}
                        placeholder="Value"
                        size="sm"
                      />
                      {condition.operator === 'between' && (
                        <>
                          <Text fontSize="sm">and</Text>
                          <Input
                            value={condition.value_max || ''}
                            onChange={(e) =>
                              updateCondition(index, { value_max: e.target.value })
                            }
                            placeholder="Max value"
                            size="sm"
                          />
                        </>
                      )}
                    </HStack>
                  </Box>
                ))}

                {conditions.length === 0 && (
                  <Text color="gray.500" fontSize="sm" textAlign="center" py={4}>
                    No conditions added yet
                  </Text>
                )}
              </VStack>
            </Box>

            <Divider />

            {/* Actions */}
            <Box>
              <HStack justify="space-between" mb={3}>
                <Text fontWeight="medium">Actions</Text>
                <Button leftIcon={<AddIcon />} size="sm" onClick={addAction}>
                  Add Action
                </Button>
              </HStack>

              <VStack spacing={3} align="stretch">
                {actions.map((action, index) => (
                  <Box key={index} p={3} bg="gray.50" borderRadius="md">
                    <HStack spacing={2}>
                      <Select
                        value={action.action_type}
                        onChange={(e) =>
                          updateAction(index, { action_type: e.target.value as ActionType })
                        }
                        size="sm"
                      >
                        <option value="add_label">Add Label</option>
                        <option value="remove_label">Remove Label</option>
                        <option value="set_category">Set Category</option>
                        <option value="set_merchant">Set Merchant</option>
                      </Select>

                      {(action.action_type === 'add_label' ||
                        action.action_type === 'remove_label') && labels ? (
                        <Select
                          value={action.action_value}
                          onChange={(e) => updateAction(index, { action_value: e.target.value })}
                          size="sm"
                          placeholder="Select label"
                        >
                          {labels.map((label) => (
                            <option key={label.id} value={label.id}>
                              {label.name}
                            </option>
                          ))}
                        </Select>
                      ) : (
                        <Input
                          value={action.action_value}
                          onChange={(e) => updateAction(index, { action_value: e.target.value })}
                          placeholder="Value"
                          size="sm"
                        />
                      )}

                      <IconButton
                        icon={<DeleteIcon />}
                        aria-label="Remove action"
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => removeAction(index)}
                      />
                    </HStack>
                  </Box>
                ))}

                {actions.length === 0 && (
                  <Text color="gray.500" fontSize="sm" textAlign="center" py={4}>
                    No actions added yet
                  </Text>
                )}
              </VStack>
            </Box>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button
            colorScheme="brand"
            onClick={handleSave}
            isLoading={createMutation.isPending || updateMutation.isPending}
          >
            {rule ? 'Update Rule' : 'Create Rule'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
