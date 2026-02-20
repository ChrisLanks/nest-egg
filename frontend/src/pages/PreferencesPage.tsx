import { useState } from 'react';

const getDaysInMonth = (year: number | null, month: number | null): number => {
  if (!month) return 31;
  const y = year ?? 2001; // use non-leap reference year when year is unknown
  return new Date(y, month, 0).getDate();
};
import {
  Box,
  Button,
  Container,
  FormControl,
  FormLabel,
  Heading,
  Input,
  NumberInput,
  NumberInputField,
  Select,
  SimpleGrid,
  Stack,
  Text,
  useToast,
  VStack,
  FormHelperText,
} from '@chakra-ui/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

interface UpdateProfileData {
  display_name?: string;
  email?: string;
  birth_day?: number | null;
  birth_month?: number | null;
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

  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [birthDay, setBirthDay] = useState<number | null>(null);
  const [birthMonth, setBirthMonth] = useState<number | null>(null);
  const [birthYear, setBirthYear] = useState<number | null>(null);

  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Fetch user profile
  const { isLoading: profileLoading } = useQuery({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const response = await api.get('/settings/profile');
      const data = response.data;
      // display_name is primary; fall back to first+last for existing users
      setDisplayName(data.display_name || `${data.first_name || ''} ${data.last_name || ''}`.trim() || '');
      setEmail(data.email || '');
      setBirthDay(data.birth_day || null);
      setBirthMonth(data.birth_month || null);
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
      const detail = error.response?.data?.detail;
      let description = 'An error occurred';
      if (typeof detail === 'string') description = detail;
      else if (Array.isArray(detail)) description = detail[0]?.msg || 'Validation error';
      else if (detail?.message) description = detail.message;
      toast({ title: 'Failed to update profile', description, status: 'error', duration: 5000 });
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
      const detail = error.response?.data?.detail;
      let title = 'Failed to change password';
      let description: any = 'An error occurred';
      if (typeof detail === 'string') {
        description = detail;
      } else if (Array.isArray(detail)) {
        description = detail[0]?.msg || 'Validation error';
      } else if (detail && typeof detail === 'object') {
        const errors: string[] = Array.isArray(detail.errors) ? detail.errors : [];
        if (errors.length > 0) {
          // Password validation error: message is a human-readable title, errors are the reasons
          if (detail.message) title = detail.message;
          description = (
            <VStack align="start" spacing={1} mt={1}>
              {errors.map((msg: string, i: number) => (
                <Text key={i} fontSize="sm">• {msg}</Text>
              ))}
            </VStack>
          );
        } else {
          // Rate limit, auth errors, etc.: keep generic title, show message as description
          description = detail.message || detail.error || 'An error occurred';
        }
      }
      toast({ title, description, status: 'error', duration: 8000 });
    },
  });

  const handleUpdateProfile = () => {
    updateProfileMutation.mutate({
      display_name: displayName,
      email: email,
      birth_day: birthDay,
      birth_month: birthMonth,
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

    if (newPassword.length < 12) {
      toast({
        title: 'Password must be at least 12 characters',
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
            <FormControl>
              <FormLabel>Name</FormLabel>
              <Input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="How you'd like to appear"
              />
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
              <FormLabel>Birthday</FormLabel>
              <SimpleGrid columns={3} spacing={2}>
                <Select
                  placeholder="Month"
                  value={birthMonth || ''}
                  onChange={(e) => {
                    const month = e.target.value ? parseInt(e.target.value) : null;
                    setBirthMonth(month);
                    // Clear day if it's now out of range for the new month
                    if (birthDay && month && birthDay > getDaysInMonth(birthYear, month)) {
                      setBirthDay(null);
                    }
                  }}
                >
                  {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].map((m, i) => (
                    <option key={i + 1} value={i + 1}>{m}</option>
                  ))}
                </Select>
                <Select
                  placeholder="Day"
                  value={birthDay || ''}
                  onChange={(e) => setBirthDay(e.target.value ? parseInt(e.target.value) : null)}
                >
                  {Array.from({ length: getDaysInMonth(birthYear, birthMonth) }, (_, i) => (
                    <option key={i + 1} value={i + 1}>{i + 1}</option>
                  ))}
                </Select>
                <NumberInput
                  value={birthYear || ''}
                  onChange={(_, value) => {
                    const year = isNaN(value) ? null : value;
                    setBirthYear(year);
                    // Clear day if Feb 29 becomes invalid (non-leap year)
                    if (birthDay && birthMonth && birthDay > getDaysInMonth(year, birthMonth)) {
                      setBirthDay(null);
                    }
                  }}
                  min={1900}
                  max={new Date().getFullYear()}
                >
                  <NumberInputField placeholder="Year" />
                </NumberInput>
              </SimpleGrid>
              <FormHelperText>
                Used for retirement planning (59½ rule, RMDs). Leave all blank to hide.
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
              <FormHelperText>Must be at least 12 characters</FormHelperText>
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
