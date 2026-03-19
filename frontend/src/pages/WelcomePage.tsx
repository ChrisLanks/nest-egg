/**
 * Post-registration onboarding wizard.
 *
 * Steps:
 * 1. Welcome — value proposition + household name
 * 2. Connect accounts — link first bank or skip
 * 3. Invite household members — why + how or skip
 * 4. Quick tour highlights — then go to dashboard
 */

import { useState } from "react";
import {
  Box,
  Button,
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
  useToast,
} from "@chakra-ui/react";
import {
  FiHome,
  FiLink,
  FiUsers,
  FiBarChart2,
  FiArrowRight,
  FiCheck,
  FiDollarSign,
  FiTarget,
  FiZap,
  FiList,
  FiTrendingUp,
  FiCalendar,
  FiBell,
  FiSettings,
  FiShield,
} from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import api from "../services/api";
import { AddAccountModal } from "../features/accounts/components/AddAccountModal";
import { useAuthStore } from "../features/auth/stores/authStore";

const STEPS = [
  { label: "Welcome", icon: FiHome },
  { label: "Accounts", icon: FiLink },
  { label: "Household", icon: FiUsers },
  { label: "Ready", icon: FiBarChart2 },
];

const HOUSEHOLD_BENEFITS = [
  {
    icon: FiBarChart2,
    title: "Combined net worth",
    desc: "See all accounts together — or filter to just one person's view",
  },
  {
    icon: FiDollarSign,
    title: "Shared budgets",
    desc: "Track spending across both of your accounts in one budget",
  },
  {
    icon: FiZap,
    title: "FIRE planning together",
    desc: "Coast FI and financial independence calculations use both your assets",
  },
  {
    icon: FiTrendingUp,
    title: "Joint retirement scenarios",
    desc: "Run Monte Carlo simulations that account for both incomes and goals",
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

const FEATURE_LIST = [
  {
    icon: FiBarChart2,
    title: "Overview Dashboard",
    desc: "Net worth trend, spending breakdown, and financial health at a glance",
  },
  {
    icon: FiDollarSign,
    title: "Budget Tracking",
    desc: "Monthly budgets per category with real-time spending and overage alerts",
  },
  {
    icon: FiList,
    title: "Transactions",
    desc: "Full spending history with smart categorization and search",
  },
  {
    icon: FiTarget,
    title: "Savings Goals",
    desc: "Track progress toward specific goals like a house, car, or emergency fund",
  },
  {
    icon: FiLink,
    title: "Investment Analysis",
    desc: "Portfolio breakdown, asset allocation, and Monte Carlo projections",
  },
  {
    icon: FiZap,
    title: "FIRE Dashboard",
    desc: "FI ratio, Coast FI, and years-to-retirement updated with every sync",
  },
  {
    icon: FiHome,
    title: "Retirement Planner",
    desc: "Scenario-based simulations with Social Security, healthcare, and tax modeling",
  },
  {
    icon: FiCalendar,
    title: "Financial Calendar",
    desc: "Recurring bills, expected transactions, and cash flow forecasting",
  },
  {
    icon: FiBell,
    title: "Smart Notifications",
    desc: "Per-category alerts for budgets, milestones, account syncs, and household events — tune what you see in Preferences",
  },
  {
    icon: FiSettings,
    title: "Customizable Preferences",
    desc: "Control notification categories, email delivery, sidebar layout, currency, and appearance",
  },
];

export default function WelcomePage() {
  const [step, setStep] = useState(0);
  const [householdName, setHouseholdName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [addAccountOpen, setAddAccountOpen] = useState(false);
  const [accountLinked, setAccountLinked] = useState(false);
  const [inviteSent, setInviteSent] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();
  const { user, setUser } = useAuthStore();

  const updateHouseholdMutation = useMutation({
    mutationFn: async (name: string) => {
      await api.patch("/household/settings", { name });
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

  const finish = async () => {
    try {
      await api.post("/onboarding/complete");
      if (user) {
        setUser({ ...user, onboarding_completed: true });
      }
    } catch {
      // Best-effort — don't block navigation
    }
    navigate("/overview");
  };

  const next = () => {
    if (step === 0 && householdName.trim()) {
      updateHouseholdMutation.mutate(householdName.trim());
    }
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      finish();
    }
  };

  const progressPercent = ((step + 1) / STEPS.length) * 100;

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
            <SimpleGrid columns={3} spacing={3}>
              {[
                { icon: FiBarChart2, label: "Net worth tracking" },
                { icon: FiDollarSign, label: "Budget & spending" },
                { icon: FiZap, label: "FIRE & retirement" },
              ].map((item) => (
                <VStack
                  key={item.label}
                  p={3}
                  borderRadius="md"
                  bg="bg.subtle"
                  spacing={1}
                  align="center"
                >
                  <Icon as={item.icon} boxSize={5} color="brand.500" />
                  <Text fontSize="xs" fontWeight="medium" textAlign="center">
                    {item.label}
                  </Text>
                </VStack>
              ))}
            </SimpleGrid>
            <FormControl>
              <FormLabel>Household name</FormLabel>
              <Input
                value={householdName}
                onChange={(e) => setHouseholdName(e.target.value)}
                placeholder="e.g. The Smith Family"
                size="lg"
              />
              <Text fontSize="xs" color="text.muted" mt={1}>
                This is shown to household members. You can change it later in
                Household Settings.
              </Text>
            </FormControl>
          </VStack>
        )}

        {step === 1 && (
          <VStack spacing={6} align="stretch">
            <VStack spacing={2}>
              <Heading size="lg">Connect Your Accounts</Heading>
              <Text color="text.secondary" textAlign="center">
                Link a bank account to automatically import transactions and
                track your net worth. You can also add accounts manually.
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
              <VStack spacing={3}>
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
                  We support 11,000+ institutions via Plaid, Teller, and MX. The
                  app auto-selects the best configured provider for you. Your
                  credentials are never stored on our servers.
                </Text>
              </VStack>
            )}
            <AddAccountModal
              isOpen={addAccountOpen}
              onClose={() => {
                setAddAccountOpen(false);
                setAccountLinked(true);
              }}
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
                  They'll receive a link to join your household. You can invite
                  more people from Household Settings.
                </Text>
              </VStack>
            ) : (
              <FormControl>
                <FormLabel>Partner's email address</FormLabel>
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
                    isDisabled={!inviteEmail.includes("@")}
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
          <VStack spacing={6} align="center">
            <Heading size="lg">You're All Set!</Heading>
            <Text color="text.secondary" textAlign="center" maxW="md">
              Here's everything waiting for you in your dashboard:
            </Text>
            <SimpleGrid columns={2} spacing={3} w="full">
              {FEATURE_LIST.map((item) => (
                <HStack
                  key={item.title}
                  spacing={3}
                  p={3}
                  borderRadius="md"
                  bg="bg.subtle"
                  align="start"
                >
                  <Icon
                    as={item.icon}
                    boxSize={5}
                    color="brand.500"
                    mt="1px"
                    flexShrink={0}
                  />
                  <VStack align="start" spacing={0}>
                    <Text fontSize="sm" fontWeight="semibold">
                      {item.title}
                    </Text>
                    <Text fontSize="xs" color="text.secondary">
                      {item.desc}
                    </Text>
                  </VStack>
                </HStack>
              ))}
            </SimpleGrid>
          </VStack>
        )}
      </Box>

      {/* Navigation buttons */}
      <HStack justify="space-between" mt={6}>
        <Button
          variant="ghost"
          onClick={step === 0 ? finish : () => setStep(step - 1)}
          size="sm"
        >
          {step === 0 ? "Skip setup" : "Back"}
        </Button>
        <Button
          colorScheme="brand"
          rightIcon={step === STEPS.length - 1 ? <FiCheck /> : <FiArrowRight />}
          onClick={next}
          size="lg"
        >
          {step === STEPS.length - 1 ? "Go to Dashboard" : "Continue"}
        </Button>
      </HStack>
    </Container>
  );
}
