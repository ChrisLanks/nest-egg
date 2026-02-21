/**
 * Forgot Password page — user enters their email to receive a reset link.
 * Always shows a success message after submission (prevents email enumeration).
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
import { Link } from 'react-router-dom';
import { useState } from 'react';
import { authApi } from '../services/authApi';

const schema = z.object({
  email: z.string().email('Please enter a valid email address'),
});

type FormData = z.infer<typeof schema>;

export const ForgotPasswordPage = () => {
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setIsLoading(true);
    try {
      await authApi.forgotPassword(data.email);
    } catch {
      // Silently ignore errors — always show success to prevent enumeration
    } finally {
      setIsLoading(false);
      setSubmitted(true);
    }
  };

  return (
    <Container maxW="md" py={20}>
      <VStack spacing={8}>
        <VStack spacing={2}>
          <Heading size="2xl">Nest Egg</Heading>
          <Text color="gray.600">Your personal finance tracker</Text>
        </VStack>

        <Box w="full" bg="white" p={8} borderRadius="lg" boxShadow="md">
          <VStack spacing={6}>
            <Heading size="lg">Forgot Password</Heading>

            {submitted ? (
              <VStack spacing={4} w="full">
                <Alert status="success" borderRadius="md">
                  <AlertIcon />
                  If that email is registered, a password reset link has been sent. Check your inbox.
                </Alert>
                <Text fontSize="sm" color="gray.500">
                  Didn't receive an email? Check your spam folder or{' '}
                  <ChakraLink
                    color="brand.500"
                    cursor="pointer"
                    onClick={() => setSubmitted(false)}
                  >
                    try again
                  </ChakraLink>
                  .
                </Text>
                <ChakraLink as={Link} to="/login" color="brand.500" fontWeight="semibold">
                  Back to login
                </ChakraLink>
              </VStack>
            ) : (
              <form onSubmit={handleSubmit(onSubmit)} style={{ width: '100%' }}>
                <Stack spacing={4}>
                  <Text color="gray.600" fontSize="sm">
                    Enter your email address and we'll send you a link to reset your password.
                  </Text>

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

                  <Button
                    type="submit"
                    colorScheme="brand"
                    size="lg"
                    w="full"
                    isLoading={isLoading}
                  >
                    Send Reset Link
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
