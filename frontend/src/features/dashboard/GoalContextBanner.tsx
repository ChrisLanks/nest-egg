/**
 * GoalContextBanner
 *
 * Shows a gentle, dismissible reminder of the goal the user picked during
 * onboarding. Keeps the app feeling personalized after signup and gives
 * beginners a clear "what to do next" prompt.
 *
 * - For "investments" goal with no accounts connected yet, the CTA redirects
 *   to Accounts (to add one) instead of the empty investments page.
 * - Reads goal from localStorage (set in WelcomePage on finish).
 * - Dismissed permanently only after the user visits their goal page OR
 *   explicitly closes it after having visited. Clicking the CTA button
 *   marks it visited+dismissed. Closing without visiting re-shows the banner
 *   on the next session (up to 3 times), so accidental dismissal doesn't
 *   lock users out forever.
 */

import { useState, useEffect } from "react";
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
import { useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "../../services/api";
import { useAuthStore } from "../../features/auth/stores/authStore";

const DISMISSED_KEY = "nest-egg-goal-banner-dismissed";
const DISMISS_COUNT_KEY = "nest-egg-goal-banner-dismiss-count";
const GOAL_KEY = "nest-egg-onboarding-goal";

// Max times the user can soft-dismiss before it stops re-appearing
const MAX_SOFT_DISMISSALS = 3;

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

// When goal=investments but no accounts exist yet, redirect to Accounts
// instead of an empty investments page.
const INVESTMENTS_NO_ACCOUNTS_CONFIG: GoalConfig = {
  intro: "You said you want to understand your investments.",
  cta: "Add your investment account first",
  path: "/accounts",
};

export const GoalContextBanner = () => {
  const [dismissed, setDismissed] = useState(() => {
    // Permanently dismissed if user clicked the CTA (visited their goal page)
    if (localStorage.getItem(DISMISSED_KEY) === "true") return true;
    // Soft-dismissed too many times — stop showing
    const count = parseInt(
      localStorage.getItem(DISMISS_COUNT_KEY) ?? "0",
      10,
    );
    return count >= MAX_SOFT_DISMISSALS;
  });
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);

  const goal = localStorage.getItem(GOAL_KEY) || user?.onboarding_goal || null;

  // Auto-dismiss permanently when the user navigates to their goal page
  // (e.g. via the sidebar rather than the banner CTA)
  useEffect(() => {
    if (dismissed || !goal) return;
    const config = GOAL_CONFIGS[goal];
    if (!config) return;
    if (location.pathname === config.path || location.pathname.startsWith(config.path + "/")) {
      localStorage.setItem(DISMISSED_KEY, "true");
      setDismissed(true);
    }
  }, [location.pathname, goal, dismissed]);

  // Fetch accounts to detect the "investments goal, no accounts" scenario.
  // Only runs when goal=investments and not yet dismissed.
  const { data: accounts } = useQuery({
    queryKey: ["goal-banner-accounts"],
    queryFn: () => api.get("/accounts").then((r) => r.data as Array<unknown>),
    enabled: goal === "investments" && !dismissed,
    staleTime: 60_000,
  });

  // Hide if dismissed, no goal stored, or goal is unrecognised
  if (dismissed || !goal || !GOAL_CONFIGS[goal]) return null;

  const hasNoAccounts =
    goal === "investments" && Array.isArray(accounts) && accounts.length === 0;

  const config = hasNoAccounts
    ? INVESTMENTS_NO_ACCOUNTS_CONFIG
    : GOAL_CONFIGS[goal];

  /** CTA click: mark permanently dismissed (user reached their goal page). */
  const handleCtaClick = () => {
    localStorage.setItem(DISMISSED_KEY, "true");
    setDismissed(true);
    navigate(config.path);
  };

  /**
   * X click: soft-dismiss. Banner will re-appear on subsequent sessions
   * until MAX_SOFT_DISMISSALS is reached, so accidental closes don't
   * permanently hide the nudge.
   */
  const handleDismiss = () => {
    const prev = parseInt(
      localStorage.getItem(DISMISS_COUNT_KEY) ?? "0",
      10,
    );
    const next = prev + 1;
    localStorage.setItem(DISMISS_COUNT_KEY, String(next));
    if (next >= MAX_SOFT_DISMISSALS) {
      localStorage.setItem(DISMISSED_KEY, "true");
    }
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
              onClick={handleCtaClick}
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
