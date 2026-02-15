/**
 * Login page with autocomplete and remember me support
 */

import {
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
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link } from 'react-router-dom';
import { useLogin } from '../hooks/useAuth';
import { useState, useEffect } from 'react';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginPage = () => {
  const toast = useToast();
  const loginMutation = useLogin();
  const [rememberMe, setRememberMe] = useState(false);

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
    console.log('🔐 Login attempt started', { email: data.email });

    try {
      // Save or clear email based on remember me checkbox
      if (rememberMe) {
        localStorage.setItem('rememberedEmail', data.email);
      } else {
        localStorage.removeItem('rememberedEmail');
      }

      console.log('🔐 Calling login API...');
      const result = await loginMutation.mutateAsync(data);
      console.log('✅ Login successful', result);

      toast({
        title: 'Login successful',
        status: 'success',
        duration: 3000,
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Invalid credentials';
      console.error('❌ Login failed:', {
        error,
        message: errorMessage,
        status: error.response?.status,
        data: error.response?.data,
      });

      toast({
        title: 'Login failed',
        description: errorMessage,
        status: 'error',
        duration: 5000,
      });
    }
  };

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
                  <FormLabel>Password</FormLabel>
                  <Input
                    type="password"
                    placeholder="Enter your password"
                    autoComplete="current-password"
                    {...register('password')}
                  />
                  <FormErrorMessage>{errors.password?.message}</FormErrorMessage>
                </FormControl>

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
