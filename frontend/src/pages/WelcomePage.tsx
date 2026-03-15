/**
 * Post-registration onboarding wizard.
 *
 * Steps:
 * 1. Welcome — household name confirmation
 * 2. Connect accounts — link first bank or skip
 * 3. Invite household members — or skip
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
  useToast,
} from "@chakra-ui/react";
import {
  FiHome,
  FiLink,
  FiUsers,
  FiBarChart2,
  FiArrowRight,
  FiCheck,
} from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import api from "../services/api";
import { AddAccountModal } from "../features/accounts/components/AddAccountModal";

const STEPS = [
  { label: "Welcome", icon: FiHome },
  { label: "Accounts", icon: FiLink },
  { label: "Household", icon: FiUsers },
  { label: "Ready", icon: FiBarChart2 },
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

  const finish = () => {
    localStorage.setItem("nest-egg-onboarding-complete", "true");
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
                Let's get your household set up. This takes about 2 minutes.
              </Text>
            </VStack>
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
                  We support 11,000+ institutions via Plaid, Teller, and MX.
                  Your credentials are never stored on our servers.
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
              <Heading size="lg">Invite Household Members</Heading>
              <Text color="text.secondary" textAlign="center">
                Nest Egg supports up to 5 household members. Each person gets
                their own login with individual account views and shared
                household analytics.
              </Text>
            </VStack>
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
                <FormLabel>Email address</FormLabel>
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
                  By default, members can view each other's data but can't edit
                  it. You control permissions from the Permissions page.
                </Text>
              </FormControl>
            )}
          </VStack>
        )}

        {step === 3 && (
          <VStack spacing={6} align="center">
            <Heading size="lg">You're All Set!</Heading>
            <Text color="text.secondary" textAlign="center" maxW="md">
              Your dashboard is ready. Here's what you can explore:
            </Text>
            <VStack spacing={3} align="stretch" w="full" maxW="sm">
              {[
                {
                  icon: FiBarChart2,
                  title: "Overview Dashboard",
                  desc: "Net worth, spending insights, and financial health at a glance",
                },
                {
                  icon: FiLink,
                  title: "Investment Analysis",
                  desc: "9-tab portfolio analysis with Monte Carlo projections",
                },
                {
                  icon: FiHome,
                  title: "Retirement Planner",
                  desc: "Monte Carlo simulations with Social Security and healthcare modeling",
                },
                {
                  icon: FiUsers,
                  title: "Household Views",
                  desc: "Switch between combined and individual member views",
                },
              ].map((item) => (
                <HStack
                  key={item.title}
                  spacing={3}
                  p={3}
                  borderRadius="md"
                  bg="bg.subtle"
                >
                  <Icon as={item.icon} boxSize={5} color="brand.500" />
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
            </VStack>
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
