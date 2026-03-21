/**
 * Savings Goals page - manage all savings goals
 */

import { useState, useEffect } from "react";
import {
  Box,
  Button,
  ButtonGroup,
  Card,
  CardBody,
  Heading,
  HStack,
  Icon,
  Text,
  VStack,
  useDisclosure,
  useToast,
  Spinner,
  Center,
  Badge,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Tooltip,
  SimpleGrid,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  useColorModeValue,
} from "@chakra-ui/react";
import { AddIcon } from "@chakra-ui/icons";
import {
  FiLock,
  FiTarget,
  FiShield,
  FiHome,
  FiSun,
  FiCreditCard,
  type IconType,
} from "react-icons/fi";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DndContext, closestCenter, type DragEndEvent } from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { savingsGoalsApi } from "../api/savings-goals";
import { accountsApi } from "../api/accounts";
import type { SavingsGoal } from "../types/savings-goal";
import type { Account } from "../types/account";
import GoalCard from "../features/goals/components/GoalCard";
import GoalForm from "../features/goals/components/GoalForm";
import { useUserView } from "../contexts/UserViewContext";
import { EmptyState } from "../components/EmptyState";
import { useAuthStore } from "../features/auth/stores/authStore";
import HelpHint from "../components/HelpHint";
import { helpContent } from "../constants/helpContent";

// ---------------------------------------------------------------------------
// SortableGoalCard — wraps GoalCard with dnd-kit drag-and-drop support
// ---------------------------------------------------------------------------

interface SortableGoalCardProps {
  goal: SavingsGoal;
  onEdit: (goal: SavingsGoal) => void;
  method: "waterfall" | "proportional";
  canEdit?: boolean;
}

function SortableGoalCard({
  goal,
  onEdit,
  method,
  canEdit = true,
}: SortableGoalCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: goal.id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <GoalCard
        goal={goal}
        onEdit={onEdit}
        showFundButton
        canEdit={canEdit}
        dragHandleListeners={listeners as Record<string, unknown>}
        dragHandleAttributes={attributes as unknown as Record<string, unknown>}
        method={method}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// AccountGroup — collapsible accordion section for goals under one account
// ---------------------------------------------------------------------------

interface AccountGroupProps {
  accountName: string;
  goals: SavingsGoal[];
  onEdit: (goal: SavingsGoal) => void;
  canEdit?: boolean;
}

function AccountGroup({
  accountName,
  goals,
  onEdit,
  canEdit = true,
}: AccountGroupProps) {
  const accent = useColorModeValue("blue", "cyan");
  return (
    <AccordionItem
      border="1px solid"
      borderColor="border.default"
      borderRadius="md"
      overflow="hidden"
    >
      <AccordionButton
        bg="bg.subtle"
        _expanded={{ bg: "blue.50", _dark: { bg: "cyan.900" } }}
        py={3}
        px={4}
      >
        <HStack flex={1} textAlign="left" spacing={3}>
          <Text fontWeight="semibold" fontSize="md">
            {accountName}
          </Text>
          <Badge colorScheme={accent} size="sm">
            {goals.length} {goals.length === 1 ? "goal" : "goals"}
          </Badge>
        </HStack>
        <AccordionIcon />
      </AccordionButton>
      <AccordionPanel pb={4} pt={3} px={4}>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {goals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              onEdit={onEdit}
              showFundButton
              canEdit={canEdit}
            />
          ))}
        </SimpleGrid>
      </AccordionPanel>
    </AccordionItem>
  );
}

// ---------------------------------------------------------------------------
// SavingsGoalsPage
// ---------------------------------------------------------------------------

type ViewMode = "priority" | "account";

export default function SavingsGoalsPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedGoal, setSelectedGoal] = useState<SavingsGoal | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("priority");
  const {
    canWriteResource,
    isOtherUserView,
    isSelfView,
    selectedUserId,
    selectedMemberIds,
    matchesMemberFilter,
    isPartialMemberSelection,
  } = useUserView();
  const selectedIds = selectedMemberIds;
  const matchesFilter = matchesMemberFilter;
  const isPartialSelection = isPartialMemberSelection;
  const canEdit = canWriteResource("savings_goal");
  const queryClient = useQueryClient();
  const toast = useToast();

  // Blue in light mode (matches budgets), cyan in dark mode (better visibility)
  const accent = useColorModeValue("blue", "cyan");

  const currentUser = useAuthStore((s) => s.user);
  const onboardingGoal = localStorage.getItem("nest-egg-onboarding-goal") ?? "";

  // Allocation method — persisted in localStorage
  const [allocationMethod, setAllocationMethod] = useState<
    "waterfall" | "proportional"
  >(
    () =>
      (localStorage.getItem("savingsGoalAllocMethod") as
        | "waterfall"
        | "proportional") ?? "waterfall",
  );

  const handleMethodChange = (m: "waterfall" | "proportional") => {
    setAllocationMethod(m);
    localStorage.setItem("savingsGoalAllocMethod", m);
  };

  // Get all goals — scoped to selected household member when one is chosen
  const { data: goals = [], isLoading: goalsLoading } = useQuery({
    queryKey: ["goals", selectedUserId],
    queryFn: () =>
      savingsGoalsApi.getAll(
        selectedUserId ? { user_id: selectedUserId } : undefined,
      ),
  });

  // Get accounts for name lookup (shared cache — no extra network calls if already fetched)
  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => accountsApi.getAccounts(),
  });

  // Build account lookup map: id → Account
  const accountMap = new Map<string, Account>(accounts.map((a) => [a.id, a]));

  // Key built from auto-sync goals' id+account_id pairs
  const autoSyncKey = goals
    .filter(
      (g) => !g.is_completed && !g.is_funded && g.auto_sync && g.account_id,
    )
    .map((g) => `${g.id}:${g.account_id}`)
    .join(",");

  useEffect(() => {
    if (!autoSyncKey) return;
    savingsGoalsApi
      .autoSync(allocationMethod)
      .then(() => queryClient.invalidateQueries({ queryKey: ["goals"] }))
      .catch(() => {
        /* silently ignore — goals still display with last known values */
      });
  }, [autoSyncKey, allocationMethod]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleEdit = (goal: SavingsGoal) => {
    setSelectedGoal(goal);
    onOpen();
  };

  const handleCreate = () => {
    setSelectedGoal(null);
    onOpen();
  };

  const handleClose = () => {
    setSelectedGoal(null);
    onClose();
  };

  // Apply view-based and user filter
  const filteredGoals = (() => {
    // Self view: show goals you created + shared goals you're part of
    if (isSelfView && currentUser) {
      return goals.filter((g) => {
        if (g.user_id === currentUser.id) return true;
        if (g.is_shared && !g.shared_user_ids) return true;
        if (g.is_shared && g.shared_user_ids?.includes(currentUser.id))
          return true;
        if (!g.user_id) return true;
        return false;
      });
    }
    // Combined view with partial member selection
    if (isPartialSelection) {
      return goals.filter((g) => {
        if (matchesFilter(g.user_id)) return true;
        if (g.is_shared && !g.shared_user_ids) return true;
        if (g.is_shared && g.shared_user_ids?.some((id) => selectedIds.has(id)))
          return true;
        return false;
      });
    }
    return goals;
  })();

  const activeGoals = filteredGoals.filter(
    (g) => !g.is_completed && !g.is_funded,
  );
  const completedGoals = filteredGoals.filter(
    (g) => g.is_completed || g.is_funded,
  );
  // Use unfiltered goals so the toggle doesn't disappear when member filter is active
  const hasAutoSyncGoals = goals.some(
    (g) => !g.is_completed && !g.is_funded && g.auto_sync && g.account_id,
  );

  // Goal templates — hide each card once the matching goal exists
  const goalNames = goals.map((g) => g.name.toLowerCase());
  const hasEmergencyFundGoal = goalNames.some((n) => n.includes("emergency"));
  const hasVacationGoal = goalNames.some(
    (n) => n.includes("vacation") || n.includes("travel"),
  );
  const hasDownPaymentGoal = goalNames.some(
    (n) => n.includes("down payment") || n.includes("home"),
  );
  const hasDebtPayoffGoal = goalNames.some(
    (n) => n.includes("debt") || n.includes("payoff"),
  );

  type GoalTemplateKey =
    | "emergency_fund"
    | "vacation_fund"
    | "home_down_payment"
    | "debt_payoff_reserve";

  const createFromTemplateMutation = useMutation({
    mutationFn: (template: GoalTemplateKey) =>
      savingsGoalsApi.createFromTemplate(template),
    onSuccess: (goal) => {
      queryClient.invalidateQueries({ queryKey: ["goals"] });
      toast({
        title: `${goal.name} created`,
        description: `Target set to $${Number(goal.target_amount).toLocaleString()} — edit anytime to adjust.`,
        status: "success",
        duration: 5000,
        isClosable: true,
      });
    },
    onError: () => {
      toast({
        title: "Could not create goal",
        status: "error",
        duration: 3000,
      });
    },
  });

  const GOAL_TEMPLATES: {
    key: GoalTemplateKey;
    label: string;
    description: string;
    icon: IconType;
    hidden: boolean;
  }[] = [
    {
      key: "emergency_fund",
      label: "Emergency Fund",
      description:
        "6 months of expenses — auto-calculated from your spending history",
      icon: FiShield,
      hidden: hasEmergencyFundGoal,
    },
    {
      key: "vacation_fund",
      label: "Vacation Fund",
      description: "Save $4,000 over the next 12 months for your next trip",
      icon: FiSun,
      hidden: hasVacationGoal,
    },
    {
      key: "home_down_payment",
      label: "Home Down Payment",
      description:
        "20% down on a $300K home — adjust the target to your market",
      icon: FiHome,
      hidden: hasDownPaymentGoal,
    },
    {
      key: "debt_payoff_reserve",
      label: "Debt Payoff Reserve",
      description:
        "10% of your total debt balance set aside for extra payments",
      icon: FiCreditCard,
      hidden: hasDebtPayoffGoal,
    },
  ];

  const visibleTemplates = GOAL_TEMPLATES.filter((t) => !t.hidden);

  // Group active goals by account_id for the "By Account" view
  const goalsByAccount = (() => {
    const groups = new Map<string | null, SavingsGoal[]>();
    for (const goal of activeGoals) {
      const key = goal.account_id ?? null;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(goal);
    }
    return groups;
  })();

  // Sorted account entries (alphabetical by account name), unlinked always last
  const linkedAccountEntries = Array.from(goalsByAccount.entries())
    .filter(([id]) => id !== null)
    .sort(([aId], [bId]) => {
      const aName = accountMap.get(aId!)?.name ?? "";
      const bName = accountMap.get(bId!)?.name ?? "";
      return aName.localeCompare(bName);
    }) as [string, SavingsGoal[]][];

  const unlinkedGoals = goalsByAccount.get(null) ?? [];

  // Number of accordion sections to open by default (all of them)
  const defaultOpenIndices = Array.from(
    {
      length: linkedAccountEntries.length + (unlinkedGoals.length > 0 ? 1 : 0),
    },
    (_, i) => i,
  );

  // Drag-and-drop reorder (priority view only)
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = activeGoals.findIndex((g) => g.id === active.id);
    const newIndex = activeGoals.findIndex((g) => g.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const newIds = arrayMove(activeGoals, oldIndex, newIndex).map((g) => g.id);

    // Optimistic update
    queryClient.setQueryData<SavingsGoal[]>(["goals"], (old) => {
      if (!old) return old;
      const reordered = arrayMove(activeGoals, oldIndex, newIndex);
      const rest = old.filter((g) => g.is_completed || g.is_funded);
      return [...reordered, ...rest];
    });

    savingsGoalsApi.reorder(newIds).catch(() => {
      queryClient.invalidateQueries({ queryKey: ["goals"] });
    });
  };

  return (
    <Box p={8}>
      <VStack align="stretch" spacing={6}>
        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="lg">
              Savings Goals
              <HelpHint hint={helpContent.savingsGoals.emergencyFund} />
            </Heading>
            <Text color="text.secondary">
              Savings targets you're working toward — notifies you when you
              reach them
            </Text>
          </VStack>
          <Tooltip
            label={
              isPartialSelection && !isSelfView
                ? "Select 'All' members or your own view to create goals"
                : !canEdit
                  ? "Read-only: You can only create goals for your own data"
                  : ""
            }
            placement="top"
            isDisabled={canEdit && (!isPartialSelection || isSelfView)}
          >
            <Button
              leftIcon={
                canEdit && (!isPartialSelection || isSelfView) ? (
                  <AddIcon />
                ) : (
                  <FiLock />
                )
              }
              colorScheme={accent}
              onClick={handleCreate}
              isDisabled={!canEdit || (isPartialSelection && !isSelfView)}
            >
              New Goal
            </Button>
          </Tooltip>
        </HStack>

        {/* Controls row — view toggle + allocation method */}
        {!goalsLoading && goals.length > 0 && (
          <HStack spacing={6} flexWrap="wrap">
            {/* View mode toggle */}
            <HStack spacing={2}>
              <Text fontSize="sm" fontWeight="medium" color="text.secondary">
                View:
              </Text>
              <ButtonGroup size="sm" isAttached variant="outline">
                <Button
                  colorScheme={viewMode === "priority" ? accent : "gray"}
                  variant={viewMode === "priority" ? "solid" : "outline"}
                  onClick={() => setViewMode("priority")}
                >
                  Priority Order
                </Button>
                <Button
                  colorScheme={viewMode === "account" ? accent : "gray"}
                  variant={viewMode === "account" ? "solid" : "outline"}
                  onClick={() => setViewMode("account")}
                >
                  By Account
                </Button>
              </ButtonGroup>
            </HStack>

            {/* Allocation method — shown when auto-sync goals exist */}
            {hasAutoSyncGoals && (
              <HStack spacing={2}>
                <Text fontSize="sm" fontWeight="medium" color="text.secondary">
                  Balance allocation:
                </Text>
                <ButtonGroup size="sm" isAttached variant="outline">
                  <Button
                    colorScheme={
                      allocationMethod === "waterfall" ? accent : "gray"
                    }
                    variant={
                      allocationMethod === "waterfall" ? "solid" : "outline"
                    }
                    onClick={() => handleMethodChange("waterfall")}
                  >
                    Priority Waterfall
                  </Button>
                  <Button
                    colorScheme={
                      allocationMethod === "proportional" ? accent : "gray"
                    }
                    variant={
                      allocationMethod === "proportional" ? "solid" : "outline"
                    }
                    onClick={() => handleMethodChange("proportional")}
                  >
                    Proportional
                  </Button>
                </ButtonGroup>
                <Tooltip
                  label={
                    allocationMethod === "waterfall"
                      ? "Goal 1 claims its full target first, then Goal 2, and so on."
                      : "Balance is split proportionally based on each goal's target amount."
                  }
                  placement="right"
                >
                  <Text fontSize="xs" color="text.muted" cursor="help">
                    (?)
                  </Text>
                </Tooltip>
              </HStack>
            )}
          </HStack>
        )}

        {/* Loading state */}
        {goalsLoading && (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        )}

        {/* Empty state */}
        {!goalsLoading && goals.length === 0 && (
          <EmptyState
            icon={FiTarget}
            title={
              isPartialSelection && !isSelfView
                ? "No savings goals match the selected members"
                : isOtherUserView
                  ? "This user has no savings goals yet"
                  : "No savings goals yet"
            }
            description={
              onboardingGoal === "retirement"
                ? "You said you want to plan for retirement — start by building an emergency fund so unexpected costs don't derail your progress."
                : onboardingGoal === "investments"
                  ? "Goals work alongside your investments. Set a savings target to fund your next contribution or build a cash buffer."
                  : "Set savings goals to track progress toward vacations, emergency funds, down payments, and more."
            }
            actionLabel="Create Your First Goal"
            onAction={handleCreate}
            showAction={canEdit && (!isPartialSelection || isSelfView)}
          />
        )}

        {/* Goal templates quick-start */}
        {!goalsLoading && canEdit && visibleTemplates.length > 0 && (
          <VStack align="stretch" spacing={3}>
            <HStack>
              <Icon as={FiTarget} color="brand.500" />
              <Text fontWeight="semibold" fontSize="sm">
                Quick-start a goal
              </Text>
              <Text fontSize="sm" color="text.muted">
                — one click to set up a common savings goal
              </Text>
            </HStack>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 2 }} spacing={3}>
              {visibleTemplates.map((tmpl) => (
                <Card
                  key={tmpl.key}
                  variant="outline"
                  size="sm"
                  _hover={{ borderColor: "brand.300", shadow: "sm" }}
                  transition="all 0.15s"
                >
                  <CardBody>
                    <HStack justify="space-between" flexWrap="wrap" spacing={3}>
                      <HStack spacing={3} flex={1} minW={0}>
                        <Icon
                          as={tmpl.icon}
                          boxSize={5}
                          color="brand.500"
                          flexShrink={0}
                        />
                        <VStack align="start" spacing={0} minW={0}>
                          <Text fontWeight="semibold" fontSize="sm">
                            {tmpl.label}
                          </Text>
                          <Text fontSize="xs" color="text.muted" noOfLines={2}>
                            {tmpl.description}
                          </Text>
                        </VStack>
                      </HStack>
                      <Button
                        colorScheme={accent}
                        size="sm"
                        variant="outline"
                        flexShrink={0}
                        onClick={() =>
                          createFromTemplateMutation.mutate(tmpl.key)
                        }
                        isLoading={
                          createFromTemplateMutation.isPending &&
                          createFromTemplateMutation.variables === tmpl.key
                        }
                      >
                        Create
                      </Button>
                    </HStack>
                  </CardBody>
                </Card>
              ))}
            </SimpleGrid>
          </VStack>
        )}

        {/* Goals tabs */}
        {!goalsLoading && goals.length > 0 && (
          <Tabs variant="enclosed" colorScheme="brand">
            <TabList>
              <Tab>
                Active Goals{" "}
                <Badge ml={2} colorScheme={accent}>
                  {activeGoals.length}
                </Badge>
              </Tab>
              <Tab>
                Completed Goals{" "}
                <Badge ml={2} colorScheme="green">
                  {completedGoals.length}
                </Badge>
              </Tab>
            </TabList>

            <TabPanels>
              {/* Active goals */}
              <TabPanel>
                {activeGoals.length === 0 ? (
                  <Center py={8}>
                    <Text color="text.muted">No active goals</Text>
                  </Center>
                ) : viewMode === "priority" ? (
                  /* Priority order — DnD sortable vertical list */
                  <DndContext
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                  >
                    <SortableContext
                      items={activeGoals.map((g) => g.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      <VStack align="stretch" spacing={4}>
                        {activeGoals.map((goal) => (
                          <SortableGoalCard
                            key={goal.id}
                            goal={goal}
                            onEdit={handleEdit}
                            method={allocationMethod}
                            canEdit={canEdit}
                          />
                        ))}
                      </VStack>
                    </SortableContext>
                  </DndContext>
                ) : (
                  /* By Account — collapsible accordion groups */
                  <Accordion allowMultiple defaultIndex={defaultOpenIndices}>
                    <VStack align="stretch" spacing={3}>
                      {linkedAccountEntries.map(([accountId, groupGoals]) => (
                        <AccountGroup
                          key={accountId}
                          accountName={
                            accountMap.get(accountId)?.name ?? "Unknown Account"
                          }
                          goals={groupGoals}
                          onEdit={handleEdit}
                          canEdit={canEdit}
                        />
                      ))}
                      {unlinkedGoals.length > 0 && (
                        <AccountGroup
                          key="unlinked"
                          accountName="Not linked to an account"
                          goals={unlinkedGoals}
                          onEdit={handleEdit}
                          canEdit={canEdit}
                        />
                      )}
                    </VStack>
                  </Accordion>
                )}
              </TabPanel>

              {/* Completed goals — static grid */}
              <TabPanel>
                {completedGoals.length === 0 ? (
                  <Center py={8}>
                    <Text color="text.muted">No completed goals yet</Text>
                  </Center>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                    {completedGoals.map((goal) => (
                      <GoalCard
                        key={goal.id}
                        goal={goal}
                        onEdit={handleEdit}
                        canEdit={canEdit}
                      />
                    ))}
                  </SimpleGrid>
                )}
              </TabPanel>
            </TabPanels>
          </Tabs>
        )}
      </VStack>

      {/* Goal form modal — key forces remount so defaultValues reset on each open */}
      <GoalForm
        key={selectedGoal?.id ?? "new"}
        isOpen={isOpen}
        onClose={handleClose}
        goal={selectedGoal}
      />
    </Box>
  );
}
