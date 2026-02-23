/**
 * Banner shown when the logged-in user's email is not yet verified.
 * Dismissed for the browser session via sessionStorage.
 */

import { useState } from 'react';
import {
  Alert,
  AlertIcon,
  AlertDescription,
  Button,
  CloseButton,
  HStack,
  Text,
} from '@chakra-ui/react';
import { useAuthStore } from '../features/auth/stores/authStore';
import { authApi } from '../features/auth/services/authApi';

const DISMISSED_KEY = 'email_verification_banner_dismissed';

export const EmailVerificationBanner: React.FC = () => {
  const { user } = useAuthStore();
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem(DISMISSED_KEY) === '1'
  );
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  // Only show when user is logged in and email is unverified
  if (!user || user.email_verified || dismissed) return null;

  const handleDismiss = () => {
    sessionStorage.setItem(DISMISSED_KEY, '1');
    setDismissed(true);
  };

  const handleResend = async () => {
    setSending(true);
    try {
      await authApi.resendVerification();
      setSent(true);
    } catch {
      // silently ignore — the banner stays visible
    } finally {
      setSending(false);
    }
  };

  return (
    <Alert
      status="warning"
      borderRadius={0}
      px={6}
      py={2}
      flexShrink={0}
    >
      <AlertIcon boxSize={4} />
      <AlertDescription flex={1}>
        <HStack spacing={3} flexWrap="wrap">
          {sent ? (
            <Text fontSize="sm">
              Verification email sent — check your inbox for{' '}
              <strong>{user.email}</strong>.
            </Text>
          ) : (
            <>
              <Text fontSize="sm">
                Please verify your email address{' '}
                <strong>{user.email}</strong> to secure your account.
              </Text>
              <Button
                size="xs"
                colorScheme="orange"
                variant="solid"
                isLoading={sending}
                onClick={handleResend}
              >
                Resend verification email
              </Button>
            </>
          )}
        </HStack>
      </AlertDescription>
      <CloseButton size="sm" onClick={handleDismiss} ml={2} />
    </Alert>
  );
};
