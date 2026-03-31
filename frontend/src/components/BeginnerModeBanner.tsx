/**
 * BeginnerModeBanner — shown to new users on their first few sessions.
 * Explains that the app starts in Simple Mode and advanced features unlock over time.
 * Dismissable, stored in localStorage.
 */
import { Alert, AlertDescription, AlertIcon, Box, Button, CloseButton, HStack, Text } from "@chakra-ui/react";
import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";

const DISMISS_KEY = "nest-egg-beginner-banner-dismissed";

const isNewUser = (loginCount: number | undefined): boolean =>
  !loginCount || loginCount <= 3;

interface BeginnerModeBannerProps {
  loginCount?: number;
}

export const BeginnerModeBanner = ({ loginCount }: BeginnerModeBannerProps) => {
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

  if (dismissed || !isNewUser(loginCount)) return null;

  return (
    <Alert status="info" borderRadius="md" mb={4}>
      <AlertIcon />
      <Box flex={1}>
        <AlertDescription>
          <Text fontSize="sm">
            <strong>You're in Simple Mode.</strong> The app starts with the essentials — advanced
            features like FIRE planning, PE metrics, and Roth conversion analysis unlock as you add
            accounts and enable them in{" "}
            <Text as={RouterLink} to="/preferences" color="blue.600" textDecoration="underline" display="inline">
              Preferences
            </Text>
            .
          </Text>
        </AlertDescription>
      </Box>
      <HStack>
        <Button as={RouterLink} to="/preferences" size="xs" colorScheme="blue" variant="outline">
          Preferences
        </Button>
        <CloseButton onClick={dismiss} size="sm" />
      </HStack>
    </Alert>
  );
};

export default BeginnerModeBanner;
