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
  FormHelperText,
  Heading,
  Input,
  NumberInput,
  NumberInputField,
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

const currentYear = new Date().getFullYear();

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  display_name: z.string().min(1, 'Name is required'),
  birth_year: z
    .number()
    .int()
    .min(1900, 'Enter a valid year')
    .max(currentYear, 'Enter a valid year')
    .optional(),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export const RegisterPage = () => {
  const toast = useToast();
  const registerMutation = useRegister();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    // Strip undefined optional fields so they're omitted from the request body
    const payload = Object.fromEntries(
      Object.entries(data).filter(([, v]) => v !== undefined)
    ) as RegisterFormData;
    try {
      await registerMutation.mutateAsync(payload);
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

                <FormControl isInvalid={!!errors.display_name}>
                  <FormLabel>Name</FormLabel>
                  <Input placeholder="How you'd like to appear" {...register('display_name')} />
                  <FormErrorMessage>{errors.display_name?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.birth_year}>
                  <FormLabel>Birth Year <Text as="span" color="gray.400" fontWeight="normal">(optional)</Text></FormLabel>
                  <NumberInput
                    min={1900}
                    max={currentYear}
                    onChange={(_, value) =>
                      setValue('birth_year', isNaN(value) ? undefined : value, { shouldValidate: true })
                    }
                  >
                    <NumberInputField placeholder="e.g. 1985" />
                  </NumberInput>
                  <FormHelperText>Used for RMD calculations — can be set later in preferences.</FormHelperText>
                  <FormErrorMessage>{errors.birth_year?.message}</FormErrorMessage>
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
