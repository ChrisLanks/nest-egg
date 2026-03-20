/**
 * GoalContextBanner
 *
 * Shows a gentle, dismissible reminder of the goal the user picked during
 * onboarding. Keeps the app feeling personalized after signup and gives
 * beginners a clear "what to do next" prompt.
 *
 * Reads the goal from localStorage (set in WelcomePage on finish).
 * Disappears permanently once the user dismisses it.
 */

import { useState } from "react";
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  CloseButton,
  HStack,
  Text,
} from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";

const DISMISSED_KEY = "nest-egg-goal-banner-dismissed";
const GOAL_KEY = "nest-egg-onboarding-goal";

interface GoalConfig {
  intro: string;
  cta: string;
  path: string;
}

const GOAL_CONFIGS: Record<string, GoalConfig> = {
  spending: {
    intro: "You said you want to track your spending.",
    cta: "Set your first budget",
    path: "/budgets",
  },
  retirement: {
    intro: "You said you want to plan for retirement.",
    cta: "See your retirement outlook",
    path: "/retirement",
  },
  investments: {
    intro: "You said you want to understand your investments.",
    cta: "View your portfolio",
    path: "/investments",
  },
};

export const GoalContextBanner = () => {
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISSED_KEY) === "true",
  );
  const navigate = useNavigate();

  const goal = localStorage.getItem(GOAL_KEY);

  // Hide if dismissed, no goal stored, or goal is unrecognised
  if (dismissed || !goal || !GOAL_CONFIGS[goal]) return null;

  const config = GOAL_CONFIGS[goal];

  const handleDismiss = () => {
    localStorage.setItem(DISMISSED_KEY, "true");
    setDismissed(true);
  };

  return (
    <Alert
      status="info"
      borderRadius="lg"
      mb={6}
      alignItems="flex-start"
      variant="subtle"
    >
      <AlertIcon mt="2px" />
      <Box flex={1}>
        <AlertDescription>
          <HStack spacing={3} align="center" flexWrap="wrap">
            <Text fontSize="sm">
              {config.intro}{" "}
              <Text as="span" color="text.secondary">
                Here's where to go next:
              </Text>
            </Text>
            <Button
              size="xs"
              colorScheme="blue"
              variant="solid"
              onClick={() => {
                handleDismiss();
                navigate(config.path);
              }}
            >
              {config.cta} →
            </Button>
          </HStack>
        </AlertDescription>
      </Box>
      <CloseButton
        alignSelf="flex-start"
        position="relative"
        right={-1}
        top={-1}
        onClick={handleDismiss}
        aria-label="Dismiss goal reminder"
      />
    </Alert>
  );
};
