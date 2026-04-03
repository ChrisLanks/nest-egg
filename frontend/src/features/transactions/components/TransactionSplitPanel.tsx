/**
 * TransactionSplitPanel — view and edit splits for a transaction.
 *
 * A "split" breaks a single transaction into labelled sub-amounts that still
 * sum to the parent transaction's absolute value.  Each split can optionally
 * be assigned to a household member so per-member settlement balances can be
 * computed.
 */

import {
  VStack,
  HStack,
  Text,
  Input,
  Button,
  IconButton,
  Alert,
  AlertIcon,
  AlertDescription,
  Box,
  Divider,
  Spinner,
  Badge,
  NumberInput,
  NumberInputField,
  Select,
} from "@chakra-ui/react";
import { DeleteIcon, AddIcon } from "@chakra-ui/icons";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { Transaction } from "../../../types/transaction";
import type { TransactionSplit } from "../../../types/transaction-split";
import { transactionSplitsApi } from "../../../api/transaction-splits";
import { useHouseholdMembers } from "../../../hooks/useHouseholdMembers";

// ── Pure validation logic (also exported for tests) ──────────────────────────

export const SPLIT_TOLERANCE = 0.005; // half a cent tolerance for float rounding

/**
 * Returns true when the given split amounts sum to the expected total within
 * floating-point tolerance.
 */
export function isSplitSumValid(amounts: number[], total: number): boolean {
  if (amounts.length === 0) return false;
  const sum = amounts.reduce((acc, v) => acc + v, 0);
  return Math.abs(sum - total) < SPLIT_TOLERANCE;
}

/** Returns true when every amount is a positive finite number. */
export function areSplitAmountsPositive(amounts: number[]): boolean {
  return amounts.every((v) => Number.isFinite(v) && v > 0);
}

// ── Component-local types ─────────────────────────────────────────────────────

interface SplitRow {
  amount: string; // string so the NumberInput can be partially typed
  description: string;
  assigned_user_id: string; // "" = unassigned
}

const DEFAULT_ROW: SplitRow = { amount: "", description: "", assigned_user_id: "" };

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatAmount(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Math.abs(n));
}

// ── Subcomponents ─────────────────────────────────────────────────────────────

interface ExistingSplitsListProps {
  splits: TransactionSplit[];
  memberNames: Record<string, string>;
}

function ExistingSplitsList({ splits, memberNames }: ExistingSplitsListProps) {
  return (
    <VStack align="stretch" spacing={2}>
      {splits.map((split, idx) => (
        <HStack
          key={split.id}
          justify="space-between"
          p={3}
          bg="bg.subtle"
          borderRadius="md"
          borderWidth="1px"
          borderColor="border.subtle"
        >
          <HStack spacing={3}>
            <Badge colorScheme="gray" fontSize="xs" minW="24px" textAlign="center">
              {idx + 1}
            </Badge>
            <VStack align="start" spacing={0}>
              <Text fontWeight="medium" fontSize="sm">
                {formatAmount(split.amount)}
              </Text>
              {split.description && (
                <Text fontSize="xs" color="text.muted">
                  {split.description}
                </Text>
              )}
              {split.assigned_user_id && (
                <Text fontSize="xs" color="brand.600" fontWeight="medium">
                  {memberNames[split.assigned_user_id] ?? "Member"}
                </Text>
              )}
            </VStack>
          </HStack>
        </HStack>
      ))}
    </VStack>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface TransactionSplitPanelProps {
  transaction: Transaction;
  canEdit: boolean;
}

export const TransactionSplitPanel = ({
  transaction,
  canEdit,
}: TransactionSplitPanelProps) => {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [rows, setRows] = useState<SplitRow[]>([
    { ...DEFAULT_ROW },
    { ...DEFAULT_ROW },
  ]);

  // ── Data fetching ───────────────────────────────────────────────────────────

  const {
    data: splits,
    isLoading,
    isError,
  } = useQuery<TransactionSplit[]>({
    queryKey: ["transaction-splits", transaction.id],
    queryFn: () => transactionSplitsApi.getByTransaction(transaction.id),
  });

  const { data: members = [] } = useHouseholdMembers();

  const memberNames: Record<string, string> = Object.fromEntries(
    members.map((m) => [m.id, m.display_name || m.first_name || m.email])
  );

  // ── Mutations ───────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: () => {
      const splitPayloads = rows
        .filter((r) => r.amount !== "")
        .map((r) => ({
          amount: Math.abs(parseFloat(r.amount)),
          description: r.description.trim() || null,
          category_id: null,
          assigned_user_id: r.assigned_user_id || null,
        }));
      return transactionSplitsApi.create({
        transaction_id: transaction.id,
        splits: splitPayloads,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["transaction-splits", transaction.id],
      });
      queryClient.invalidateQueries({ queryKey: ["member-balances"] });
      setIsEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => transactionSplitsApi.delete(transaction.id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["transaction-splits", transaction.id],
      });
      queryClient.invalidateQueries({ queryKey: ["member-balances"] });
    },
  });

  // ── Derived state ───────────────────────────────────────────────────────────

  const hasSplits = Array.isArray(splits) && splits.length > 0;
  const total = Math.abs(transaction.amount);

  const filledRows = rows.filter((r) => r.amount !== "");
  const rowAmounts = filledRows.map((r) => Math.abs(parseFloat(r.amount) || 0));
  const currentSum = rowAmounts.reduce((a, b) => a + b, 0);
  const remaining = Math.max(0, total - currentSum);

  const canSave =
    filledRows.length >= 2 &&
    areSplitAmountsPositive(rowAmounts) &&
    isSplitSumValid(rowAmounts, total);

  const sumError =
    filledRows.length > 0 && !isSplitSumValid(rowAmounts, total)
      ? currentSum > total
        ? `Splits exceed total by ${formatAmount(currentSum - total)}`
        : `Splits are ${formatAmount(total - currentSum)} short of total`
      : null;

  // ── Row handlers ────────────────────────────────────────────────────────────

  const handleAmountChange = (idx: number, value: string) => {
    setRows((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], amount: value };
      return next;
    });
  };

  const handleDescriptionChange = (idx: number, value: string) => {
    setRows((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], description: value };
      return next;
    });
  };

  const handleMemberChange = (idx: number, value: string) => {
    setRows((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], assigned_user_id: value };
      return next;
    });
  };

  const handleAddRow = () => {
    setRows((prev) => [...prev, { ...DEFAULT_ROW }]);
  };

  const handleDeleteRow = (idx: number) => {
    setRows((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleStartEditing = () => {
    setRows([{ ...DEFAULT_ROW }, { ...DEFAULT_ROW }]);
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setRows([{ ...DEFAULT_ROW }, { ...DEFAULT_ROW }]);
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <HStack justify="center" py={6}>
        <Spinner size="sm" />
        <Text fontSize="sm" color="text.muted">
          Loading splits…
        </Text>
      </HStack>
    );
  }

  if (isError) {
    return (
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        <AlertDescription>Failed to load splits.</AlertDescription>
      </Alert>
    );
  }

  return (
    <VStack align="stretch" spacing={4}>
      {/* Header row */}
      <HStack justify="space-between">
        <Box>
          <Text fontSize="sm" fontWeight="medium" color="text.heading">
            Split Transaction
          </Text>
          <Text fontSize="xs" color="text.muted">
            Total: {formatAmount(total)}
          </Text>
        </Box>

        {hasSplits && canEdit && !isEditing && (
          <Button
            size="sm"
            colorScheme="red"
            variant="outline"
            onClick={() => deleteMutation.mutate()}
            isLoading={deleteMutation.isPending}
          >
            Remove All Splits
          </Button>
        )}
      </HStack>

      <Divider />

      {/* Existing splits (read-only view) */}
      {hasSplits && !isEditing && (
        <ExistingSplitsList splits={splits} memberNames={memberNames} />
      )}

      {/* Prompt to add splits when none exist */}
      {!hasSplits && !isEditing && canEdit && (
        <VStack spacing={3} py={2}>
          <Text fontSize="sm" color="text.muted" textAlign="center">
            No splits yet. Split this transaction to categorize it differently
            across multiple line items.
          </Text>
          <Button
            size="sm"
            colorScheme="brand"
            leftIcon={<AddIcon />}
            onClick={handleStartEditing}
          >
            Add Split
          </Button>
        </VStack>
      )}

      {!hasSplits && !isEditing && !canEdit && (
        <Text fontSize="sm" color="text.muted" textAlign="center" py={2}>
          No splits for this transaction.
        </Text>
      )}

      {/* Split editor */}
      {isEditing && (
        <VStack align="stretch" spacing={3}>
          {/* Remaining helper */}
          {filledRows.length > 0 && (
            <HStack justify="flex-end">
              <Text fontSize="xs" color={remaining > 0 ? "text.muted" : "finance.positive"}>
                Remaining: {formatAmount(remaining)}
              </Text>
            </HStack>
          )}

          {/* Split rows */}
          {rows.map((row, idx) => (
            <HStack key={idx} spacing={2} align="flex-start">
              {/* Amount */}
              <NumberInput
                value={row.amount}
                onChange={(val) => handleAmountChange(idx, val)}
                min={0.01}
                precision={2}
                size="sm"
                maxW="110px"
              >
                <NumberInputField placeholder="0.00" />
              </NumberInput>

              {/* Description */}
              <Input
                size="sm"
                placeholder="Description"
                value={row.description}
                onChange={(e) => handleDescriptionChange(idx, e.target.value)}
                flex={1}
              />

              {/* Member assignment */}
              {members.length > 1 && (
                <Select
                  size="sm"
                  maxW="140px"
                  value={row.assigned_user_id}
                  onChange={(e) => handleMemberChange(idx, e.target.value)}
                  placeholder="Assign to…"
                >
                  {members.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.display_name || m.first_name || m.email}
                    </option>
                  ))}
                </Select>
              )}

              {/* Delete row */}
              <IconButton
                aria-label="Remove split row"
                icon={<DeleteIcon />}
                size="sm"
                variant="ghost"
                colorScheme="red"
                onClick={() => handleDeleteRow(idx)}
                isDisabled={rows.length <= 2}
              />
            </HStack>
          ))}

          {/* Add row */}
          <Button
            size="xs"
            variant="ghost"
            leftIcon={<AddIcon />}
            onClick={handleAddRow}
            alignSelf="flex-start"
          >
            Add row
          </Button>

          {/* Validation error */}
          {sumError && filledRows.length >= 2 && (
            <Alert status="warning" borderRadius="md" py={2}>
              <AlertIcon />
              <AlertDescription fontSize="sm">{sumError}</AlertDescription>
            </Alert>
          )}

          {/* Save / Cancel */}
          <HStack spacing={2} pt={1}>
            <Button
              size="sm"
              colorScheme="brand"
              onClick={() => createMutation.mutate()}
              isLoading={createMutation.isPending}
              isDisabled={!canSave}
            >
              Save Splits
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleCancel}
              isDisabled={createMutation.isPending}
            >
              Cancel
            </Button>
          </HStack>
        </VStack>
      )}
    </VStack>
  );
};
