/**
 * Login page with autocomplete and remember me support
 */

import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Container,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Heading,
  Input,
  Stack,
  Text,
  Link as ChakraLink,
  useToast,
  VStack,
  Checkbox,
  HStack,
  PinInput,
  PinInputField,
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link } from 'react-router-dom';
import { useLogin } from '../hooks/useAuth';
import { useState, useEffect } from 'react';
import { isMFAChallenge } from '../../../types/auth';
import { authApi } from '../services/authApi';
import { useAuthStore } from '../stores/authStore';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginPage = () => {
  const toast = useToast();
  const loginMutation = useLogin();
  const { setTokens } = useAuthStore();
  const [rememberMe, setRememberMe] = useState(false);
  const [credentialError, setCredentialError] = useState<string | null>(null);

  // MFA challenge state
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaError, setMfaError] = useState<string | null>(null);
  const [mfaLoading, setMfaLoading] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      rememberMe: false,
    },
  });

  // Load saved email on mount
  useEffect(() => {
    const savedEmail = localStorage.getItem('rememberedEmail');
    if (savedEmail) {
      setValue('email', savedEmail);
      setRememberMe(true);
    }
  }, [setValue]);

  const onSubmit = async (data: LoginFormData) => {
    setCredentialError(null);

    try {
      if (rememberMe) {
        localStorage.setItem('rememberedEmail', data.email);
      } else {
        localStorage.removeItem('rememberedEmail');
      }

      const result = await authApi.login(data);

      if (isMFAChallenge(result)) {
        // Backend requires MFA — show the TOTP step
        setMfaToken(result.mfa_token);
        return;
      }

      // Normal login — store tokens and navigate
      setTokens(result.access_token, result.user);
      window.location.href = '/dashboard';
    } catch (error: any) {
      const status = error?.response?.status;

      if (status === 401) {
        setCredentialError('Incorrect email or password.');
      } else if (status === 423) {
        setCredentialError('Account temporarily locked due to too many failed attempts. Please try again later.');
      } else if (status === 429) {
        toast({
          title: 'Too many attempts',
          description: 'Please wait a moment and try again.',
          status: 'warning',
          duration: 6000,
        });
      } else {
        toast({
          title: 'Login failed',
          description: 'Something went wrong on our end. Please try again.',
          status: 'error',
          duration: 5000,
        });
      }
    }
  };

  const handleMfaVerify = async () => {
    if (!mfaToken || mfaCode.length < 6) return;
    setMfaError(null);
    setMfaLoading(true);

    try {
      const result = await authApi.verifyMfa({ mfa_token: mfaToken, code: mfaCode });
      setTokens(result.access_token, result.user);
      window.location.href = '/dashboard';
    } catch (error: any) {
      const status = error?.response?.status;
      if (status === 401) {
        setMfaError('Invalid code. Please check your authenticator app and try again.');
        setMfaCode('');
      } else if (status === 429) {
        setMfaError('Too many attempts. Please wait a moment.');
      } else {
        setMfaError('Something went wrong. Please try again.');
      }
    } finally {
      setMfaLoading(false);
    }
  };

  // ── MFA challenge step ─────────────────────────────────────────────────────
  if (mfaToken) {
    return (
      <Container maxW="md" py={20}>
        <VStack spacing={8}>
          <VStack spacing={2}>
            <Heading size="2xl">Nest Egg</Heading>
            <Text color="gray.600">Your personal finance tracker</Text>
          </VStack>

          <Box w="full" bg="white" p={8} borderRadius="lg" boxShadow="md">
            <VStack spacing={6}>
              <Heading size="lg">Two-Factor Authentication</Heading>
              <Text color="gray.600" textAlign="center" fontSize="sm">
                Enter the 6-digit code from your authenticator app.
              </Text>

              <HStack justify="center">
                <PinInput
                  value={mfaCode}
                  onChange={setMfaCode}
                  onComplete={handleMfaVerify}
                  otp
                  size="lg"
                >
                  {[0, 1, 2, 3, 4, 5].map((i) => (
                    <PinInputField key={i} />
                  ))}
                </PinInput>
              </HStack>

              {mfaError && (
                <Alert status="error" borderRadius="md">
                  <AlertIcon />
                  {mfaError}
                </Alert>
              )}

              <Button
                colorScheme="brand"
                size="lg"
                w="full"
                isLoading={mfaLoading}
                isDisabled={mfaCode.length < 6}
                onClick={handleMfaVerify}
              >
                Verify
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setMfaToken(null); setMfaCode(''); setMfaError(null); }}
              >
                Back to login
              </Button>
            </VStack>
          </Box>
        </VStack>
      </Container>
    );
  }

  // ── Normal login step ──────────────────────────────────────────────────────
  return (
    <Container maxW="md" py={20}>
      <VStack spacing={8}>
        <VStack spacing={2}>
          <Heading size="2xl">Nest Egg</Heading>
          <Text color="gray.600">Your personal finance tracker</Text>
        </VStack>

        <Box
          w="full"
          bg="white"
          p={8}
          borderRadius="lg"
          boxShadow="md"
        >
          <VStack spacing={6}>
            <Heading size="lg">Login</Heading>

            <form onSubmit={handleSubmit(onSubmit)} style={{ width: '100%' }} autoComplete="on">
              <Stack spacing={4}>
                <FormControl isInvalid={!!errors.email}>
                  <FormLabel>Email</FormLabel>
                  <Input
                    type="email"
                    placeholder="you@example.com"
                    autoComplete="email"
                    autoFocus
                    {...register('email')}
                  />
                  <FormErrorMessage>{errors.email?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.password}>
                  <HStack justify="space-between" mb={1}>
                    <FormLabel mb={0}>Password</FormLabel>
                    <ChakraLink
                      as={Link}
                      to="/forgot-password"
                      fontSize="sm"
                      color="brand.500"
                    >
                      Forgot password?
                    </ChakraLink>
                  </HStack>
                  <Input
                    type="password"
                    placeholder="Enter your password"
                    autoComplete="current-password"
                    {...register('password')}
                  />
                  <FormErrorMessage>{errors.password?.message}</FormErrorMessage>
                </FormControl>

                {credentialError && (
                  <Alert status="error" borderRadius="md">
                    <AlertIcon />
                    {credentialError}
                  </Alert>
                )}

                <HStack justify="space-between">
                  <Checkbox
                    isChecked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  >
                    Remember me
                  </Checkbox>
                </HStack>

                <Button
                  type="submit"
                  colorScheme="brand"
                  size="lg"
                  w="full"
                  isLoading={isSubmitting || loginMutation.isPending}
                >
                  Login
                </Button>
              </Stack>
            </form>

            <Text color="gray.600">
              Don't have an account?{' '}
              <ChakraLink as={Link} to="/register" color="brand.500" fontWeight="semibold">
                Register
              </ChakraLink>
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Container>
  );
};
