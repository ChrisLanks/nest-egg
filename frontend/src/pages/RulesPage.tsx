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
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  Alert,
  AlertIcon,
  Input,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from "@chakra-ui/react";
import { useState, useRef, useMemo, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DeleteIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  AddIcon,
  EditIcon,
} from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import { RuleBuilderModal } from "../components/RuleBuilderModal";
import type { Rule } from "../types/rule";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { HelpHint } from "../components/HelpHint";
import { helpContent } from "../constants/helpContent";

const FIELD_LABELS: Record<string, string> = {
  merchant_name: "Merchant",
  amount: "Amount",
  amount_exact: "Amount (Exact)",
  category: "Category",
  description: "Description",
};

const OPERATOR_LABELS: Record<string, string> = {
  equals: "=",
  contains: "contains",
  starts_with: "starts with",
  ends_with: "ends with",
  greater_than: ">",
  less_than: "<",
  between: "between",
  regex: "matches regex",
};

const ACTION_LABELS: Record<string, string> = {
  set_category: "Set category",
  add_label: "Add label",
  remove_label: "Remove label",
  set_merchant: "Set merchant",
};

export const RulesPage = () => {
  const [isRuleBuilderOpen, setIsRuleBuilderOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [expandedRule, setExpandedRule] = useState<string | null>(null);
  const [merchantAliases, setMerchantAliases] = useState<
    Record<string, string>
  >({});
  const [showMerchantAliases, setShowMerchantAliases] = useState(false);
  const toast = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { canWriteResource } = useUserView();
  const canEdit = canWriteResource("rule");

  // Confirmation dialog state
  const {
    isOpen: isConfirmOpen,
    onOpen: onConfirmOpen,
    onClose: onConfirmClose,
  } = useDisclosure();
  const confirmCancelRef = useRef<HTMLButtonElement>(null);
  const [confirmConfig, setConfirmConfig] = useState<{
    title: string;
    body: string;
    confirmLabel: string;
    colorScheme: string;
    onConfirm: () => void;
  }>({
    title: "",
    body: "",
    confirmLabel: "Confirm",
    colorScheme: "red",
    onConfirm: () => {},
  });

  const openConfirmDialog = (config: {
    title: string;
    body: string;
    confirmLabel?: string;
    colorScheme?: string;
    onConfirm: () => void;
  }) => {
    setConfirmConfig({
      title: config.title,
      body: config.body,
      confirmLabel: config.confirmLabel || "Confirm",
      colorScheme: config.colorScheme || "red",
      onConfirm: config.onConfirm,
    });
    onConfirmOpen();
  };

  const { data: rules, isLoading, isError } = useQuery({
    queryKey: ["rules"],
    queryFn: async () => {
      const response = await api.get<Rule[]>("/rules");
      return response.data;
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: async ({
      ruleId,
      isActive,
    }: {
      ruleId: string;
      isActive: boolean;
    }) => {
      const response = await api.patch(`/rules/${ruleId}`, {
        is_active: isActive,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      toast({
        title: "Rule updated",
        status: "success",
        duration: 2000,
      });
    },
    onError: () => {
      toast({
        title: "Failed to update rule",
        status: "error",
        duration: 5000,
      });
    },
  });

  const hasDividendRule = useMemo(
    () => rules?.some((r) => r.name === "Dividend Income Detection") ?? false,
    [rules],
  );

  const seedDividendRuleMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post<Rule>("/rules/seed-dividend-detection");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      toast({
        title: "Dividend detection rule added",
        description:
          "You can customize the patterns and actions in the rule editor.",
        status: "success",
        duration: 4000,
      });
    },
    onError: () => {
      toast({
        title: "Failed to add dividend rule",
        status: "error",
        duration: 5000,
      });
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: async (ruleId: string) => {
      await api.delete(`/rules/${ruleId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      toast({
        title: "Rule deleted",
        status: "success",
        duration: 2000,
      });
    },
    onError: () => {
      toast({
        title: "Failed to delete rule",
        status: "error",
        duration: 5000,
      });
    },
  });

  const handleToggleActive = (ruleId: string, isActive: boolean) => {
    toggleActiveMutation.mutate({ ruleId, isActive: !isActive });
  };

  const handleDelete = (ruleId: string, ruleName: string) => {
    openConfirmDialog({
      title: "Delete Rule",
      body: `Are you sure you want to delete the rule "${ruleName}"?`,
      confirmLabel: "Delete",
      colorScheme: "red",
      onConfirm: () => deleteRuleMutation.mutate(ruleId),
    });
  };

  const toggleExpanded = (ruleId: string) => {
    setExpandedRule(expandedRule === ruleId ? null : ruleId);
  };

  // Fetch distinct merchants for the alias section
  const { data: merchantList } = useQuery({
    queryKey: ["merchants"],
    queryFn: async () => {
      const response = await api.get<
        Array<{ merchant_name: string; transaction_count: number }>
      >("/transactions/merchants");
      return response.data;
    },
    enabled: showMerchantAliases,
  });

  // Pre-populate alias inputs from existing SET_MERCHANT rules
  useEffect(() => {
    if (!rules) return;
    const initialAliases: Record<string, string> = {};
    rules.forEach((rule) => {
      if (rule.actions?.[0]?.action_type === "set_merchant") {
        const cond = rule.conditions?.[0];
        if (cond?.field === "merchant_name" && cond?.operator === "equals") {
          initialAliases[cond.value] = rule.actions[0].action_value ?? "";
        }
      }
    });
    setMerchantAliases((prev) => ({ ...initialAliases, ...prev }));
  }, [rules]);

  const saveMerchantAlias = async (rawName: string, displayName: string) => {
    if (!displayName.trim() || displayName === rawName) return;
    try {
      await api.post("/rules", {
        name: `Alias: ${rawName}`,
        is_active: true,
        conditions: [
          { field: "merchant_name", operator: "equals", value: rawName },
        ],
        actions: [
          { action_type: "set_merchant", action_value: displayName.trim() },
        ],
      });
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      toast({
        title: "Merchant alias saved",
        status: "success",
        duration: 2000,
      });
    } catch {
      toast({ title: "Failed to save alias", status: "error", duration: 3000 });
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  if (isError) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          Failed to load rules. Please refresh and try again.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between" align="start">
          <Box>
            <Heading size="lg">Rules</Heading>
            <Text color="text.secondary" mt={2}>
              Manage automation rules for transaction categorization.{" "}
              {rules?.length || 0} rule(s) total.
            </Text>
          </Box>
          <HStack>
            <Button variant="ghost" onClick={() => navigate("/transactions")}>
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

        {/* Suggested rules banner */}
        {!hasDividendRule && canEdit && (
          <Card
            variant="outline"
            borderColor="green.200"
            bg="green.50"
            _dark={{ bg: "green.900", borderColor: "green.700" }}
          >
            <CardBody py={3} px={4}>
              <HStack justify="space-between" align="center">
                <Box>
                  <HStack spacing={2} mb={1}>
                    <Text fontWeight="semibold" fontSize="sm">
                      Suggested: Dividend Income Detection
                    </Text>
                    <Badge colorScheme="green" fontSize="2xs">
                      Recommended
                    </Badge>
                  </HStack>
                  <Text fontSize="xs" color="text.muted">
                    Auto-labels dividend, interest, and capital gain
                    transactions from your linked accounts. Fully customizable
                    after setup.
                  </Text>
                </Box>
                <Button
                  size="sm"
                  colorScheme="green"
                  onClick={() => seedDividendRuleMutation.mutate()}
                  isLoading={seedDividendRuleMutation.isPending}
                >
                  Add Rule
                </Button>
              </HStack>
            </CardBody>
          </Card>
        )}

        {rules && rules.length === 0 ? (
          <Box
            bg="bg.surface"
            p={12}
            borderRadius="lg"
            boxShadow="sm"
            textAlign="center"
          >
            <Text fontSize="lg" color="text.secondary" mb={4}>
              No rules created yet
            </Text>
            <Text color="text.muted" mb={6}>
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
                            icon={
                              isExpanded ? (
                                <ChevronUpIcon />
                              ) : (
                                <ChevronDownIcon />
                              )
                            }
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
                              <Badge
                                colorScheme={rule.is_active ? "green" : "gray"}
                              >
                                {rule.is_active ? "Active" : "Inactive"}
                              </Badge>
                              <Badge colorScheme="purple">
                                {rule.match_type === "all"
                                  ? "ALL conditions"
                                  : "ANY condition"}
                                <HelpHint
                                  hint={
                                    rule.match_type === "all"
                                      ? helpContent.rules.matchAll
                                      : helpContent.rules.matchAny
                                  }
                                />
                              </Badge>
                              <Badge colorScheme="blue">
                                {rule.apply_to === "new_only" && "New only"}
                                {rule.apply_to === "existing_only" &&
                                  "Existing only"}
                                {rule.apply_to === "both" && "New & existing"}
                                {rule.apply_to === "single" && "Single use"}
                                <HelpHint hint={helpContent.rules.applyTo} />
                              </Badge>
                            </HStack>
                            {rule.description && (
                              <Text fontSize="sm" color="text.secondary">
                                {rule.description}
                              </Text>
                            )}
                            <Text fontSize="xs" color="text.muted" mt={1}>
                              Applied {rule.times_applied} times
                              {rule.last_applied_at &&
                                ` • Last: ${formatDate(rule.last_applied_at)}`}
                            </Text>
                          </Box>
                        </HStack>

                        <HStack spacing={2}>
                          <HStack spacing={2}>
                            <Text fontSize="sm" color="text.secondary">
                              {rule.is_active ? "Enabled" : "Disabled"}
                            </Text>
                            <Switch
                              colorScheme="green"
                              isChecked={rule.is_active}
                              onChange={() =>
                                handleToggleActive(rule.id, rule.is_active)
                              }
                              isDisabled={
                                !canEdit || toggleActiveMutation.isPending
                              }
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
                            <Text
                              fontWeight="semibold"
                              fontSize="sm"
                              color="text.heading"
                              mb={2}
                            >
                              Conditions ({rule.conditions?.length || 0}):
                              <HelpHint hint={helpContent.rules.conditions} />
                            </Text>
                            <VStack align="stretch" spacing={1}>
                              {rule.conditions?.map((condition, idx) => (
                                <HStack
                                  key={condition.id}
                                  spacing={2}
                                  fontSize="sm"
                                >
                                  <Badge colorScheme="blue" variant="subtle">
                                    {idx + 1}
                                  </Badge>
                                  <Text>
                                    {FIELD_LABELS[condition.field] ||
                                      condition.field}
                                  </Text>
                                  <Text fontWeight="semibold">
                                    {OPERATOR_LABELS[condition.operator] ||
                                      condition.operator}
                                  </Text>
                                  <Text fontWeight="medium" color="blue.600">
                                    "{condition.value}"
                                  </Text>
                                  {condition.value_max && (
                                    <>
                                      <Text>and</Text>
                                      <Text
                                        fontWeight="medium"
                                        color="blue.600"
                                      >
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
                            <Text
                              fontWeight="semibold"
                              fontSize="sm"
                              color="text.heading"
                              mb={2}
                            >
                              Actions ({rule.actions?.length || 0}):
                              <HelpHint hint={helpContent.rules.actions} />
                            </Text>
                            <VStack align="stretch" spacing={1}>
                              {rule.actions?.map((action, idx) => (
                                <HStack
                                  key={action.id}
                                  spacing={2}
                                  fontSize="sm"
                                >
                                  <Badge colorScheme="green" variant="subtle">
                                    {idx + 1}
                                  </Badge>
                                  <Text>
                                    {ACTION_LABELS[action.action_type] ||
                                      action.action_type}
                                  </Text>
                                  <Text>to</Text>
                                  <Text fontWeight="medium" color="green.600">
                                    "{action.action_value}"
                                  </Text>
                                </HStack>
                              ))}
                            </VStack>
                          </Box>

                          <Text fontSize="xs" color="text.muted" mt={4}>
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

        {/* Merchant Aliases section */}
        <Card variant="outline">
          <CardBody>
            <HStack justify="space-between" mb={2}>
              <Heading size="sm">Merchant Aliases</Heading>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowMerchantAliases(!showMerchantAliases)}
                rightIcon={
                  showMerchantAliases ? (
                    <ChevronUpIcon />
                  ) : (
                    <ChevronDownIcon />
                  )
                }
              >
                {showMerchantAliases ? "Hide" : "Show"}
              </Button>
            </HStack>
            <Text fontSize="sm" color="text.secondary" mb={2}>
              Set display names for raw merchant names from your transactions.
            </Text>
            <Collapse in={showMerchantAliases}>
              {merchantList && merchantList.length > 0 ? (
                <Table size="sm" variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Raw Name</Th>
                      <Th># Txns</Th>
                      <Th>Display Name</Th>
                      <Th />
                    </Tr>
                  </Thead>
                  <Tbody>
                    {merchantList.slice(0, 50).map((m) => (
                      <Tr key={m.merchant_name}>
                        <Td fontSize="sm">{m.merchant_name}</Td>
                        <Td fontSize="sm" isNumeric>
                          {m.transaction_count}
                        </Td>
                        <Td>
                          <Input
                            size="sm"
                            placeholder={m.merchant_name}
                            value={merchantAliases[m.merchant_name] ?? ""}
                            onChange={(e) =>
                              setMerchantAliases((prev) => ({
                                ...prev,
                                [m.merchant_name]: e.target.value,
                              }))
                            }
                          />
                        </Td>
                        <Td>
                          <Button
                            size="xs"
                            colorScheme="brand"
                            isDisabled={!canEdit}
                            onClick={() =>
                              saveMerchantAlias(
                                m.merchant_name,
                                merchantAliases[m.merchant_name] ?? ""
                              )
                            }
                          >
                            Save
                          </Button>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              ) : (
                <Text fontSize="sm" color="text.secondary">
                  {merchantList ? "No merchants found." : "Loading…"}
                </Text>
              )}
            </Collapse>
          </CardBody>
        </Card>

        <RuleBuilderModal
          isOpen={isRuleBuilderOpen}
          onClose={() => {
            setIsRuleBuilderOpen(false);
            setEditingRule(null);
          }}
          rule={editingRule ?? undefined}
        />

        {/* Confirmation dialog */}
        <AlertDialog
          isOpen={isConfirmOpen}
          leastDestructiveRef={confirmCancelRef}
          onClose={onConfirmClose}
          isCentered
        >
          <AlertDialogOverlay>
            <AlertDialogContent>
              <AlertDialogHeader fontSize="lg" fontWeight="bold">
                {confirmConfig.title}
              </AlertDialogHeader>
              <AlertDialogBody>{confirmConfig.body}</AlertDialogBody>
              <AlertDialogFooter>
                <Button ref={confirmCancelRef} onClick={onConfirmClose}>
                  Cancel
                </Button>
                <Button
                  colorScheme={confirmConfig.colorScheme}
                  ml={3}
                  onClick={() => {
                    confirmConfig.onConfirm();
                    onConfirmClose();
                  }}
                >
                  {confirmConfig.confirmLabel}
                </Button>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialogOverlay>
        </AlertDialog>
      </VStack>
    </Container>
  );
};
