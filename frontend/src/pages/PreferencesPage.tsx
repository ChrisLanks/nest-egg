import { useState } from 'react';
import {
  Box,
  Button,
  Container,
  Divider,
  FormControl,
  FormLabel,
  Heading,
  Input,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Stack,
  Text,
  useToast,
  VStack,
  HStack,
  FormHelperText,
} from '@chakra-ui/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

interface UserProfile {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  birth_year: number | null;
  is_org_admin: boolean;
}

interface UpdateProfileData {
  first_name?: string;
  last_name?: string;
  display_name?: string;
  email?: string;
  birth_year?: number | null;
}

interface ChangePasswordData {
  current_password: string;
  new_password: string;
}

export default function PreferencesPage() {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Note: Preferences are always for the current logged-in user,
  // not the selected user view. This page shows YOUR settings.

  // Profile state
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [birthYear, setBirthYear] = useState<number | null>(null);

  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Fetch user profile
  const { isLoading: profileLoading } = useQuery<UserProfile>({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const response = await api.get('/settings/profile');
      const data = response.data;
      setFirstName(data.first_name || '');
      setLastName(data.last_name || '');
      setDisplayName(data.display_name || '');
      setEmail(data.email || '');
      setBirthYear(data.birth_year || null);
      return data;
    },
  });

  // Update profile mutation
  const updateProfileMutation = useMutation({
    mutationFn: async (data: UpdateProfileData) => {
      const response = await api.patch('/settings/profile', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userProfile'] });
      toast({
        title: 'Profile updated',
        status: 'success',
        duration: 3000,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update profile',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Change password mutation
  const changePasswordMutation = useMutation({
    mutationFn: async (data: ChangePasswordData) => {
      const response = await api.post('/settings/profile/change-password', data);
      return response.data;
    },
    onSuccess: () => {
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      toast({
        title: 'Password changed successfully',
        status: 'success',
        duration: 3000,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to change password',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleUpdateProfile = () => {
    updateProfileMutation.mutate({
      first_name: firstName,
      last_name: lastName,
      display_name: displayName,
      email: email,
      birth_year: birthYear,
    });
  };

  const handleChangePassword = () => {
    if (newPassword !== confirmPassword) {
      toast({
        title: 'Passwords do not match',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    if (newPassword.length < 8) {
      toast({
        title: 'Password must be at least 8 characters',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    changePasswordMutation.mutate({
      current_password: currentPassword,
      new_password: newPassword,
    });
  };

  if (profileLoading) {
    return (
      <Container maxW="container.lg" py={8}>
        <Text>Loading...</Text>
      </Container>
    );
  }

  return (
    <Container maxW="container.lg" py={8}>
      <VStack spacing={8} align="stretch">
        <Heading size="lg">Settings</Heading>

        {/* User Profile Section */}
        <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
          <Heading size="md" mb={4}>
            User Profile
          </Heading>
          <Stack spacing={4}>
            <HStack spacing={4}>
              <FormControl>
                <FormLabel>First Name</FormLabel>
                <Input
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="First name"
                />
              </FormControl>
              <FormControl>
                <FormLabel>Last Name</FormLabel>
                <Input
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Last name"
                />
              </FormControl>
            </HStack>

            <FormControl>
              <FormLabel>Display Name</FormLabel>
              <Input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Display name (optional)"
              />
              <FormHelperText>
                This name will be displayed throughout the app
              </FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel>Email</FormLabel>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Birth Year</FormLabel>
              <NumberInput
                value={birthYear || ''}
                onChange={(_, value) => setBirthYear(isNaN(value) ? null : value)}
                min={1900}
                max={new Date().getFullYear()}
              >
                <NumberInputField placeholder="e.g., 1980" />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
              <FormHelperText>
                Used for RMD (Required Minimum Distribution) calculations. Leave blank to hide RMD.
              </FormHelperText>
            </FormControl>

            <Button
              colorScheme="blue"
              onClick={handleUpdateProfile}
              isLoading={updateProfileMutation.isPending}
              alignSelf="flex-start"
            >
              Save Profile
            </Button>
          </Stack>
        </Box>

        {/* Change Password Section */}
        <Box bg="white" p={6} borderRadius="lg" boxShadow="sm">
          <Heading size="md" mb={4}>
            Change Password
          </Heading>
          <Stack spacing={4}>
            <FormControl>
              <FormLabel>Current Password</FormLabel>
              <Input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
              />
            </FormControl>

            <FormControl>
              <FormLabel>New Password</FormLabel>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
              />
              <FormHelperText>Must be at least 8 characters</FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel>Confirm New Password</FormLabel>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
              />
            </FormControl>

            <Button
              colorScheme="blue"
              onClick={handleChangePassword}
              isLoading={changePasswordMutation.isPending}
              alignSelf="flex-start"
            >
              Change Password
            </Button>
          </Stack>
        </Box>

      </VStack>
    </Container>
  );
}
