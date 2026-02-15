/**
 * User View Toggle Component
 *
 * Button group to switch between Combined, Self, and other household members.
 * Replaces the dropdown selector with a more prominent toggle UI.
 */

import { ButtonGroup, Button, HStack, Text, Spinner } from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useUserView } from '../contexts/UserViewContext';
import api from '../services/api';

interface HouseholdMember {
  id: string;
  email: string;
  display_name?: string;
  first_name?: string;
  last_name?: string;
  is_org_admin: boolean;
  is_primary_household_member: boolean;
}

export const UserViewToggle = () => {
  const { user } = useAuthStore();
  const { selectedUserId, setSelectedUserId, isCombinedView, isSelfView } = useUserView();

  // Fetch household members
  const { data: members, isLoading } = useQuery<HouseholdMember[]>({
    queryKey: ['household-members'],
    queryFn: async () => {
      const response = await api.get('/household/members');
      return response.data;
    },
  });

  // Don't show toggle if only one member
  if (!isLoading && members && members.length <= 1) {
    return null;
  }

  if (isLoading) {
    return <Spinner size="sm" />;
  }

  // Format display name for a member
  const getDisplayName = (member: HouseholdMember): string => {
    // For current user, always show "Self"
    if (member.id === user?.id) {
      return 'Self';
    }

    // For others, use their name
    if (member.display_name) return member.display_name;
    if (member.first_name && member.last_name) {
      return `${member.first_name} ${member.last_name}`;
    }
    if (member.first_name) return member.first_name;
    return member.email.split('@')[0];
  };

  // Find other members (not current user)
  const otherMembers = members?.filter(m => m.id !== user?.id) || [];

  return (
    <HStack spacing={3} align="center">
      <Text fontSize="sm" fontWeight="medium" color="gray.600">
        View:
      </Text>
      <ButtonGroup size="sm" isAttached variant="outline">
        {/* Combined Button */}
        <Button
          onClick={() => setSelectedUserId(null)}
          colorScheme={isCombinedView ? 'brand' : 'gray'}
          variant={isCombinedView ? 'solid' : 'outline'}
          fontWeight={isCombinedView ? 'semibold' : 'normal'}
        >
          Combined
        </Button>

        {/* Self Button */}
        <Button
          onClick={() => setSelectedUserId(user?.id || null)}
          colorScheme={isSelfView ? 'brand' : 'gray'}
          variant={isSelfView ? 'solid' : 'outline'}
          fontWeight={isSelfView ? 'semibold' : 'normal'}
        >
          Self
        </Button>

        {/* Other Members Buttons */}
        {otherMembers.map((member) => {
          const isSelected = selectedUserId === member.id;
          return (
            <Button
              key={member.id}
              onClick={() => setSelectedUserId(member.id)}
              colorScheme={isSelected ? 'brand' : 'gray'}
              variant={isSelected ? 'solid' : 'outline'}
              fontWeight={isSelected ? 'semibold' : 'normal'}
            >
              {getDisplayName(member)}
            </Button>
          );
        })}
      </ButtonGroup>
    </HStack>
  );
};
