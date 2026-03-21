/**
 * TransactionMergeModal — find and merge duplicate transactions.
 *
 * Uses autoDetect (dry_run=true) to surface groups of potential duplicates,
 * then lets the user confirm which transaction to keep as the "primary"
 * before calling merge() for each group.
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
  Spinner,
  Alert,
  AlertIcon,
  AlertDescription,
  Badge,
  Box,
  Divider,
  Radio,
  RadioGroup,
  Stack,
  useToast,
} from "@chakra-ui/react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Transaction } from "../../../types/transaction";
import { transactionMergesApi } from "../../../api/transaction-merges";

// ── Pure logic helpers (also exported for tests) ──────────────────────────────

export interface DuplicateGroup {
  primary: Transaction;
  duplicates: Transaction[];
}

/**
 * Groups raw autoDetect matches into DuplicateGroup objects.
 * The initial primary is the one the backend suggested.
 */
export function buildDuplicateGroups(
  matches: Array<{ primary: Transaction; duplicates: Transaction[] }>
): DuplicateGroup[] {
  return matches.map((m) => ({ primary: m.primary, duplicates: m.duplicates }));
}

/**
 * Returns true when the group has a valid primary selection — i.e. the
 * primaryId is one of the transaction ids in the group (primary or one of the
 * duplicates).
 */
export function isPrimaryValid(
  group: DuplicateGroup,
  primaryId: string
): boolean {
  if (!primaryId) return false;
  const allIds = [group.primary.id, ...group.duplicates.map((d) => d.id)];
  return allIds.includes(primaryId);
}

/**
 * Given a map of groupIndex → chosen primaryId, returns true when every group
 * has a valid primary selected.
 */
export function allGroupsHavePrimary(
  groups: DuplicateGroup[],
  selections: Record<number, string>
): boolean {
  return groups.every((g, i) => isPrimaryValid(g, selections[i] ?? ""));
}

/**
 * Group transactions by matching date + amount (rounded to 2 dp).
 * Returns only sets with more than one transaction.
 */
export function groupByDateAndAmount(
  transactions: Transaction[]
): Transaction[][] {
  const map = new Map<string, Transaction[]>();
  for (const t of transactions) {
    const key = `${t.date}|${Math.abs(t.amount).toFixed(2)}`;
    const existing = map.get(key);
    if (existing) {
      existing.push(t);
    } else {
      map.set(key, [t]);
    }
  }
  return Array.from(map.values()).filter((g) => g.length > 1);
}

// ── Sub-components ────────────────────────────────────────────────────────────

function TransactionRow({ txn }: { txn: Transaction }) {
  const label =
    txn.merchant_name ?? txn.description ?? txn.category_primary ?? "—";
  const amount = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Math.abs(txn.amount));

  return (
    <HStack justify="space-between" w="full" py={1}>
      <VStack align="start" spacing={0} flex={1} minW={0}>
        <Text fontWeight="medium" noOfLines={1} fontSize="sm">
          {label}
        </Text>
        <HStack spacing={2}>
          <Text fontSize="xs" color="text.secondary">
            {txn.date}
          </Text>
          {txn.account_name && (
            <Badge fontSize="xs" variant="subtle" colorScheme="gray">
              {txn.account_name}
              {txn.account_mask ? ` ···${txn.account_mask}` : ""}
            </Badge>
          )}
          {txn.is_pending && (
            <Badge fontSize="xs" colorScheme="orange">
              Pending
            </Badge>
          )}
        </HStack>
      </VStack>
      <Text
        fontWeight="semibold"
        fontSize="sm"
        color={txn.amount < 0 ? "red.500" : "green.500"}
        flexShrink={0}
      >
        {txn.amount < 0 ? "-" : "+"}
        {amount}
      </Text>
    </HStack>
  );
}

interface DuplicateGroupCardProps {
  group: DuplicateGroup;
  groupIndex: number;
  selectedPrimaryId: string;
  onSelectPrimary: (groupIndex: number, id: string) => void;
}

function DuplicateGroupCard({
  group,
  groupIndex,
  selectedPrimaryId,
  onSelectPrimary,
}: DuplicateGroupCardProps) {
  const allTxns = [group.primary, ...group.duplicates];

  return (
    <Box
      border="1px solid"
      borderColor="border.subtle"
      borderRadius="md"
      p={4}
      bg="bg.surface"
    >
      <Text fontSize="xs" fontWeight="semibold" color="text.muted" mb={3}>
        GROUP {groupIndex + 1} — {allTxns.length} possible duplicates
      </Text>
      <RadioGroup
        value={selectedPrimaryId}
        onChange={(id) => onSelectPrimary(groupIndex, id)}
      >
        <Stack spacing={2}>
          {allTxns.map((txn) => (
            <Box
              key={txn.id}
              border="1px solid"
              borderColor={
                selectedPrimaryId === txn.id ? "brand.400" : "border.subtle"
              }
              borderRadius="md"
              px={3}
              py={2}
              bg={selectedPrimaryId === txn.id ? "bg.info" : undefined}
              cursor="pointer"
              onClick={() => onSelectPrimary(groupIndex, txn.id)}
            >
              <HStack spacing={3} align="center">
                <Radio value={txn.id} onClick={(e) => e.stopPropagation()} />
                <Box flex={1} minW={0}>
                  <TransactionRow txn={txn} />
                </Box>
              </HStack>
            </Box>
          ))}
        </Stack>
      </RadioGroup>
      <Text fontSize="xs" color="text.muted" mt={3}>
        Select the transaction to keep. The others will be marked as duplicates.
      </Text>
    </Box>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface TransactionMergeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type ViewState = "loading" | "empty" | "results" | "merging" | "success";

export function TransactionMergeModal({
  isOpen,
  onClose,
}: TransactionMergeModalProps) {
  const toast = useToast();
  const queryClient = useQueryClient();

  const [viewState, setViewState] = useState<ViewState>("loading");
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  // selections: groupIndex → chosen primaryId
  const [selections, setSelections] = useState<Record<number, string>>({});
  const [mergeError, setMergeError] = useState<string | null>(null);

  // ── Auto-detect duplicates on open ─────────────────────────────────────────

  const detectMutation = useMutation({
    mutationFn: () => transactionMergesApi.autoDetect({ dry_run: true }),
    onSuccess: (data) => {
      const built = buildDuplicateGroups(data.matches);
      setGroups(built);
      // Pre-select the backend-suggested primary for each group
      const initial: Record<number, string> = {};
      built.forEach((g, i) => {
        initial[i] = g.primary.id;
      });
      setSelections(initial);
      setViewState(built.length === 0 ? "empty" : "results");
    },
    onError: () => {
      setViewState("empty");
      toast({
        title: "Could not detect duplicates",
        description: "An error occurred while scanning for duplicates.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // ── Merge mutation ──────────────────────────────────────────────────────────

  const mergeMutation = useMutation({
    mutationFn: async () => {
      setMergeError(null);
      for (let i = 0; i < groups.length; i++) {
        const primaryId = selections[i];
        if (!primaryId) continue;
        const allTxns = [groups[i].primary, ...groups[i].duplicates];
        const duplicateIds = allTxns
          .filter((t) => t.id !== primaryId)
          .map((t) => t.id);
        await transactionMergesApi.merge({
          primary_transaction_id: primaryId,
          duplicate_transaction_ids: duplicateIds,
          merge_reason: "user_initiated",
        });
      }
    },
    onSuccess: () => {
      setViewState("success");
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      setMergeError(message);
    },
  });

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleOpen = () => {
    setViewState("loading");
    setGroups([]);
    setSelections({});
    setMergeError(null);
    detectMutation.mutate();
  };

  const handleSelectPrimary = (groupIndex: number, id: string) => {
    setSelections((prev) => ({ ...prev, [groupIndex]: id }));
  };

  const handleMerge = () => {
    if (!allGroupsHavePrimary(groups, selections)) return;
    setViewState("merging");
    mergeMutation.mutate();
  };

  const handleClose = () => {
    onClose();
    // Reset after animation completes
    setTimeout(() => {
      setViewState("loading");
      setGroups([]);
      setSelections({});
      setMergeError(null);
    }, 300);
  };

  const canMerge =
    viewState === "results" && allGroupsHavePrimary(groups, selections);

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      onOverlayClick={handleClose}
      size="xl"
      scrollBehavior="inside"
      // Trigger detection when modal opens
      onCloseComplete={() => {}}
    >
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Find Duplicate Transactions</ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          {/* Trigger detection on first open */}
          <OpenTrigger isOpen={isOpen} onOpen={handleOpen} />

          {viewState === "loading" && (
            <VStack py={12} spacing={4}>
              <Spinner size="lg" color="brand.500" />
              <Text color="text.secondary" fontSize="sm">
                Scanning for duplicate transactions…
              </Text>
            </VStack>
          )}

          {viewState === "empty" && (
            <VStack py={12} spacing={3}>
              <Text fontSize="2xl">✓</Text>
              <Text fontWeight="semibold">No duplicates detected</Text>
              <Text color="text.secondary" fontSize="sm" textAlign="center">
                Your transactions look clean — no potential duplicates were
                found.
              </Text>
            </VStack>
          )}

          {(viewState === "results" || viewState === "merging") && (
            <VStack spacing={4} align="stretch">
              <Text fontSize="sm" color="text.secondary">
                {groups.length} group{groups.length !== 1 ? "s" : ""} of
                potential duplicates found. Select which transaction to keep as
                the primary record in each group.
              </Text>

              {mergeError && (
                <Alert status="error" borderRadius="md">
                  <AlertIcon />
                  <AlertDescription fontSize="sm">{mergeError}</AlertDescription>
                </Alert>
              )}

              {groups.map((group, i) => (
                <DuplicateGroupCard
                  key={i}
                  group={group}
                  groupIndex={i}
                  selectedPrimaryId={selections[i] ?? ""}
                  onSelectPrimary={handleSelectPrimary}
                />
              ))}
            </VStack>
          )}

          {viewState === "success" && (
            <VStack py={12} spacing={3}>
              <Text fontSize="2xl">🎉</Text>
              <Text fontWeight="semibold">Merge complete</Text>
              <Text color="text.secondary" fontSize="sm" textAlign="center">
                {groups.length} duplicate group
                {groups.length !== 1 ? "s were" : " was"} merged successfully.
                Your transaction list has been refreshed.
              </Text>
            </VStack>
          )}
        </ModalBody>

        <Divider />
        <ModalFooter gap={2}>
          {viewState === "success" ? (
            <Button onClick={handleClose} colorScheme="brand">
              Done
            </Button>
          ) : (
            <>
              <Button variant="ghost" onClick={handleClose}>
                Cancel
              </Button>
              {(viewState === "results" || viewState === "merging") && (
                <Button
                  colorScheme="red"
                  onClick={handleMerge}
                  isDisabled={!canMerge || viewState === "merging"}
                  isLoading={viewState === "merging"}
                  loadingText="Merging…"
                >
                  Merge Duplicates
                </Button>
              )}
            </>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

// ── Helper: trigger detection exactly once when the modal opens ───────────────

/**
 * Tiny stateless helper that calls `onOpen` once whenever `isOpen` flips to
 * true.  Using a component (rather than a useEffect in the parent) keeps the
 * detection logic self-contained inside the modal tree.
 */
function OpenTrigger({
  isOpen,
  onOpen,
}: {
  isOpen: boolean;
  onOpen: () => void;
}) {
  const [prevOpen, setPrevOpen] = useState(false);
  if (isOpen && !prevOpen) {
    setPrevOpen(true);
    // Schedule for after render to avoid setState-during-render warning
    setTimeout(onOpen, 0);
  }
  if (!isOpen && prevOpen) {
    setPrevOpen(false);
  }
  return null;
}
