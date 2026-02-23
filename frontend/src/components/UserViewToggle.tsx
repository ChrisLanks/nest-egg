/**
 * User View Toggle Component
 *
 * Dropdown to switch between Combined, Self, and other household members.
 * Provides a scalable UI for households with multiple users.
 */

import { Select, HStack, Text, Spinner } from '@chakra-ui/react';
import { useLocation } from 'react-router-dom';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useUserView } from '../contexts/UserViewContext';
import { useHouseholdMembers } from '../hooks/useHouseholdMembers';
import type { HouseholdMember } from '../hooks/useHouseholdMembers';

// Pages that always operate on the current user's own data
const SELF_ONLY_PATHS = ['/preferences', '/permissions', '/household'];

export const UserViewToggle = () => {
  const { user } = useAuthStore();
  const { selectedUserId, setSelectedUserId } = useUserView();
  const { pathname } = useLocation();
  const isSelfOnlyPage = SELF_ONLY_PATHS.includes(pathname);

  // Fetch household members
  const { data: members, isLoading } = useHouseholdMembers();

  // Don't show toggle if only one member
  if (!isLoading && members && members.length <= 1) {
    return null;
  }

  if (isLoading) {
    return <Spinner size="sm" />;
  }

  // Format display name for a member
  const getDisplayName = (member: HouseholdMember): string => {
    if (member.display_name) return member.display_name;
    if (member.first_name && member.last_name) {
      return `${member.first_name} ${member.last_name}`;
    }
    if (member.first_name) return member.first_name;
    return member.email.split('@')[0];
  };

  // Determine current selection value for the dropdown
  const getCurrentValue = (): string => {
    if (!selectedUserId) return 'combined';
    if (selectedUserId === user?.id) return 'self';
    return selectedUserId;
  };

  const handleChange = (value: string) => {
    if (value === 'combined') {
      setSelectedUserId(null);
    } else if (value === 'self') {
      setSelectedUserId(user?.id || null);
    } else {
      setSelectedUserId(value);
    }
  };

  return (
    <HStack spacing={2} align="center">
      <Text fontSize="sm" fontWeight="medium" color={isSelfOnlyPage ? 'gray.400' : 'gray.600'}>
        View:
      </Text>
      <Select
        value={isSelfOnlyPage ? 'self' : getCurrentValue()}
        onChange={(e) => handleChange(e.target.value)}
        size="sm"
        width="200px"
        bg="white"
        isDisabled={isSelfOnlyPage}
        opacity={isSelfOnlyPage ? 0.5 : 1}
      >
        <option value="combined">Combined Household</option>
        <option value="self">Self</option>
        {members?.filter(m => m.id !== user?.id).map((member) => (
          <option key={member.id} value={member.id}>
            {getDisplayName(member)}
          </option>
        ))}
      </Select>
    </HStack>
  );
};
