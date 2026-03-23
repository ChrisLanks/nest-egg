/**
 * Budget card component showing budget progress
 */

import {
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  Progress,
  HStack,
  VStack,
  Badge,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useToast,
  Box,
  Tooltip,
  Collapse,
  Button,
  Skeleton,
} from "@chakra-ui/react";
import { EditIcon, DeleteIcon, SettingsIcon } from "@chakra-ui/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { Budget } from "../../../types/budget";
import { BudgetPeriod } from "../../../types/budget";
import { budgetsApi } from "../../../api/budgets";
import { labelsApi } from "../../../api/labels";
import { useHouseholdMembers } from "../../../hooks/useHouseholdMembers";
import { useAuthStore } from "../../auth/stores/authStore";
import { useCurrency } from "../../../contexts/CurrencyContext";
import api from "../../../services/api";

interface BudgetCardProps {
  budget: Budget;
  onEdit: (budget: Budget) => void;
  canEdit?: boolean;
}

export default function BudgetCard({
  budget,
  onEdit,
  canEdit = true,
}: BudgetCardProps) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data: householdMembers = [] } = useHouseholdMembers();
  const currentUser = useAuthStore((s) => s.user);
  const { formatCurrency } = useCurrency();
  const [varianceOpen, setVarianceOpen] = useState(false);
  const [varianceData, setVarianceData] = useState<any>(null);
  const [varianceLoading, setVarianceLoading] = useState(false);

  // Resolve owner display name
  const ownerName = (() => {
    if (!budget.user_id) return null; // org-wide budget
    if (budget.user_id === currentUser?.id) return "You";
    const member = householdMembers.find((m) => m.id === budget.user_id);
    return member?.display_name || member?.first_name || member?.email || "Member";
  })();

  // Scope label: who this budget covers
  const scopeLabel = (() => {
    if (budget.is_shared) {
      if (!budget.shared_user_ids) return "All members";
      const names = budget.shared_user_ids
        .map((id) => householdMembers.find((m) => m.id === id))
        .filter(Boolean)
        .map((m) => m!.display_name || m!.first_name || m!.email);
      return names.length ? `Shared: ${names.join(", ")}` : "Shared";
    }
    if (!budget.user_id) return "All members";
    return null; // personal budget — owner badge alone is enough
  })();

  // Build shared tooltip label (kept for backward-compat Tooltip)
  const sharedLabel = scopeLabel ?? "";

  // Get spending data
  const { data: spending, isLoading: spendingLoading } = useQuery({
    queryKey: ["budgets", budget.id, "spending"],
    queryFn: () => budgetsApi.getSpending(budget.id),
  });

  // Fetch labels to resolve label name (uses shared cache, no extra network call)
  const { data: allLabels = [] } = useQuery({
    queryKey: ["labels"],
    queryFn: () => labelsApi.getAll(),
    enabled: !!budget.label_id,
  });
  const labelName = budget.label_id
    ? (allLabels.find((l) => l.id === budget.label_id)?.name ?? null)
    : null;

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => budgetsApi.delete(budget.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budgets-widget"] });
      toast({
        title: "Budget deleted",
        status: "success",
        duration: 3000,
      });
    },
    onError: () => {
      toast({
        title: "Failed to delete budget",
        status: "error",
        duration: 3000,
      });
    },
  });

  const percentage = Number(spending?.percentage ?? 0);
  const getProgressColor = () => {
    if (percentage >= 100) return "red";
    if (percentage >= budget.alert_threshold * 100) return "orange";
    return "green";
  };

  const formatPeriod = (period: BudgetPeriod) => {
    switch (period) {
      case BudgetPeriod.MONTHLY:
        return "Monthly";
      case BudgetPeriod.QUARTERLY:
        return "Quarterly";
      case BudgetPeriod.SEMI_ANNUAL:
        return "Every 6 Months";
      case BudgetPeriod.YEARLY:
        return "Yearly";
    }
  };

  // formatCurrency from CurrencyContext (org-aware)

  const handleVarianceClick = async () => {
    if (varianceOpen) {
      setVarianceOpen(false);
      return;
    }
    setVarianceOpen(true);
    if (!varianceData) {
      setVarianceLoading(true);
      try {
        const response = await api.get(`/budgets/${budget.id}/variance`);
        setVarianceData(response.data);
      } catch {
        toast({
          title: "Could not load spending breakdown",
          status: "error",
          duration: 3000,
        });
        setVarianceOpen(false);
      } finally {
        setVarianceLoading(false);
      }
    }
  };

  return (
    <Card>
      <CardHeader pb={2}>
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="md">{budget.name}</Heading>
            <HStack flexWrap="wrap" gap={1}>
              <Badge colorScheme="blue" size="sm">
                {formatPeriod(budget.period)}
              </Badge>
              {/* Owner badge */}
              {ownerName && (
                <Tooltip label={`Created by ${ownerName}`} placement="top">
                  <Badge colorScheme="gray" size="sm" cursor="default">
                    {ownerName}
                  </Badge>
                </Tooltip>
              )}
              {/* Scope badge */}
              {scopeLabel && (
                <Tooltip label={scopeLabel} placement="top">
                  <Badge colorScheme="teal" size="sm" cursor="default">
                    {budget.is_shared ? "Shared" : "All members"}
                  </Badge>
                </Tooltip>
              )}
              {labelName && (
                <Badge colorScheme="purple" size="sm">
                  {labelName}
                </Badge>
              )}
              {!budget.is_active && (
                <Badge colorScheme="gray" size="sm">
                  Inactive
                </Badge>
              )}
              {/* End date badge */}
              {budget.end_date && (() => {
                const endDate = new Date(budget.end_date);
                const now = new Date();
                const isFuture = endDate > now;
                const formatted = endDate.toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                });
                if (isFuture) {
                  return (
                    <Tooltip label={endDate.toLocaleDateString()} placement="top">
                      <Badge colorScheme="yellow" size="sm" cursor="default">
                        Expires {formatted}
                      </Badge>
                    </Tooltip>
                  );
                }
                return (
                  <Badge colorScheme="red" size="sm">
                    Expired
                  </Badge>
                );
              })()}
            </HStack>
          </VStack>

          <Menu>
            <MenuButton
              as={IconButton}
              icon={<SettingsIcon />}
              variant="ghost"
              size="sm"
            />
            <MenuList>
              <MenuItem
                icon={<EditIcon />}
                isDisabled={!canEdit}
                onClick={() => onEdit(budget)}
              >
                Edit
              </MenuItem>
              <MenuItem
                icon={<DeleteIcon />}
                onClick={() => deleteMutation.mutate()}
                isDisabled={!canEdit || deleteMutation.isPending}
                color="red.600"
              >
                Delete
              </MenuItem>
            </MenuList>
          </Menu>
        </HStack>
      </CardHeader>

      <CardBody>
        <VStack align="stretch" spacing={3}>
          {/* Progress bar */}
          <Box>
            <HStack justify="space-between" mb={2}>
              {spendingLoading ? (
                <Skeleton height="16px" width="160px" />
              ) : (
                <Text fontSize="sm" fontWeight="medium">
                  {formatCurrency(spending?.spent ?? 0)} of{" "}
                  {formatCurrency(budget.amount)}
                </Text>
              )}
              {spendingLoading ? (
                <Skeleton height="16px" width="40px" />
              ) : (
                <Text fontSize="sm" color={getProgressColor()}>
                  {percentage.toFixed(1)}%
                </Text>
              )}
            </HStack>
            {spendingLoading ? (
              <Skeleton height="16px" borderRadius="md" />
            ) : (
              <Progress
                value={percentage}
                colorScheme={getProgressColor()}
                size="lg"
                borderRadius="md"
              />
            )}
          </Box>

          {/* Remaining amount */}
          <HStack justify="space-between">
            <Text fontSize="sm" color={spending?.remaining != null && spending.remaining < 0 ? "finance.negative" : "text.secondary"}>
              {spending?.remaining != null && spending.remaining < 0 ? "Over budget" : "Remaining"}
            </Text>
            {spendingLoading ? (
              <Skeleton height="16px" width="80px" />
            ) : (
              <Text
                fontSize="sm"
                fontWeight="medium"
                color={
                  spending?.remaining && spending.remaining < 0
                    ? "finance.negative"
                    : "finance.positive"
                }
              >
                {spending?.remaining != null && spending.remaining < 0
                  ? formatCurrency(Math.abs(spending.remaining))
                  : formatCurrency(spending?.remaining ?? budget.amount)}
              </Text>
            )}
          </HStack>

          {/* Rollover info */}
          {spending && spending.rollover_amount != null && spending.rollover_amount > 0 && (
            <Text fontSize="xs" color="text.muted">
              + {formatCurrency(spending.rollover_amount)} rollover from last period
            </Text>
          )}

          {/* Period dates */}
          {spending && (
            <Text fontSize="xs" color="text.muted">
              {new Date(spending.period_start).toLocaleDateString()} -{" "}
              {new Date(spending.period_end).toLocaleDateString()}
            </Text>
          )}

          {/* "Why?" variance button — shown when over 80% */}
          {percentage >= 80 && (
            <Box>
              <Button
                size="xs"
                variant="ghost"
                colorScheme="orange"
                onClick={handleVarianceClick}
                isLoading={varianceLoading}
              >
                {varianceOpen ? "Hide breakdown" : "Why? View breakdown"}
              </Button>

              <Collapse in={varianceOpen && !!varianceData} animateOpacity>
                {varianceData && (
                  <Box mt={2} p={3} bg="bg.subtle" borderRadius="md" fontSize="sm">
                    <Text fontWeight="semibold" mb={2} fontSize="xs">
                      Top merchants this period
                    </Text>
                    <VStack align="stretch" spacing={1}>
                      {(varianceData.merchant_breakdown || []).slice(0, 5).map(
                        (m: any, i: number) => (
                          <HStack key={i} justify="space-between">
                            <Text fontSize="xs" noOfLines={1} flex={1}>
                              {m.merchant_name}
                            </Text>
                            <Text fontSize="xs" color="text.secondary" flexShrink={0}>
                              {formatCurrency(m.amount)} ({m.transaction_count} txn{m.transaction_count !== 1 ? "s" : ""})
                            </Text>
                          </HStack>
                        )
                      )}
                    </VStack>
                    {varianceData.largest_transactions?.length > 0 && (
                      <Box mt={2}>
                        <Text fontWeight="semibold" mb={1} fontSize="xs">
                          Largest transactions
                        </Text>
                        <VStack align="stretch" spacing={1}>
                          {varianceData.largest_transactions.map((t: any) => (
                            <HStack key={t.id} justify="space-between">
                              <Text fontSize="xs" noOfLines={1} flex={1}>
                                {t.merchant_name}
                              </Text>
                              <Text fontSize="xs" color="finance.negative" flexShrink={0}>
                                {formatCurrency(t.amount)}
                              </Text>
                            </HStack>
                          ))}
                        </VStack>
                      </Box>
                    )}
                  </Box>
                )}
              </Collapse>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
}
