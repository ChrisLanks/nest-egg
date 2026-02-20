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
  Select,
  SimpleGrid,
  Stack,
  Text,
  Link as ChakraLink,
  useToast,
  VStack,
} from '@chakra-ui/react';

const getDaysInMonth = (year: number | undefined, month: number | undefined): number => {
  if (!month) return 31;
  // new Date(year, month, 0) gives last day of month (month is 1-indexed here)
  // Use a non-leap reference year when year is unknown so Feb shows 28
  const y = year ?? 2001;
  return new Date(y, month, 0).getDate();
};
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link } from 'react-router-dom';
import { useRegister } from '../hooks/useAuth';

const currentYear = new Date().getFullYear();

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string()
    .min(12, 'Password must be at least 12 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/\d/, 'Password must contain at least one number')
    .regex(/[!@#$%^&*(),.?":{}|<>_\-+=[\]\\;\/`~]/, 'Password must contain at least one special character'),
  display_name: z.string().min(1, 'Name is required'),
  birth_day: z.number().int().min(1).max(31).optional(),
  birth_month: z.number().int().min(1).max(12).optional(),
  birth_year: z
    .number()
    .int()
    .min(1900, 'Enter a valid year')
    .max(currentYear, 'Enter a valid year')
    .optional(),
}).refine(
  (data) => {
    const set = [data.birth_day, data.birth_month, data.birth_year].filter(Boolean).length;
    return set === 0 || set === 3;
  },
  { message: 'Provide day, month, and year — or leave all blank', path: ['birth_year'] }
);

type RegisterFormData = z.infer<typeof registerSchema>;

export const RegisterPage = () => {
  const toast = useToast();
  const registerMutation = useRegister();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const watchedMonth = watch('birth_month');
  const watchedYear = watch('birth_year');
  const maxDay = getDaysInMonth(watchedYear, watchedMonth);

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
      const detail = error?.response?.data?.detail;
      let description = 'An error occurred';
      if (typeof detail === 'string') {
        description = detail;
      } else if (detail && typeof detail === 'object') {
        if (detail.message && Array.isArray(detail.errors) && detail.errors.length > 0) {
          description = `${detail.message}: ${detail.errors.join('; ')}`;
        } else if (detail.message) {
          description = detail.message;
        } else if (detail.error) {
          description = detail.error;
        }
      }
      toast({
        title: 'Registration failed',
        description,
        status: 'error',
        duration: 7000,
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
                    placeholder="At least 12 characters"
                    {...register('password')}
                  />
                  <FormHelperText>
                    12+ characters with uppercase, lowercase, number, and special character.
                  </FormHelperText>
                  <FormErrorMessage>{errors.password?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.display_name}>
                  <FormLabel>Name</FormLabel>
                  <Input placeholder="How you'd like to appear" {...register('display_name')} />
                  <FormErrorMessage>{errors.display_name?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!errors.birth_year || !!errors.birth_month || !!errors.birth_day}>
                  <FormLabel>Birthday <Text as="span" color="gray.400" fontWeight="normal">(optional)</Text></FormLabel>
                  <SimpleGrid columns={3} spacing={2}>
                    <Select
                      placeholder="Month"
                      onChange={(e) => {
                        const month = e.target.value ? parseInt(e.target.value) : undefined;
                        setValue('birth_month', month, { shouldValidate: true });
                        // Clear day if it's now out of range for the new month
                        const currentDay = watch('birth_day');
                        if (currentDay && month && currentDay > getDaysInMonth(watchedYear, month)) {
                          setValue('birth_day', undefined, { shouldValidate: true });
                        }
                      }}
                    >
                      {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].map((m, i) => (
                        <option key={i + 1} value={i + 1}>{m}</option>
                      ))}
                    </Select>
                    <Select
                      placeholder="Day"
                      onChange={(e) =>
                        setValue('birth_day', e.target.value ? parseInt(e.target.value) : undefined, { shouldValidate: true })
                      }
                    >
                      {Array.from({ length: maxDay }, (_, i) => (
                        <option key={i + 1} value={i + 1}>{i + 1}</option>
                      ))}
                    </Select>
                    <NumberInput
                      min={1900}
                      max={currentYear}
                      onChange={(_, value) => {
                        const year = isNaN(value) ? undefined : value;
                        setValue('birth_year', year, { shouldValidate: true });
                        // Clear day if Feb 29 becomes invalid (non-leap year)
                        const currentDay = watch('birth_day');
                        if (currentDay && watchedMonth && currentDay > getDaysInMonth(year, watchedMonth)) {
                          setValue('birth_day', undefined, { shouldValidate: true });
                        }
                      }}
                    >
                      <NumberInputField placeholder="Year" />
                    </NumberInput>
                  </SimpleGrid>
                  <FormHelperText>Used for retirement planning — can be set later in preferences.</FormHelperText>
                  <FormErrorMessage>{errors.birth_year?.message || errors.birth_month?.message || errors.birth_day?.message}</FormErrorMessage>
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
