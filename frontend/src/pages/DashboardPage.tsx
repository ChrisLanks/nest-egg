/**
 * Dashboard page — thin shell that delegates to the customizable widget grid.
 *
 * All chart/data logic lives in individual widget components under
 * src/features/dashboard/widgets/. Layout persistence is handled by
 * the useWidgetLayout hook.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Container,
  Heading,
  HStack,
  Icon,
  Progress,
  Text,
  Tooltip,
  useDisclosure,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { AddIcon, EditIcon, RepeatIcon } from "@chakra-ui/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type ElementType, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiLink, FiDollarSign, FiBarChart2, FiTarget } from "react-icons/fi";
import type { SavingsGoal } from "../types/savings-goal";
import { useAuthStore } from "../features/auth/stores/authStore";
import { DashboardGrid } from "../features/dashboard/DashboardGrid";
import { AddWidgetDrawer } from "../features/dashboard/AddWidgetDrawer";
import { useWidgetLayout } from "../features/dashboard/useWidgetLayout";
import { WIDGET_REGISTRY } from "../features/dashboard/widgetRegistry";
import type { LayoutItem } from "../features/dashboard/types";
import api from "../services/api";
import { AddAccountModal } from "../features/accounts/components/AddAccountModal";
import { GoalContextBanner } from "../features/dashboard/GoalContextBanner";

const GOAL_STEPS: Record<
  string,
  { label: string; hint: string; icon: ElementType; action: boolean; path?: string }[]
> = {
  spending: [
    {
      icon: FiLink,
      label: "Connect a bank account",
      hint: "We import your transactions automatically — nothing to enter by hand.",
      action: true,
    },
    {
      icon: FiDollarSign,
      label: "Set your first budget",
      hint: "Pick one spending category and give it a monthly limit.",
      action: false,
      path: "/budgets",
    },
    {
      icon: FiBarChart2,
      label: "Check your spending breakdown",
      hint: "See exactly where your money goes each month.",
      action: false,
      path: "/cash-flow",
    },
  ],
  retirement: [
    {
      icon: FiLink,
      label: "Connect or add an account",
      hint: "Link your 401(k), IRA, or bank — or add balances manually.",
      action: true,
    },
    {
      icon: FiDollarSign,
      label: "Set your birthdate in Preferences",
      hint: "Required for accurate retirement projections.",
      action: false,
      path: "/preferences",
    },
    {
      icon: FiBarChart2,
      label: "Create your first retirement scenario",
      hint: "See when you could retire and what you need to get there.",
      action: false,
      path: "/retirement",
    },
  ],
  investments: [
    {
      icon: FiLink,
      label: "Connect your investment account",
      hint: "Link your 401(k), IRA, or brokerage to see your full portfolio.",
      action: true,
    },
    {
      icon: FiDollarSign,
      label: "Review your holdings",
      hint: "See what you're invested in and your expense ratios.",
      action: false,
      path: "/investments",
    },
    {
      icon: FiBarChart2,
      label: "Check your net worth",
      hint: "Your investments plus all other assets, minus debts.",
      action: false,
      path: "/overview",
    },
  ],
};

const DEFAULT_STEPS = GOAL_STEPS.spending;

// ── Life Goals mini-widget ─────────────────────────────────────────────────

const GoalsWidget = ({ goals, onNavigate }: { goals: SavingsGoal[]; onNavigate: (path: string) => void }) => {
  const active = goals.filter((g) => !g.is_completed && !g.is_funded);

  if (goals.length === 0) {
    return (
      <Card mb={6} variant="outline" borderStyle="dashed">
        <CardBody py={3} px={4}>
          <HStack justify="space-between" align="center">
            <HStack spacing={3}>
              <Icon as={FiTarget} color="text.muted" boxSize={5} />
              <Text fontSize="sm" color="text.secondary">No goals yet — set one to track your progress.</Text>
            </HStack>
            <Button
              size="sm"
              variant="ghost"
              colorScheme="brand"
              onClick={() => onNavigate("/goals")}
              flexShrink={0}
            >
              Set your first goal →
            </Button>
          </HStack>
        </CardBody>
      </Card>
    );
  }

  const totalCurrent = active.reduce((sum, g) => sum + g.current_amount, 0);
  const totalTarget = active.reduce((sum, g) => sum + g.target_amount, 0);
  const overallPct = totalTarget > 0 ? Math.round((totalCurrent / totalTarget) * 100) : 0;

  return (
    <Card mb={6}>
      <CardBody py={3} px={4}>
        <HStack justify="space-between" align="center" mb={active.length > 0 ? 2 : 0}>
          <HStack spacing={2}>
            <Icon as={FiTarget} color="brand.500" boxSize={4} />
            <Text fontSize="sm" fontWeight="semibold">Life Goals</Text>
            <Badge colorScheme="brand" fontSize="xs">{active.length} active</Badge>
          </HStack>
          <Button
            size="sm"
            variant="ghost"
            colorScheme="brand"
            onClick={() => onNavigate("/goals")}
            flexShrink={0}
          >
            View Goals →
          </Button>
        </HStack>
        {active.length > 0 && totalTarget > 0 && (
          <HStack spacing={3} align="center">
            <Progress
              value={overallPct}
              colorScheme="brand"
              size="sm"
              borderRadius="full"
              flex={1}
            />
            <Text fontSize="xs" color="text.secondary" flexShrink={0}>{overallPct}% overall</Text>
          </HStack>
        )}
      </CardBody>
    </Card>
  );
};

const GettingStartedEmptyState = ({
  onConnectBank,
  goal,
  onNavigate,
}: {
  onConnectBank: () => void;
  goal: string | null;
  onNavigate: (path: string) => void;
}) => {
  const steps = (goal && GOAL_STEPS[goal]) || DEFAULT_STEPS;
  const headings: Record<string, string> = {
    spending: "Your financial picture starts here",
    retirement: "Let's plan your retirement",
    investments: "Let's look at your investments",
  };
  const subtext: Record<string, string> = {
    spending:
      "Connect an account and your transactions import automatically — then you'll see spending by category, net worth, and where your money goes.",
    retirement:
      "Connect an account and set up your first scenario to see when you could retire — and what it takes to get there.",
    investments:
      "Connect your investment accounts to see your portfolio, expense ratios, and how your money is allocated.",
  };

  return (
    <Box
      p={8}
      borderRadius="xl"
      bg="bg.surface"
      boxShadow="sm"
      border="1px dashed"
      borderColor="border.default"
      textAlign="center"
    >
      <VStack spacing={6} maxW="md" mx="auto">
        <Icon as={FiBarChart2} boxSize={12} color="brand.500" />
        <VStack spacing={2}>
          <Heading size="md">
            {headings[goal ?? ""] ?? headings.spending}
          </Heading>
          <Text color="text.secondary">
            {subtext[goal ?? ""] ?? subtext.spending}
          </Text>
        </VStack>
        <VStack spacing={3} w="full">
          {steps.map((step, i) => (
            <HStack
              key={step.label}
              w="full"
              p={3}
              bg="bg.subtle"
              borderRadius="md"
              spacing={3}
              align="start"
              cursor={step.path ? "pointer" : "default"}
              onClick={step.path ? () => onNavigate(step.path!) : undefined}
              _hover={step.path ? { bg: "bg.hover", borderColor: "brand.200" } : undefined}
              border="1px solid transparent"
              transition="all 0.15s"
            >
              <Icon
                as={step.icon}
                color={step.action ? "brand.500" : step.path ? "brand.400" : "text.muted"}
                boxSize={5}
                mt="2px"
                flexShrink={0}
              />
              <VStack align="start" spacing={0} flex={1}>
                <Text
                  fontSize="sm"
                  fontWeight="medium"
                  color={step.action ? "text.primary" : step.path ? "text.primary" : "text.muted"}
                  textAlign="left"
                >
                  {i + 1}. {step.label}
                </Text>
                <Text fontSize="xs" color="text.secondary" textAlign="left">
                  {step.hint}
                </Text>
              </VStack>
              {step.action && (
                <Badge colorScheme="brand" fontSize="xs" flexShrink={0}>
                  Start here
                </Badge>
              )}
              {step.path && !step.action && (
                <Badge colorScheme="gray" fontSize="xs" flexShrink={0} variant="outline">
                  Go →
                </Badge>
              )}
            </HStack>
          ))}
        </VStack>
        <Button
          colorScheme="brand"
          size="lg"
          leftIcon={<FiLink />}
          onClick={onConnectBank}
        >
          {goal === "investments"
            ? "Connect an Investment Account"
            : "Connect a Bank Account"}
        </Button>
        <Text fontSize="xs" color="text.muted">
          Prefer to enter accounts manually? You can do that from the{" "}
          <Text as="span" fontWeight="medium">
            Accounts
          </Text>{" "}
          page in the top navigation.
        </Text>
      </VStack>
    </Box>
  );
};

export const DashboardPage = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const onboardingGoal =
    localStorage.getItem("nest-egg-onboarding-goal") ||
    user?.onboarding_goal ||
    null;
  const queryClient = useQueryClient();
  const toast = useToast();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const {
    layout,
    isEditing,
    isSaving,
    startEditing,
    saveLayout,
    cancelEditing,
    setPendingLayout,
  } = useWidgetLayout();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isAddAccountOpen,
    onOpen: onAddAccountOpen,
    onClose: onAddAccountClose,
  } = useDisclosure();

  const { data: accounts, isLoading: accountsLoading, isError: accountsError } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const res = await api.get("/accounts");
      return res.data as Array<{ id: string }>;
    },
    staleTime: 30_000,
  });

  const { data: goals } = useQuery<SavingsGoal[]>({
    queryKey: ["savings-goals-dashboard"],
    queryFn: () => api.get("/savings-goals/").then((r) => r.data),
    staleTime: 60_000,
  });
  const handleAddWidget = (widgetId: string) => {
    const def = WIDGET_REGISTRY[widgetId];
    if (!def) return;
    const newItem: LayoutItem = { id: widgetId, span: def.defaultSpan };
    setPendingLayout([...layout, newItem]);
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      // Invalidate all dashboard-related queries to force a fresh fetch on every widget
      await queryClient.invalidateQueries({ predicate: () => true });
      toast({
        title: "Dashboard refreshed",
        status: "success",
        duration: 2000,
        isClosable: true,
        position: "bottom-right",
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <Container maxW="container.xl" py={8}>
      <HStack justify="space-between" mb={8} align="start">
        <Box>
          <Heading size="lg">
            {(user?.login_count ?? 0) <= 1 ? "Welcome" : "Welcome back"},{" "}
            {user?.display_name ||
              user?.first_name ||
              user?.email?.split("@")[0] ||
              "User"}
            !
          </Heading>
          <Text color="text.secondary" mt={1}>
            {onboardingGoal === "retirement"
              ? "Here's where your retirement stands"
              : onboardingGoal === "investments"
                ? "Here's your investment overview"
                : onboardingGoal === "spending"
                  ? "Here's where your money is going"
                  : "Here's your financial overview"}
          </Text>
        </Box>

        {!isEditing ? (
          <HStack flexShrink={0} spacing={2}>
            <Tooltip
              label="Get the latest data from all your accounts right now"
              hasArrow
            >
              <Button
                leftIcon={<RepeatIcon />}
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                isLoading={isRefreshing}
                loadingText="Refreshing…"
              >
                Refresh
              </Button>
            </Tooltip>
            <Button
              leftIcon={<EditIcon />}
              variant="ghost"
              size="sm"
              onClick={startEditing}
            >
              Customize
            </Button>
          </HStack>
        ) : (
          <HStack flexShrink={0}>
            <Button
              leftIcon={<AddIcon />}
              variant="outline"
              colorScheme="brand"
              size="sm"
              onClick={onOpen}
              isDisabled={isSaving}
            >
              Add Widget
            </Button>
            <Button
              colorScheme="brand"
              size="sm"
              onClick={saveLayout}
              isLoading={isSaving}
            >
              Done
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={cancelEditing}
              isDisabled={isSaving}
            >
              Cancel
            </Button>
          </HStack>
        )}
      </HStack>

      <GoalContextBanner />

      {goals !== undefined && (
        <GoalsWidget goals={goals} onNavigate={navigate} />
      )}

      {accountsError && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          Could not load account data. Some widgets may be unavailable — please refresh the page.
        </Alert>
      )}

      {!accountsLoading && !accountsError && accounts !== undefined && accounts.length === 0 && (
        <GettingStartedEmptyState onConnectBank={onAddAccountOpen} goal={onboardingGoal} onNavigate={navigate} />
      )}

      {(accountsError || (!accountsLoading && accounts !== undefined && accounts.length > 0)) && (
        <DashboardGrid
          layout={layout}
          isEditing={isEditing}
          onLayoutChange={setPendingLayout}
          onAddWidget={onOpen}
        />
      )}

      <AddWidgetDrawer
        isOpen={isOpen}
        onClose={onClose}
        currentLayout={layout}
        onAdd={handleAddWidget}
      />

      <AddAccountModal isOpen={isAddAccountOpen} onClose={onAddAccountClose} />
    </Container>
  );
};
