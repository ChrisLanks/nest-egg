/**
 * Email verification page — handles the /verify-email?token=... link
 * that is sent after registration or an email change.
 */

import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Center,
  VStack,
  Heading,
  Text,
  Button,
  Alert,
  AlertIcon,
  Spinner,
  Icon,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import { authApi } from '../features/auth/services/authApi';
import { useAuthStore } from '../features/auth/stores/authStore';

type State = 'loading' | 'success' | 'error' | 'no-token';

export const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();
  const [state, setState] = useState<State>('loading');
  const [resending, setResending] = useState(false);
  const [resendDone, setResendDone] = useState(false);

  const token = searchParams.get('token');

  useEffect(() => {
    if (!token) {
      setState('no-token');
      return;
    }

    authApi
      .verifyEmail(token)
      .then(() => {
        // Update local auth state so the unverified banner disappears immediately
        if (user) {
          setUser({ ...user, email_verified: true });
        }
        setState('success');
      })
      .catch(() => {
        setState('error');
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleResend = async () => {
    setResending(true);
    try {
      await authApi.resendVerification();
      setResendDone(true);
    } catch {
      // ignore — user may not be logged in
    } finally {
      setResending(false);
    }
  };

  return (
    <Center minH="100vh" bg="bg.canvas">
      <Box
        bg="bg.surface"
        borderRadius="xl"
        boxShadow="md"
        p={10}
        maxW="440px"
        w="full"
        mx={4}
      >
        {state === 'loading' && (
          <VStack spacing={4}>
            <Spinner size="xl" color="blue.500" thickness="4px" />
            <Text color="text.secondary">Verifying your email address…</Text>
          </VStack>
        )}

        {state === 'success' && (
          <VStack spacing={5} textAlign="center">
            <Icon as={CheckCircleIcon} boxSize={16} color="green.400" />
            <Heading size="md">Email verified!</Heading>
            <Text color="text.secondary">
              Your email address has been verified. You're all set.
            </Text>
            <Button
              colorScheme="blue"
              width="full"
              onClick={() => navigate('/overview')}
            >
              Go to dashboard
            </Button>
          </VStack>
        )}

        {(state === 'error' || state === 'no-token') && (
          <VStack spacing={5} textAlign="center">
            <Icon as={WarningIcon} boxSize={16} color="red.400" />
            <Heading size="md">Link invalid or expired</Heading>
            <Text color="text.secondary">
              This verification link is no longer valid. Links expire after 24
              hours and can only be used once.
            </Text>

            {resendDone ? (
              <Alert status="success" borderRadius="md">
                <AlertIcon />
                A new verification email has been sent. Check your inbox.
              </Alert>
            ) : (
              <Button
                colorScheme="blue"
                width="full"
                isLoading={resending}
                onClick={handleResend}
              >
                Resend verification email
              </Button>
            )}

            <Button
              variant="ghost"
              width="full"
              onClick={() => navigate('/overview')}
            >
              Back to app
            </Button>
          </VStack>
        )}
      </Box>
    </Center>
  );
};

export default VerifyEmailPage;
