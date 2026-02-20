/**
 * Register page
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
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link } from 'react-router-dom';
import { useRegister } from '../hooks/useAuth';

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().optional(),
  display_name: z.string().optional(),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export const RegisterPage = () => {
  const toast = useToast();
  const registerMutation = useRegister();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      await registerMutation.mutateAsync(data);
      toast({
        title: 'Registration successful',
        description: 'Welcome to Nest Egg!',
        status: 'success',
        duration: 3000,
      });
    } catch (error: any) {
      toast({
        title: 'Registration failed',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    }
  };

  return (
    <Container maxW="md" py={12}>
      <VStack spacing={8}>
        <VStack spacing={2}>
          <Heading size="2xl">Nest Egg</Heading>
          <Text color="gray.600">Create your account</Text>
        </VStack>

        <Box w="full" bg="white" p={8} borderRadius="lg" boxShadow="md">
          <VStack spacing={6}>
            <Heading size="lg">Register</Heading>

            <form onSubmit={handleSubmit(onSubmit)} style={{ width: '100%' }}>
              <Stack spacing={4}>
                <FormControl isInvalid={!!errors.email}>
                  <FormLabel>Email</FormLabel>
                  <Input
                    type="email"
                    placeholder="you@example.com"
                    {...register('email')}
                  />
                  <FormErrorMessage>{errors.email?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.password}>
                  <FormLabel>Password</FormLabel>
                  <Input
                    type="password"
                    placeholder="At least 8 characters"
                    {...register('password')}
                  />
                  <FormErrorMessage>{errors.password?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.first_name}>
                  <FormLabel>First Name</FormLabel>
                  <Input placeholder="John" {...register('first_name')} />
                  <FormErrorMessage>{errors.first_name?.message}</FormErrorMessage>
                </FormControl>

                <FormControl>
                  <FormLabel>Last Name <Text as="span" color="gray.400" fontSize="sm">(optional)</Text></FormLabel>
                  <Input placeholder="Doe" {...register('last_name')} />
                </FormControl>

                <FormControl>
                  <FormLabel>Display Name <Text as="span" color="gray.400" fontSize="sm">(optional)</Text></FormLabel>
                  <Input placeholder="How you'd like to appear" {...register('display_name')} />
                </FormControl>

                <Button
                  type="submit"
                  colorScheme="brand"
                  size="lg"
                  w="full"
                  isLoading={isSubmitting || registerMutation.isPending}
                >
                  Create Account
                </Button>
              </Stack>
            </form>

            <Text color="gray.600">
              Already have an account?{' '}
              <ChakraLink as={Link} to="/login" color="brand.500" fontWeight="semibold">
                Login
              </ChakraLink>
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Container>
  );
};
