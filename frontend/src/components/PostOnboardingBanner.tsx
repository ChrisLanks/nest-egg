/**
 * PostOnboardingBanner — shown after a user adds their first account(s).
 *
 * Guides early users toward the next 2-3 high-value actions:
 * setting a goal, running a tax projection, and exploring their net worth.
 * Dismissable; hidden once dismissed or after 5+ logins.
 */
import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  CloseButton,
  HStack,
  SimpleGrid,
  Text,
} from "@chakra-ui/react";
import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";

const DISMISS_KEY = "nest-egg-post-onboarding-banner-dismissed";
const MAX_LOGINS = 5;

/** Show the banner when the user has accounts but is still early in their journey. */
export const shouldShowPostOnboardingBanner = (
  accountCount: number,
  loginCount: number | undefined,
  dismissed: boolean,
): boolean => {
  if (dismissed) return false;
  if (accountCount === 0) return false; // GettingStartedEmptyState handles this
  if ((loginCount ?? 0) >= MAX_LOGINS) return false; // seasoned user — stop nudging
  return true;
};

const NEXT_STEPS: Array<{ label: string; hint: string; path: string }> = [
  {
    label: "Set a goal",
    hint: "Tell Nest Egg what you're working toward — retirement, a home, or a rainy day fund.",
    path: "/goals",
  },
  {
    label: "See your tax projection",
    hint: "Get an estimate of what you'll owe this year before April arrives.",
    path: "/tax-center",
  },
  {
    label: "Check your net worth",
    hint: "See your assets vs. liabilities in one chart — the starting point for any financial plan.",
    path: "/net-worth",
  },
];

interface PostOnboardingBannerProps {
  accountCount: number;
  loginCount?: number;
}

export const PostOnboardingBanner = ({
  accountCount,
  loginCount,
}: PostOnboardingBannerProps) => {
  const [dismissed, setDismissed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === "true";
    } catch {
      return false;
    }
  });

  const dismiss = () => {
    setDismissed(true);
    try {
      localStorage.setItem(DISMISS_KEY, "true");
    } catch {}
  };

  if (!shouldShowPostOnboardingBanner(accountCount, loginCount, dismissed)) {
    return null;
  }

  return (
    <Alert status="success" borderRadius="md" mb={4} alignItems="flex-start">
      <AlertIcon mt={1} />
      <Box flex={1}>
        <AlertDescription>
          <Text fontSize="sm" fontWeight="semibold" mb={2}>
            Account added — here's what to do next:
          </Text>
          <SimpleGrid columns={{ base: 1, sm: 3 }} spacing={2}>
            {NEXT_STEPS.map((step) => (
              <Button
                key={step.path}
                as={RouterLink}
                to={step.path}
                size="xs"
                colorScheme="green"
                variant="outline"
                justifyContent="flex-start"
                whiteSpace="normal"
                height="auto"
                py={1}
                px={2}
                textAlign="left"
                title={step.hint}
              >
                {step.label} →
              </Button>
            ))}
          </SimpleGrid>
        </AlertDescription>
      </Box>
      <CloseButton onClick={dismiss} size="sm" mt={1} />
    </Alert>
  );
};

export default PostOnboardingBanner;
