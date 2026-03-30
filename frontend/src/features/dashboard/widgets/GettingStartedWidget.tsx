import React, { memo, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
  HStack,
  Icon,
  IconButton,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { FiCheckCircle, FiCircle, FiArrowRight } from "react-icons/fi";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import api from "../../../services/api";
import { useAuthStore } from "../../auth/stores/authStore";

const DISMISSED_KEY = "nest-egg-getting-started-dismissed";
const NET_WORTH_VIEWED_KEY = "nest-egg-net-worth-viewed";

interface StepProps {
  label: string;
  hint: string;
  to: string;
  done: boolean;
}

const Step: React.FC<StepProps> = ({ label, hint, to, done }) => {
  const navigate = useNavigate();

  return (
    <HStack spacing={3} w="100%" align="start">
      <Icon
        as={done ? FiCheckCircle : FiCircle}
        color={done ? "green.500" : "gray.400"}
        boxSize={5}
        flexShrink={0}
        mt="2px"
      />
      <VStack align="start" spacing={0} flex={1}>
        <Text
          as={RouterLink}
          to={to}
          fontSize="sm"
          fontWeight="medium"
          color={done ? "text.muted" : "inherit"}
          textDecoration={done ? "line-through" : "none"}
          _hover={{ textDecoration: "underline" }}
        >
          {label}
        </Text>
        {!done && (
          <Text fontSize="xs" color="text.muted">
            {hint}
          </Text>
        )}
      </VStack>
      {!done && (
        <Button
          variant="link"
          size="xs"
          colorScheme="brand"
          flexShrink={0}
          onClick={() => navigate(to)}
        >
          Open →
        </Button>
      )}
    </HStack>
  );
};

const WHAT_NEXT_DISMISSED_KEY = "nest-egg-what-next-dismissed";
const WHAT_NEXT_HIDDEN_ITEMS_KEY = "nest-egg-what-next-hidden";

const WHAT_NEXT_ITEMS: Record<
  string,
  { label: string; desc: string; path: string }[]
> = {
  spending: [
    {
      label: "See your spending trends",
      desc: "How has your spending changed month to month?",
      path: "/cash-flow",
    },
    {
      label: "Set up recurring bill tracking",
      desc: "Auto-detect subscriptions and upcoming bills.",
      path: "/bills",
    },
    {
      label: "Review your budget progress",
      desc: "Are you staying within your limits this month?",
      path: "/budgets",
    },
  ],
  retirement: [
    {
      label: "Check your retirement outlook",
      desc: "Are you on track to retire when you want?",
      path: "/retirement",
    },
    {
      label: "Review your investments",
      desc: "What are your fees? How is your money allocated?",
      path: "/investments",
    },
    {
      label: "See your net worth over time",
      desc: "Track the number that matters most.",
      path: "/net-worth-timeline",
    },
  ],
  investments: [
    {
      label: "Review your investments",
      desc: "What are your fees? How is your money split?",
      path: "/investments",
    },
    {
      label: "Check your retirement outlook",
      desc: "Are you on track to retire when you want?",
      path: "/retirement",
    },
    {
      label: "See your net worth over time",
      desc: "Track total assets minus debts over time.",
      path: "/net-worth-timeline",
    },
  ],
  default: [
    {
      label: "See your spending trends",
      desc: "How has your spending changed month to month?",
      path: "/cash-flow",
    },
    {
      label: "Check your retirement outlook",
      desc: "Are you on track to retire when you want?",
      path: "/retirement",
    },
    {
      label: "Review your investments",
      desc: "What are your fees? How is your money split?",
      path: "/investments",
    },
  ],
};

const WhatNextCard: React.FC = () => {
  const [dismissed, setDismissed] = useState<boolean>(
    () => localStorage.getItem(WHAT_NEXT_DISMISSED_KEY) === "true",
  );
  const [hiddenItems, setHiddenItems] = useState<Set<string>>(
    () =>
      new Set(
        JSON.parse(
          localStorage.getItem(WHAT_NEXT_HIDDEN_ITEMS_KEY) || "[]",
        ) as string[],
      ),
  );
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  if (dismissed) return null;

  const goal =
    localStorage.getItem("nest-egg-onboarding-goal") ||
    user?.onboarding_goal ||
    "default";
  const allItems = WHAT_NEXT_ITEMS[goal] ?? WHAT_NEXT_ITEMS.default;
  const visibleItems = allItems.filter((item) => !hiddenItems.has(item.label));

  const handleHideItem = (label: string) => {
    const next = new Set(hiddenItems).add(label);
    setHiddenItems(next);
    localStorage.setItem(
      WHAT_NEXT_HIDDEN_ITEMS_KEY,
      JSON.stringify([...next]),
    );
  };

  // Auto-dismiss the card when all items have been hidden
  if (visibleItems.length === 0) {
    localStorage.setItem(WHAT_NEXT_DISMISSED_KEY, "true");
    return null;
  }

  return (
    <Card h="100%" borderColor="brand.200" borderWidth="1px">
      <CardHeader pb={2}>
        <HStack justify="space-between" align="center">
          <Heading size="md">You&apos;re set up!</Heading>
          <IconButton
            aria-label="Dismiss"
            icon={
              <Text fontSize="lg" lineHeight={1}>
                ×
              </Text>
            }
            variant="ghost"
            size="sm"
            onClick={() => {
              localStorage.setItem(WHAT_NEXT_DISMISSED_KEY, "true");
              setDismissed(true);
            }}
          />
        </HStack>
      </CardHeader>
      <CardBody pt={2}>
        <VStack align="stretch" spacing={3}>
          <Text fontSize="sm" color="text.secondary">
            The basics are covered. Here are a few things worth exploring next:
          </Text>
          <VStack align="stretch" spacing={2}>
            {visibleItems.map((item) => (
              <HStack
                key={item.label}
                p={3}
                bg="bg.subtle"
                borderRadius="md"
                spacing={3}
                role="group"
              >
                <HStack
                  flex={1}
                  spacing={3}
                  cursor="pointer"
                  onClick={() => navigate(item.path)}
                  _hover={{ "& p": { color: "brand.500" } }}
                >
                  <VStack align="start" spacing={0} flex={1}>
                    <Text fontSize="sm" fontWeight="medium">
                      {item.label}
                    </Text>
                    <Text fontSize="xs" color="text.muted">
                      {item.desc}
                    </Text>
                  </VStack>
                  <Icon as={FiArrowRight} color="text.muted" boxSize={4} />
                </HStack>
                <IconButton
                  aria-label={`Remove "${item.label}" suggestion`}
                  icon={
                    <Text fontSize="md" lineHeight={1}>
                      ×
                    </Text>
                  }
                  variant="ghost"
                  size="xs"
                  color="text.muted"
                  opacity={0}
                  _groupHover={{ opacity: 1 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleHideItem(item.label);
                  }}
                />
              </HStack>
            ))}
          </VStack>
          <Text fontSize="xs" color="text.muted">
            Tip: Use the Customize button on your dashboard to add or remove
            panels anytime.
          </Text>
        </VStack>
      </CardBody>
    </Card>
  );
};

const GettingStartedWidgetBase: React.FC = () => {
  const [dismissed, setDismissed] = useState<boolean>(
    () => localStorage.getItem(DISMISSED_KEY) === "true",
  );

  const { data: accounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api.get("/accounts/").then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: budgets } = useQuery({
    queryKey: ["budgets"],
    queryFn: () => api.get("/budgets/").then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: savingsGoals } = useQuery({
    queryKey: ["goals"],
    queryFn: () => api.get("/savings-goals/").then((r) => r.data),
    staleTime: 60_000,
  });

  if (dismissed) return null;

  const step1Done = Array.isArray(accounts) && accounts.length > 0;
  const step2Done = Array.isArray(budgets) && budgets.length > 0;
  const step3Done = Array.isArray(savingsGoals) && savingsGoals.length > 0;
  const step4Done =
    (Array.isArray(accounts) &&
      accounts.some(
        (a: { current_balance?: number | null }) =>
          (a.current_balance ?? 0) !== 0,
      )) ||
    localStorage.getItem(NET_WORTH_VIEWED_KEY) === "true";

  const allDone = step1Done && step2Done && step3Done && step4Done;

  if (allDone) return <WhatNextCard />;

  const handleDismiss = () => {
    localStorage.setItem(DISMISSED_KEY, "true");
    setDismissed(true);
  };

  return (
    <Card h="100%">
      <CardHeader pb={2}>
        <HStack justify="space-between" align="center">
          <VStack align="start" spacing={0}>
            <Heading size="md">Getting Started</Heading>
            <Text fontSize="xs" color="text.muted">
              Four quick steps to get the most out of Nest Egg
            </Text>
          </VStack>
          <IconButton
            aria-label="Dismiss getting started checklist"
            icon={
              <Text fontSize="lg" lineHeight={1}>
                ×
              </Text>
            }
            variant="ghost"
            size="sm"
            onClick={handleDismiss}
          />
        </HStack>
      </CardHeader>
      <CardBody pt={2}>
        <VStack align="stretch" spacing={4}>
          <Step
            label="Connect a bank account"
            hint="Everything works better with real data — transactions, budgets, and net worth all pull from your accounts."
            to="/accounts"
            done={step1Done}
          />
          <Step
            label="Set your first budget"
            hint="Pick one spending category (like Dining or Groceries) and set a monthly limit. You'll immediately see how you're doing."
            to="/budgets"
            done={step2Done}
          />
          <Step
            label="Create a savings goal"
            hint="Name something you're saving toward — an emergency fund, a trip, a down payment. Set a target and track progress."
            to="/goals"
            done={step3Done}
          />
          <Step
            label="Review your net worth"
            hint="Your net worth is everything you own minus everything you owe. It's the single most useful number to watch over time."
            to="/net-worth-timeline"
            done={step4Done}
          />
        </VStack>
      </CardBody>
    </Card>
  );
};

export const GettingStartedWidget = memo(GettingStartedWidgetBase);
