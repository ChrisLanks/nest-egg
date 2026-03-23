/**
 * Post-registration onboarding wizard.
 *
 * Steps:
 * 1. Welcome — goal selector + household name
 * 2. Connect accounts — link first bank or skip
 * 3. Invite household members — why + how or skip
 * 4. Dashboard style — simple (5 widgets) or advanced (11 widgets)
 * 5. Ready — focused CTA based on chosen goal
 */

import { useState, useEffect } from "react";
import {
  Box,
  Button,
  Checkbox,
  Container,
  Heading,
  HStack,
  Icon,
  Input,
  Text,
  VStack,
  Progress,
  FormControl,
  FormLabel,
  SimpleGrid,
  List,
  ListItem,
  ListIcon,
  useToast,
} from "@chakra-ui/react";
import {
  FiHome,
  FiLink,
  FiUsers,
  FiLayout,
  FiBarChart2,
  FiArrowRight,
  FiCheck,
  FiDollarSign,
  FiZap,
  FiTrendingUp,
  FiShield,
} from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import api from "../services/api";
import { AddAccountModal } from "../features/accounts/components/AddAccountModal";
import { useAuthStore } from "../features/auth/stores/authStore";
import { validateEmail } from "../utils/validation";
import {
  SIMPLE_LAYOUT,
  ADVANCED_LAYOUT,
} from "../features/dashboard/widgetRegistry";

const STEPS = [
  { label: "Welcome", icon: FiHome },
  { label: "Accounts", icon: FiLink },
  { label: "Household", icon: FiUsers },
  { label: "Dashboard", icon: FiLayout },
  { label: "Ready", icon: FiBarChart2 },
];

const HOUSEHOLD_BENEFITS = [
  {
    icon: FiBarChart2,
    title: "Combined net worth",
    desc: "See your total assets minus debts in one number — across both of your accounts",
  },
  {
    icon: FiDollarSign,
    title: "Shared budgets",
    desc: "Track spending across both of your accounts in one budget",
  },
  {
    icon: FiZap,
    title: "Retirement planning together",
    desc: "See if you can both retire when you want — using your combined savings and income",
  },
  {
    icon: FiTrendingUp,
    title: "Joint retirement projections",
    desc: "Model different scenarios: what if one of you stops working early, or you save more?",
  },
  {
    icon: FiShield,
    title: "Granular permissions",
    desc: "Control exactly what each member can see and do — grant or restrict access per feature",
  },
  {
    icon: FiUsers,
    title: "Up to 5 members",
    desc: "Add partners, adult children, or anyone else who shares your financial life",
  },
];

const GOAL_OPTIONS = [
  {
    id: "spending",
    icon: FiDollarSign,
    title: "Track my spending",
    desc: "See where my money goes each month and set a budget so I stop overspending",
  },
  {
    id: "retirement",
    icon: FiZap,
    title: "Plan for retirement",
    desc: "Based on what I save, see when I could stop working — and what I need to get there",
  },
  {
    id: "investments",
    icon: FiTrendingUp,
    title: "Understand my investments",
    desc: "If I have a 401(k) or brokerage account, see what's in it and what it costs me each year",
  },
];

const GOAL_HIGHLIGHTS: Record<string, string> = {
  spending: "budgets, spending breakdowns, and transaction history",
  retirement:
    "your retirement planner, savings projections, and years-to-retirement tracker",
  investments:
    "your portfolio value, what you're invested in, and how much it costs you each year",
};

const GOAL_CTA_LABEL: Record<string, string> = {
  spending: "Set my first budget",
  retirement: "See my retirement outlook",
  investments: "View my investments",
};

const GOAL_DESTINATION: Record<string, string> = {
  spending: "/budgets",
  retirement: "/retirement",
  investments: "/investments",
};

const GOAL_NEXT_SENTENCE: Record<string, string> = {
  spending:
    "Most people start by setting a monthly budget — it takes 2 minutes and immediately shows where your money goes.",
  retirement:
    "Head to your retirement planner to see if you're on track and when you could stop working.",
  investments:
    "Check your investments page to see your portfolio, what it's costing you each year, and how your money is split.",
};

const DASHBOARD_OPTIONS = [
  {
    id: "simple",
    title: "Keep it simple",
    desc: "A clean starting point — just the essentials. You can always add more later.",
    includes: [
      "Net worth at a glance",
      "Your top spending categories this month",
      "Recent transactions",
      "Setup checklist to guide you",
    ],
  },
  {
    id: "advanced",
    title: "Show me everything",
    desc: "The full dashboard — every chart and panel from day one.",
    includes: [
      "Everything in Simple, plus:",
      "Cash flow trend and 90-day forecast",
      "Spending insights and anomaly alerts",
      "Account balances, budgets, and savings goals",
    ],
  },
];

export default function WelcomePage() {
  const [step, setStep] = useState(0);
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null);
  const [selectedDashboard, setSelectedDashboard] = useState<
    "simple" | "advanced" | null
  >(null);
  const [householdName, setHouseholdName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [addAccountOpen, setAddAccountOpen] = useState(false);
  const [accountLinked, setAccountLinked] = useState(false);
  const [inviteSent, setInviteSent] = useState(false);
  const [showAdvancedNav, setShowAdvancedNav] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();
  const { user, setUser } = useAuthStore();

  // Re-entry guard: redirect users who have already completed onboarding.
  // For users mid-onboarding, restore their last saved step.
  useEffect(() => {
    if (user?.onboarding_completed) {
      navigate("/", { replace: true });
      return;
    }
    if (user?.onboarding_step) {
      const STEP_MAP: Record<string, number> = {
        profile: 0,
        accounts: 1,
        budget: 3,
        goals: 3,
      };
      const restored = STEP_MAP[user.onboarding_step];
      if (restored !== undefined) {
        setStep(restored);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateHouseholdMutation = useMutation({
    mutationFn: async (name: string) => {
      await api.patch("/settings/organization", { name });
    },
    onError: () => {
      // Non-critical — don't block onboarding
    },
  });

  const inviteMutation = useMutation({
    mutationFn: async (email: string) => {
      await api.post("/household/invite", { email });
    },
    onSuccess: () => {
      setInviteSent(true);
      toast({
        title: "Invitation sent",
        description: `We sent an invite to ${inviteEmail}`,
        status: "success",
        duration: 3000,
      });
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail;
      toast({
        title: "Could not send invite",
        description: typeof detail === "string" ? detail : "Try again later",
        status: "error",
        duration: 4000,
      });
    },
  });

  const finish = async (destination?: string) => {
    // Persist selected goal so the dashboard can show a contextual reminder
    if (selectedGoal) {
      localStorage.setItem("nest-egg-onboarding-goal", selectedGoal);
    }
    // Persist advanced nav preference
    localStorage.setItem("nest-egg-show-advanced-nav", String(showAdvancedNav));
    // Save chosen dashboard layout — best-effort, don't block navigation
    try {
      const layout =
        selectedDashboard === "advanced" ? ADVANCED_LAYOUT : SIMPLE_LAYOUT;
      await api.put("/settings/dashboard-layout", { layout });
    } catch {
      // Non-critical
    }
    // Persist onboarding goal server-side — best-effort, don't block navigation
    if (selectedGoal) {
      try {
        await api.patch("/settings/profile", { onboarding_goal: selectedGoal });
      } catch {
        // Non-critical
      }
    }
    try {
      await api.post("/onboarding/complete");
      if (user) {
        setUser({ ...user, onboarding_completed: true });
      }
    } catch {
      toast({
        title: "Failed to complete setup. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
      return;
    }
    navigate(destination ?? "/overview");
  };

  const next = () => {
    if (step === 0 && householdName.trim()) {
      updateHouseholdMutation.mutate(householdName.trim());
    }
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      const destination = selectedGoal
        ? GOAL_DESTINATION[selectedGoal]
        : "/budgets";
      finish(destination);
    }
  };

  const progressPercent = ((step + 1) / STEPS.length) * 100;

  const primaryCtaLabel = selectedGoal
    ? GOAL_CTA_LABEL[selectedGoal]
    : "Set a monthly budget";

  const primaryCtaDestination = selectedGoal
    ? GOAL_DESTINATION[selectedGoal]
    : "/budgets";

  return (
    <Container maxW="container.md" py={12}>
      {/* Progress bar */}
      <Progress
        value={progressPercent}
        size="sm"
        colorScheme="brand"
        borderRadius="full"
        mb={2}
      />
      <HStack justify="space-between" mb={8}>
        {STEPS.map((s, i) => (
          <HStack
            key={s.label}
            spacing={1}
            color={i <= step ? "brand.500" : "text.muted"}
            fontSize="xs"
            fontWeight={i === step ? "bold" : "normal"}
          >
            <Icon as={i < step ? FiCheck : s.icon} />
            <Text display={{ base: "none", md: "inline" }}>{s.label}</Text>
          </HStack>
        ))}
      </HStack>

      {/* Step content */}
      <Box bg="bg.surface" p={8} borderRadius="xl" boxShadow="lg" minH="320px">
        {step === 0 && (
          <VStack spacing={6} align="stretch">
            <VStack spacing={2}>
              <Heading size="lg">Welcome to Nest Egg</Heading>
              <Text color="text.secondary" textAlign="center">
                Your complete household financial dashboard — accounts, budgets,
                investments, and retirement planning in one place.
              </Text>
            </VStack>

            {/* Goal selector */}
            <VStack spacing={3} align="stretch">
              <VStack spacing={0} align="stretch">
                <Text fontWeight="semibold" fontSize="sm">
                  What brings you here?
                </Text>
                <Text fontSize="xs" color="text.muted">
                  Pick what to tackle first — you can do all of this once
                  you&apos;re set up.
                </Text>
              </VStack>
              <SimpleGrid columns={{ base: 1, sm: 3 }} spacing={3}>
                {GOAL_OPTIONS.map((goal) => (
                  <Box
                    key={goal.id}
                    cursor="pointer"
                    border="2px solid"
                    borderColor={
                      selectedGoal === goal.id ? "brand.500" : "border.default"
                    }
                    borderRadius="lg"
                    p={4}
                    onClick={() => setSelectedGoal(goal.id)}
                    transition="border-color 0.15s"
                    _hover={{ borderColor: "brand.400" }}
                  >
                    <VStack spacing={2} align="start">
                      <Icon
                        as={goal.icon}
                        boxSize={5}
                        color={
                          selectedGoal === goal.id ? "brand.500" : "text.muted"
                        }
                      />
                      <Text fontSize="sm" fontWeight="semibold">
                        {goal.title}
                      </Text>
                      <Text fontSize="xs" color="text.secondary">
                        {goal.desc}
                      </Text>
                    </VStack>
                  </Box>
                ))}
              </SimpleGrid>
              {selectedGoal && (
                <Box bg="bg.subtle" p={3} borderRadius="md">
                  <Text fontSize="sm" color="text.secondary">
                    We&apos;ll highlight{" "}
                    <Text as="span" fontWeight="medium" color="text.primary">
                      {GOAL_HIGHLIGHTS[selectedGoal]}
                    </Text>{" "}
                    for you.
                  </Text>
                </Box>
              )}
            </VStack>

            <FormControl>
              <FormLabel>Household name</FormLabel>
              <Input
                value={householdName}
                onChange={(e) => setHouseholdName(e.target.value)}
                placeholder="e.g. Jane's Finances or The Smith Family"
                size="lg"
              />
              <Text fontSize="xs" color="text.muted" mt={1}>
                Just a label for your account — you can change it anytime.
              </Text>
            </FormControl>

            {/* Advanced features opt-in */}
            <Box
              p={3}
              bg="bg.subtle"
              borderRadius="md"
              border="1px solid"
              borderColor="border.default"
            >
              <Checkbox
                isChecked={showAdvancedNav}
                onChange={(e) => setShowAdvancedNav(e.target.checked)}
                colorScheme="brand"
              >
                <Text fontSize="sm" fontWeight="medium">
                  I&apos;m an experienced investor — show advanced features
                </Text>
              </Checkbox>
              <Text fontSize="xs" color="text.muted" mt={1} ml={6}>
                Unlocks FIRE planning, Tax Projection, and more. You can turn
                this on or off anytime in Settings.
              </Text>
            </Box>
          </VStack>
        )}

        {step === 1 && (
          <VStack spacing={6} align="stretch">
            <VStack spacing={2}>
              <Heading size="lg">Connect Your Accounts</Heading>
              <Text color="text.secondary" textAlign="center">
                Link a bank account to automatically import transactions and
                track your net worth in real time.
              </Text>
            </VStack>
            {accountLinked ? (
              <VStack
                spacing={3}
                p={6}
                bg="bg.success"
                borderRadius="lg"
                align="center"
              >
                <Icon as={FiCheck} boxSize={10} color="green.500" />
                <Text fontWeight="semibold" color="green.700">
                  Account connected successfully!
                </Text>
                <Text fontSize="sm" color="text.secondary">
                  You can add more accounts anytime from the sidebar.
                </Text>
              </VStack>
            ) : (
              <VStack spacing={4}>
                {/* How it works — reassures first-timers before they click */}
                <Box
                  w="full"
                  p={4}
                  bg="bg.subtle"
                  borderRadius="lg"
                  border="1px solid"
                  borderColor="border.default"
                >
                  <VStack spacing={2} align="stretch">
                    <Text fontSize="sm" fontWeight="semibold">
                      How this works
                    </Text>
                    {[
                      {
                        icon: FiShield,
                        text: "We connect through trusted providers like Plaid and Teller — the same technology used by Venmo, Coinbase, and thousands of other apps. Your bank login is entered directly on your bank's own secure page, not ours.",
                      },
                      {
                        icon: FiCheck,
                        text: "We never see or store your bank password. Nest Egg only receives a read-only connection to import transactions and balances.",
                      },
                      {
                        icon: FiLink,
                        text: "We support 11,000+ banks and credit unions. You can disconnect at any time from Account Settings.",
                      },
                    ].map((item) => (
                      <HStack key={item.text} spacing={3} align="start">
                        <Icon
                          as={item.icon}
                          boxSize={4}
                          color="brand.500"
                          mt="2px"
                          flexShrink={0}
                        />
                        <Text fontSize="xs" color="text.secondary">
                          {item.text}
                        </Text>
                      </HStack>
                    ))}
                  </VStack>
                </Box>
                <Button
                  size="lg"
                  colorScheme="brand"
                  leftIcon={<FiLink />}
                  w="full"
                  onClick={() => setAddAccountOpen(true)}
                >
                  Connect a Bank Account
                </Button>
                <Text fontSize="xs" color="text.muted" textAlign="center">
                  Prefer to enter accounts manually? You can skip this step and
                  add them by hand from the Accounts page.
                </Text>
              </VStack>
            )}
            <AddAccountModal
              isOpen={addAccountOpen}
              onClose={() => setAddAccountOpen(false)}
              onSuccess={() => setAccountLinked(true)}
            />
          </VStack>
        )}

        {step === 2 && (
          <VStack spacing={6} align="stretch">
            <VStack spacing={2}>
              <Heading size="lg">Build Your Household</Heading>
              <Text color="text.secondary" textAlign="center">
                Nest Egg is built for couples and families managing money
                together. Add up to 5 members — partners, adult children, or
                anyone who shares your financial life:
              </Text>
            </VStack>
            <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={3}>
              {HOUSEHOLD_BENEFITS.map((b) => (
                <HStack
                  key={b.title}
                  spacing={3}
                  p={3}
                  borderRadius="md"
                  bg="bg.subtle"
                  align="start"
                >
                  <Icon as={b.icon} boxSize={5} color="brand.500" mt="1px" />
                  <VStack align="start" spacing={0}>
                    <Text fontSize="sm" fontWeight="semibold">
                      {b.title}
                    </Text>
                    <Text fontSize="xs" color="text.secondary">
                      {b.desc}
                    </Text>
                  </VStack>
                </HStack>
              ))}
            </SimpleGrid>
            {inviteSent ? (
              <VStack
                spacing={3}
                p={6}
                bg="bg.success"
                borderRadius="lg"
                align="center"
              >
                <Icon as={FiCheck} boxSize={10} color="green.500" />
                <Text fontWeight="semibold" color="green.700">
                  Invitation sent to {inviteEmail}
                </Text>
                <Text fontSize="sm" color="text.secondary">
                  They&apos;ll receive a link to join your household. You can
                  invite more people from Household Settings.
                </Text>
              </VStack>
            ) : (
              <FormControl>
                <FormLabel>Partner&apos;s email address</FormLabel>
                <HStack>
                  <Input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="partner@example.com"
                  />
                  <Button
                    colorScheme="brand"
                    onClick={() => inviteMutation.mutate(inviteEmail)}
                    isLoading={inviteMutation.isPending}
                    isDisabled={!validateEmail(inviteEmail).valid}
                  >
                    Invite
                  </Button>
                </HStack>
                <Text fontSize="xs" color="text.muted" mt={2}>
                  Each person keeps their own login. You control what they can
                  view and edit from Household Settings → Permissions. You can
                  invite more members anytime.
                </Text>
              </FormControl>
            )}
          </VStack>
        )}

        {step === 3 && (
          <VStack spacing={6} align="stretch">
            <VStack spacing={2}>
              <Heading size="lg">How do you want your dashboard?</Heading>
              <Text color="text.secondary" textAlign="center">
                Choose how much you want to see when you first log in. You can
                always add or remove panels later.
              </Text>
            </VStack>
            <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={4}>
              {DASHBOARD_OPTIONS.map((opt) => (
                <Box
                  key={opt.id}
                  cursor="pointer"
                  border="2px solid"
                  borderColor={
                    selectedDashboard === opt.id
                      ? "brand.500"
                      : "border.default"
                  }
                  borderRadius="lg"
                  p={5}
                  onClick={() =>
                    setSelectedDashboard(opt.id as "simple" | "advanced")
                  }
                  transition="border-color 0.15s"
                  _hover={{ borderColor: "brand.400" }}
                  position="relative"
                >
                  {selectedDashboard === opt.id && (
                    <Icon
                      as={FiCheck}
                      position="absolute"
                      top={3}
                      right={3}
                      color="brand.500"
                      boxSize={4}
                    />
                  )}
                  <VStack spacing={3} align="start">
                    <VStack spacing={0} align="start">
                      <Text fontWeight="semibold">{opt.title}</Text>
                      <Text fontSize="xs" color="text.secondary">
                        {opt.desc}
                      </Text>
                    </VStack>
                    <List spacing={1}>
                      {opt.includes.map((item) => (
                        <ListItem key={item} fontSize="xs" color="text.muted">
                          <ListIcon
                            as={FiCheck}
                            color={
                              selectedDashboard === opt.id
                                ? "brand.500"
                                : "text.muted"
                            }
                          />
                          {item}
                        </ListItem>
                      ))}
                    </List>
                  </VStack>
                </Box>
              ))}
            </SimpleGrid>
            <Text fontSize="xs" color="text.muted" textAlign="center">
              Not sure? Start simple — it&apos;s easier to add panels than to
              feel overwhelmed.
            </Text>
          </VStack>
        )}

        {step === 4 && (
          <VStack spacing={6} align="center">
            <Box
              bg="green.50"
              borderRadius="full"
              p={4}
              display="inline-flex"
              alignItems="center"
              justifyContent="center"
            >
              <Icon as={FiCheck} boxSize={16} color="green.500" />
            </Box>
            <Heading size="lg">You&apos;re all set!</Heading>
            <Text color="text.secondary" textAlign="center" maxW="md">
              Your dashboard is ready.{" "}
              {selectedGoal
                ? GOAL_NEXT_SENTENCE[selectedGoal]
                : GOAL_NEXT_SENTENCE["spending"]}
            </Text>
            <VStack maxW="sm" w="full" mx="auto" spacing={3}>
              <Button
                colorScheme="brand"
                size="lg"
                w="full"
                onClick={() => finish(primaryCtaDestination)}
              >
                {primaryCtaLabel}
              </Button>
              <Button
                variant="ghost"
                w="full"
                onClick={() => finish("/overview")}
              >
                Take me to the dashboard
              </Button>
            </VStack>
          </VStack>
        )}
      </Box>

      {/* Navigation buttons */}
      <HStack justify="space-between" mt={6}>
        <Button
          variant="ghost"
          onClick={step === 0 ? () => finish() : () => setStep(step - 1)}
          size="sm"
        >
          {step === 0 ? "Skip for now" : "Back"}
        </Button>
        <Button
          colorScheme="brand"
          rightIcon={step === STEPS.length - 1 ? <FiCheck /> : <FiArrowRight />}
          onClick={next}
          size="lg"
        >
          {step === STEPS.length - 1 ? primaryCtaLabel : "Continue"}
        </Button>
      </HStack>
    </Container>
  );
}
