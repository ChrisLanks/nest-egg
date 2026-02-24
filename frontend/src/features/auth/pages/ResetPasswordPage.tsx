/**
 * Reset Password page — user sets a new password using a token from the reset email.
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
  VStack,
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { authApi } from '../services/authApi';

const schema = z
  .object({
    new_password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  });

type FormData = z.infer<typeof schema>;

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';

  const [success, setSuccess] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  // Redirect to login after successful reset
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => navigate('/login'), 2500);
      return () => clearTimeout(timer);
    }
  }, [success, navigate]);

  // No token in URL — show error immediately
  if (!token) {
    return (
      <Container maxW="md" py={20}>
        <Box w="full" bg="bg.surface" p={8} borderRadius="lg" boxShadow="md">
          <VStack spacing={4}>
            <Alert status="error" borderRadius="md">
              <AlertIcon />
              This password reset link is invalid or missing.
            </Alert>
            <ChakraLink as={Link} to="/forgot-password" color="brand.500" fontWeight="semibold">
              Request a new reset link
            </ChakraLink>
          </VStack>
        </Box>
      </Container>
    );
  }

  const onSubmit = async (data: FormData) => {
    setApiError(null);
    setIsLoading(true);
    try {
      await authApi.resetPassword(token, data.new_password);
      setSuccess(true);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      setApiError(
        typeof detail === 'string'
          ? detail
          : 'This link is invalid or has expired.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxW="md" py={20}>
      <VStack spacing={8}>
        <VStack spacing={2}>
          <Heading size="2xl">Nest Egg</Heading>
          <Text color="text.secondary">Your personal finance tracker</Text>
        </VStack>

        <Box w="full" bg="bg.surface" p={8} borderRadius="lg" boxShadow="md">
          <VStack spacing={6}>
            <Heading size="lg">Reset Password</Heading>

            {success ? (
              <VStack spacing={4} w="full">
                <Alert status="success" borderRadius="md">
                  <AlertIcon />
                  Password reset! Redirecting to login…
                </Alert>
              </VStack>
            ) : (
              <form onSubmit={handleSubmit(onSubmit)} style={{ width: '100%' }}>
                <Stack spacing={4}>
                  {apiError && (
                    <Alert status="error" borderRadius="md">
                      <AlertIcon />
                      {apiError}{' '}
                      <ChakraLink as={Link} to="/forgot-password" color="red.700" ml={1}>
                        Request a new link.
                      </ChakraLink>
                    </Alert>
                  )}

                  <FormControl isInvalid={!!errors.new_password}>
                    <FormLabel>New Password</FormLabel>
                    <Input
                      type="password"
                      placeholder="At least 8 characters"
                      autoComplete="new-password"
                      autoFocus
                      {...register('new_password')}
                    />
                    <FormErrorMessage>{errors.new_password?.message}</FormErrorMessage>
                  </FormControl>

                  <FormControl isInvalid={!!errors.confirm_password}>
                    <FormLabel>Confirm Password</FormLabel>
                    <Input
                      type="password"
                      placeholder="Repeat your new password"
                      autoComplete="new-password"
                      {...register('confirm_password')}
                    />
                    <FormErrorMessage>{errors.confirm_password?.message}</FormErrorMessage>
                  </FormControl>

                  <Button
                    type="submit"
                    colorScheme="brand"
                    size="lg"
                    w="full"
                    isLoading={isLoading}
                  >
                    Reset Password
                  </Button>

                  <ChakraLink
                    as={Link}
                    to="/login"
                    color="brand.500"
                    textAlign="center"
                    fontSize="sm"
                  >
                    Back to login
                  </ChakraLink>
                </Stack>
              </form>
            )}
          </VStack>
        </Box>
      </VStack>
    </Container>
  );
};
