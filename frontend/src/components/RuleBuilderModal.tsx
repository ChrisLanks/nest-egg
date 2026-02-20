/**
 * Rule builder modal for creating automation rules
 */

import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  VStack,
  HStack,
  Text,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Textarea,
  IconButton,
  Box,
  Divider,
  Radio,
  RadioGroup,
  Stack,
  useToast,
} from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { Transaction } from '../types/transaction';
import {
  RuleMatchType,
  RuleApplyTo,
  ConditionField,
  ConditionOperator,
  ActionType,
  type RuleCondition,
  type RuleAction,
  type RuleCreate,
} from '../types/rule';
import api from '../services/api';
import { ConditionValueInput } from './ConditionValueInput';
import { ActionValueInput } from './ActionValueInput';
import { FIELD_OPERATORS, resolveOperatorForField } from '../utils/ruleUtils';

interface RuleBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
  prefilledTransaction?: Transaction;
}

const FIELD_LABELS: Record<ConditionField, string> = {
  [ConditionField.MERCHANT_NAME]: 'Merchant Name',
  [ConditionField.AMOUNT]: 'Amount',
  [ConditionField.AMOUNT_EXACT]: 'Amount (Exact)',
  [ConditionField.CATEGORY]: 'Category',
  [ConditionField.DESCRIPTION]: 'Description',
};

const OPERATOR_LABELS: Record<ConditionOperator, string> = {
  [ConditionOperator.EQUALS]: 'Equals',
  [ConditionOperator.CONTAINS]: 'Contains',
  [ConditionOperator.STARTS_WITH]: 'Starts With',
  [ConditionOperator.ENDS_WITH]: 'Ends With',
  [ConditionOperator.GREATER_THAN]: 'Greater Than',
  [ConditionOperator.LESS_THAN]: 'Less Than',
  [ConditionOperator.BETWEEN]: 'Between',
  [ConditionOperator.REGEX]: 'Regex',
};

// FIELD_OPERATORS and resolveOperatorForField are imported from ../utils/ruleUtils

export const RuleBuilderModal = ({
  isOpen,
  onClose,
  prefilledTransaction,
}: RuleBuilderModalProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [matchType, setMatchType] = useState<RuleMatchType>(RuleMatchType.ALL);
  const [applyTo, setApplyTo] = useState<RuleApplyTo>(RuleApplyTo.NEW_ONLY);
  const [conditions, setConditions] = useState<RuleCondition[]>([]);
  const [actions, setActions] = useState<RuleAction[]>([]);

  const toast = useToast();
  const queryClient = useQueryClient();

  // Pre-fill from transaction
  useEffect(() => {
    if (prefilledTransaction && isOpen) {
      // Set default name
      setName(`Auto-categorize ${prefilledTransaction.merchant_name}`);

      // Add merchant condition
      setConditions([
        {
          field: ConditionField.MERCHANT_NAME,
          operator: ConditionOperator.EQUALS,
          value: prefilledTransaction.merchant_name || '',
        },
      ]);

      // Add category action if present
      // Handle both category object and category_primary string
      const categoryValue = prefilledTransaction.category?.name || prefilledTransaction.category_primary;
      if (categoryValue) {
        setActions([
          {
            action_type: ActionType.SET_CATEGORY,
            action_value: categoryValue,
          },
        ]);
      }
    }
  }, [prefilledTransaction, isOpen]);

  const createRuleMutation = useMutation({
    mutationFn: async (data: RuleCreate) => {
      const response = await api.post('/rules', data);
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Rule created successfully',
        status: 'success',
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      handleClose();
    },
    onError: () => {
      toast({
        title: 'Failed to create rule',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleClose = () => {
    setName('');
    setDescription('');
    setMatchType(RuleMatchType.ALL);
    setApplyTo(RuleApplyTo.NEW_ONLY);
    setConditions([]);
    setActions([]);
    onClose();
  };

  const addCondition = () => {
    setConditions([
      ...conditions,
      {
        field: ConditionField.MERCHANT_NAME,
        operator: ConditionOperator.CONTAINS,
        value: '',
      },
    ]);
  };

  const updateCondition = (index: number, updates: Partial<RuleCondition>) => {
    const newConditions = [...conditions];
    const current = newConditions[index];
    const merged = { ...current, ...updates };

    // If the field changed, keep or reset the operator via the utility
    if (updates.field && updates.field !== current.field) {
      merged.operator = resolveOperatorForField(merged.operator, updates.field);
    }

    newConditions[index] = merged;
    setConditions(newConditions);
  };

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };

  const addAction = () => {
    setActions([
      ...actions,
      {
        action_type: ActionType.SET_CATEGORY,
        action_value: '',
      },
    ]);
  };

  const updateAction = (index: number, updates: Partial<RuleAction>) => {
    const newActions = [...actions];
    newActions[index] = { ...newActions[index], ...updates };
    setActions(newActions);
  };

  const removeAction = (index: number) => {
    setActions(actions.filter((_, i) => i !== index));
  };

  const handleSubmit = () => {
    if (!name.trim()) {
      toast({
        title: 'Name is required',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    if (conditions.length === 0) {
      toast({
        title: 'At least one condition is required',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    if (actions.length === 0) {
      toast({
        title: 'At least one action is required',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    createRuleMutation.mutate({
      name,
      description: description || undefined,
      match_type: matchType,
      apply_to: applyTo,
      priority: 0,
      is_active: true,
      conditions,
      actions,
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="2xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Create Rule</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={6} align="stretch">
            {/* Rule Name */}
            <FormControl isRequired>
              <FormLabel>Rule Name</FormLabel>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Auto-categorize Amazon purchases"
              />
            </FormControl>

            {/* Description */}
            <FormControl>
              <FormLabel>Description</FormLabel>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description of what this rule does"
                rows={2}
              />
            </FormControl>

            <Divider />

            {/* Match Type */}
            <FormControl>
              <FormLabel>Match Type</FormLabel>
              <RadioGroup
                value={matchType}
                onChange={(value) => setMatchType(value as RuleMatchType)}
              >
                <Stack direction="row" spacing={4}>
                  <Radio value={RuleMatchType.ALL}>
                    ALL conditions must match
                  </Radio>
                  <Radio value={RuleMatchType.ANY}>
                    ANY condition can match
                  </Radio>
                </Stack>
              </RadioGroup>
            </FormControl>

            {/* Conditions */}
            <Box>
              <HStack justify="space-between" mb={3}>
                <Text fontWeight="bold" fontSize="lg">
                  Conditions
                </Text>
                <Button
                  size="sm"
                  leftIcon={<AddIcon />}
                  onClick={addCondition}
                  colorScheme="blue"
                >
                  Add Condition
                </Button>
              </HStack>

              <VStack spacing={3} align="stretch">
                {conditions.map((condition, index) => (
                  <Box
                    key={index}
                    p={3}
                    borderWidth={1}
                    borderRadius="md"
                    bg="gray.50"
                  >
                    <HStack spacing={2} align="start">
                      <FormControl flex={1}>
                        <Select
                          size="sm"
                          value={condition.field}
                          onChange={(e) =>
                            updateCondition(index, {
                              field: e.target.value as ConditionField,
                            })
                          }
                        >
                          {Object.entries(FIELD_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </Select>
                      </FormControl>

                      <FormControl flex={1}>
                        <Select
                          size="sm"
                          value={condition.operator}
                          onChange={(e) =>
                            updateCondition(index, {
                              operator: e.target.value as ConditionOperator,
                            })
                          }
                        >
                          {FIELD_OPERATORS[condition.field].map((op) => (
                            <option key={op} value={op}>
                              {OPERATOR_LABELS[op]}
                            </option>
                          ))}
                        </Select>
                      </FormControl>

                      <ConditionValueInput
                        field={condition.field}
                        value={condition.value}
                        onChange={(value) => updateCondition(index, { value })}
                        size="sm"
                      />

                      <IconButton
                        size="sm"
                        icon={<DeleteIcon />}
                        aria-label="Remove condition"
                        onClick={() => removeCondition(index)}
                        colorScheme="red"
                        variant="ghost"
                      />
                    </HStack>
                  </Box>
                ))}

                {conditions.length === 0 && (
                  <Text color="gray.500" textAlign="center" py={4}>
                    No conditions yet. Click "Add Condition" to get started.
                  </Text>
                )}
              </VStack>
            </Box>

            <Divider />

            {/* Actions */}
            <Box>
              <HStack justify="space-between" mb={3}>
                <Text fontWeight="bold" fontSize="lg">
                  Actions
                </Text>
                <Button
                  size="sm"
                  leftIcon={<AddIcon />}
                  onClick={addAction}
                  colorScheme="green"
                >
                  Add Action
                </Button>
              </HStack>

              <VStack spacing={3} align="stretch">
                {actions.map((action, index) => (
                  <Box
                    key={index}
                    p={3}
                    borderWidth={1}
                    borderRadius="md"
                    bg="gray.50"
                  >
                    <HStack spacing={2} align="start">
                      <FormControl flex={1}>
                        <Select
                          size="sm"
                          value={action.action_type}
                          onChange={(e) =>
                            updateAction(index, {
                              action_type: e.target.value as ActionType,
                            })
                          }
                        >
                          <option value={ActionType.SET_CATEGORY}>
                            Set Category
                          </option>
                          <option value={ActionType.ADD_LABEL}>
                            Add Label
                          </option>
                          <option value={ActionType.REMOVE_LABEL}>
                            Remove Label
                          </option>
                          <option value={ActionType.SET_MERCHANT}>
                            Set Merchant
                          </option>
                        </Select>
                      </FormControl>

                      <ActionValueInput
                        actionType={action.action_type}
                        value={action.action_value}
                        onChange={(value) =>
                          updateAction(index, { action_value: value })
                        }
                        size="sm"
                      />

                      <IconButton
                        size="sm"
                        icon={<DeleteIcon />}
                        aria-label="Remove action"
                        onClick={() => removeAction(index)}
                        colorScheme="red"
                        variant="ghost"
                      />
                    </HStack>
                  </Box>
                ))}

                {actions.length === 0 && (
                  <Text color="gray.500" textAlign="center" py={4}>
                    No actions yet. Click "Add Action" to get started.
                  </Text>
                )}
              </VStack>
            </Box>

            <Divider />

            {/* Apply To */}
            <FormControl>
              <FormLabel>Apply To</FormLabel>
              <Select
                value={applyTo}
                onChange={(e) => setApplyTo(e.target.value as RuleApplyTo)}
              >
                <option value={RuleApplyTo.NEW_ONLY}>
                  New Transactions Only
                </option>
                <option value={RuleApplyTo.EXISTING_ONLY}>
                  Existing Transactions Only
                </option>
                <option value={RuleApplyTo.BOTH}>
                  Both New and Existing
                </option>
                <option value={RuleApplyTo.SINGLE}>
                  Single Transaction (one-time)
                </option>
              </Select>
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={handleClose}>
            Cancel
          </Button>
          <Button
            colorScheme="brand"
            onClick={handleSubmit}
            isLoading={createRuleMutation.isPending}
          >
            Create Rule
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
