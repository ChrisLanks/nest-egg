/**
 * Budgets page - manage all budgets
 */

import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Container,
  Heading,
  HStack,
  SimpleGrid,
  Text,
  VStack,
  useDisclosure,
  Spinner,
  Center,
  Badge,
  Tooltip,
  ButtonGroup,
} from "@chakra-ui/react";
import { AddIcon } from "@chakra-ui/icons";
import { FiLock, FiDollarSign } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { budgetsApi } from "../api/budgets";
import type { Budget, BudgetSuggestion } from "../types/budget";
import { BudgetPeriod } from "../types/budget";
import type { BudgetCreate } from "../types/budget";
import BudgetCard from "../features/budgets/components/BudgetCard";
import BudgetForm from "../features/budgets/components/BudgetForm";
import BudgetSuggestions from "../features/budgets/components/BudgetSuggestions";
import { useUserView } from "../contexts/UserViewContext";
import { EmptyState } from "../components/EmptyState";
import { useAuthStore } from "../features/auth/stores/authStore";
import HelpHint from "../components/HelpHint";
import { helpContent } from "../constants/helpContent";

type FilterTab = "all" | "category" | "label";

export default function BudgetsPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedBudget, setSelectedBudget] = useState<Budget | null>(null);
  const [prefillValues, setPrefillValues] =
    useState<Partial<BudgetCreate> | null>(null);
  const [prefillProviderCategoryName, setPrefillProviderCategoryName] =
    useState<string | null>(null);
  const [filterTab, setFilterTab] = useState<FilterTab>("all");
  const {
    canWriteResource,
    isOtherUserView,
    isSelfView,
    selectedUserId,
    selectedMemberIds,
    matchesMemberFilter,
    isPartialMemberSelection,
  } = useUserView();
  const canEdit = canWriteResource("budget");

  const selectedIds = selectedMemberIds;
  const matchesFilter = matchesMemberFilter;
  const isPartialSelection = isPartialMemberSelection;
  const currentUser = useAuthStore((s) => s.user);

  const onboardingGoal = localStorage.getItem("nest-egg-onboarding-goal") ?? "";

  // Get all budgets
  const { data: budgets = [], isLoading, isError } = useQuery({
    queryKey: ["budgets", selectedUserId],
    queryFn: () =>
      budgetsApi.getAll(
        selectedUserId ? { user_id: selectedUserId } : undefined,
      ),
  });

  const handleEdit = (budget: Budget) => {
    setSelectedBudget(budget);
    onOpen();
  };

  const handleCreate = () => {
    setSelectedBudget(null);
    // Pre-fill scope defaults based on the current view context
    const viewDefaults: Partial<BudgetCreate> = {};
    if (!isSelfView && !selectedUserId) {
      // Combined / all-members view → default to shared with everyone
      viewDefaults.is_shared = true;
      viewDefaults.shared_user_ids = null;
    } else if (selectedUserId && isOtherUserView) {
      // Viewing a specific other member → personal budget for that member
      viewDefaults.is_shared = false;
    }
    setPrefillValues(viewDefaults);
    setPrefillProviderCategoryName(null);
    onOpen();
  };

  const handleAcceptSuggestion = (suggestion: BudgetSuggestion) => {
    setSelectedBudget(null);
    // Inherit scope defaults from current view, then layer suggestion specifics
    const viewDefaults: Partial<BudgetCreate> = {};
    if (!isSelfView && !selectedUserId) {
      viewDefaults.is_shared = true;
      viewDefaults.shared_user_ids = null;
    }
    setPrefillValues({
      ...viewDefaults,
      name: suggestion.category_name,
      amount: suggestion.suggested_amount,
      period: suggestion.suggested_period as BudgetPeriod,
      category_id: suggestion.category_id ?? undefined,
      start_date: new Date().toISOString().split("T")[0],
    });
    // If the suggestion is based on a provider category (no UUID), pass the raw
    // category_primary value so the form can find the exact match in allCategories.
    // category_primary_raw is the lowercased DB value; fall back to category_name.
    setPrefillProviderCategoryName(
      !suggestion.category_id
        ? (suggestion.category_primary_raw ?? suggestion.category_name)
        : null,
    );
    onOpen();
  };

  const handleClose = () => {
    setSelectedBudget(null);
    setPrefillValues(null);
    setPrefillProviderCategoryName(null);
    onClose();
  };

  // Apply view-based and user filter
  const filterByUser = (list: Budget[]) => {
    // Self view: show budgets you created + shared budgets you're part of
    if (isSelfView && currentUser) {
      return list.filter((b) => {
        if (b.user_id === currentUser.id) return true;
        if (b.is_shared && !b.shared_user_ids) return true;
        if (b.is_shared && b.shared_user_ids?.includes(currentUser.id))
          return true;
        if (!b.user_id) return true;
        return false;
      });
    }
    // Combined view with partial member selection
    if (isPartialSelection) {
      return list.filter((b) => {
        if (matchesFilter(b.user_id)) return true;
        if (b.is_shared && !b.shared_user_ids) return true;
        if (b.is_shared && b.shared_user_ids?.some((id) => selectedIds.has(id)))
          return true;
        return false;
      });
    }
    return list;
  };

  // Apply filter tab
  const filterBudgets = (list: Budget[]) => {
    let filtered = filterByUser(list);
    if (filterTab === "category")
      filtered = filtered.filter((b) => !!b.category_id);
    if (filterTab === "label") filtered = filtered.filter((b) => !!b.label_id);
    return filtered;
  };

  const activeBudgets = filterBudgets(budgets.filter((b) => b.is_active));
  const inactiveBudgets = filterBudgets(budgets.filter((b) => !b.is_active));

  // Count for filter badges
  const categoryCount = budgets.filter((b) => !!b.category_id).length;
  const labelCount = budgets.filter((b) => !!b.label_id).length;

  const filteredEmpty =
    activeBudgets.length === 0 && inactiveBudgets.length === 0;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack align="stretch" spacing={6}>
        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="lg">
              Budgets
              <HelpHint hint={helpContent.budgets.period} />
            </Heading>
            <Text color="text.secondary">
              Monthly spending limits by category — alerts you before you
              overspend
            </Text>
          </VStack>
          <Tooltip
            label={
              isPartialSelection && !isSelfView
                ? "Select 'All' members or your own view to create budgets"
                : !canEdit
                  ? "Read-only: You can only create budgets for your own data"
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
              colorScheme="blue"
              onClick={handleCreate}
              isDisabled={!canEdit || (isPartialSelection && !isSelfView)}
            >
              New Budget
            </Button>
          </Tooltip>
        </HStack>

        {/* Filter row */}
        {!isLoading && budgets.length > 0 && (
          <HStack spacing={6} flexWrap="wrap">
            {/* Type filter */}
            <HStack spacing={2}>
              <Text fontSize="sm" fontWeight="medium" color="text.secondary">
                Filter:
              </Text>
              <ButtonGroup size="sm" isAttached variant="outline">
                <Button
                  colorScheme={filterTab === "all" ? "blue" : "gray"}
                  variant={filterTab === "all" ? "solid" : "outline"}
                  onClick={() => setFilterTab("all")}
                >
                  All{" "}
                  <Badge
                    ml={1}
                    colorScheme={filterTab === "all" ? "blue" : "gray"}
                  >
                    {budgets.length}
                  </Badge>
                </Button>
                <Button
                  colorScheme={filterTab === "category" ? "blue" : "gray"}
                  variant={filterTab === "category" ? "solid" : "outline"}
                  onClick={() => setFilterTab("category")}
                >
                  By Category{" "}
                  <Badge
                    ml={1}
                    colorScheme={filterTab === "category" ? "blue" : "gray"}
                  >
                    {categoryCount}
                  </Badge>
                </Button>
                <Button
                  colorScheme={filterTab === "label" ? "blue" : "gray"}
                  variant={filterTab === "label" ? "solid" : "outline"}
                  onClick={() => setFilterTab("label")}
                >
                  By Label{" "}
                  <Badge
                    ml={1}
                    colorScheme={filterTab === "label" ? "blue" : "gray"}
                  >
                    {labelCount}
                  </Badge>
                </Button>
              </ButtonGroup>
            </HStack>
          </HStack>
        )}

        {/* Loading state */}
        {isLoading && (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        )}

        {/* Error state */}
        {isError && !isLoading && (
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            Unable to load budgets. Please try again.
          </Alert>
        )}

        {/* Empty state — no budgets at all */}
        {!isLoading && budgets.length === 0 && (
          <>
            <EmptyState
              icon={FiDollarSign}
              title={
                isPartialSelection && !isSelfView
                  ? "No budgets match the selected members"
                  : isOtherUserView
                    ? "This user has no budgets yet"
                    : "No budgets yet"
              }
              description={
                onboardingGoal === "spending"
                  ? "You said you want to track spending — a budget is the best place to start. Pick a category below and set a monthly limit."
                  : onboardingGoal === "retirement"
                    ? "Budgets help you free up money to save for retirement. Start with your biggest spending category."
                    : "Create budgets to track spending by category and stay on top of your financial goals."
              }
              actionLabel="Create Your First Budget"
              onAction={handleCreate}
              showAction={canEdit && (!isPartialSelection || isSelfView)}
            />
            {canEdit && (isSelfView || !selectedUserId) && (
              <BudgetSuggestions onAccept={handleAcceptSuggestion} userId={selectedUserId} />
            )}
          </>
        )}

        {/* Empty state — filter returns nothing */}
        {!isLoading && budgets.length > 0 && filteredEmpty && (
          <Center py={8}>
            <Text color="text.muted">
              No budgets match the selected filter.
            </Text>
          </Center>
        )}

        {/* Active budgets */}
        {!isLoading && activeBudgets.length > 0 && (
          <VStack align="stretch" spacing={4}>
            <Heading size="md">
              Active Budgets{" "}
              <Badge colorScheme="green" ml={2}>
                {activeBudgets.length}
              </Badge>
            </Heading>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
              {activeBudgets.map((budget) => (
                <BudgetCard
                  key={budget.id}
                  budget={budget}
                  onEdit={handleEdit}
                  canEdit={canEdit}
                />
              ))}
            </SimpleGrid>
          </VStack>
        )}

        {/* Suggestions when user has some but few budgets */}
        {!isLoading &&
          budgets.length > 0 &&
          budgets.length <= 3 &&
          canEdit &&
          (isSelfView || !selectedUserId) && (
            <BudgetSuggestions onAccept={handleAcceptSuggestion} userId={selectedUserId} />
          )}

        {/* Inactive budgets */}
        {!isLoading && inactiveBudgets.length > 0 && (
          <VStack align="stretch" spacing={4}>
            <Heading size="md">
              Inactive Budgets{" "}
              <Badge colorScheme="gray" ml={2}>
                {inactiveBudgets.length}
              </Badge>
            </Heading>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
              {inactiveBudgets.map((budget) => (
                <BudgetCard
                  key={budget.id}
                  budget={budget}
                  onEdit={handleEdit}
                  canEdit={canEdit}
                />
              ))}
            </SimpleGrid>
          </VStack>
        )}
      </VStack>

      {/* Budget form modal — key forces remount so defaultValues reset on each open */}
      <BudgetForm
        key={selectedBudget?.id ?? prefillValues?.name ?? prefillProviderCategoryName ?? "new"}
        isOpen={isOpen}
        onClose={handleClose}
        budget={selectedBudget}
        initialValues={prefillValues}
        initialProviderCategoryName={prefillProviderCategoryName}
      />
    </Container>
  );
}
