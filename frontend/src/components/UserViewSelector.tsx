/**
 * User View Selector Component
 *
 * Dropdown to switch between individual user views and combined household view.
 * Used on Investments, Cash Flow, and Dashboard pages for multi-user filtering.
 */

import { Select } from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
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

interface UserViewSelectorProps {
  /** Currently selected user ID (null = combined household view) */
  currentUserId: string | null;
  /** Callback when user selection changes */
  onUserChange: (userId: string | null) => void;
  /** Optional size prop for the select component */
  size?: 'sm' | 'md' | 'lg';
}

export const UserViewSelector: React.FC<UserViewSelectorProps> = ({
  currentUserId,
  onUserChange,
  size = 'md',
}) => {
  // Fetch household members
  const { data: members, isLoading } = useQuery<HouseholdMember[]>({
    queryKey: ['household-members'],
    queryFn: async () => {
      const response = await api.get('/household/members');
      return response.data;
    },
  });

  // Don't show selector if only one member (no need to filter)
  if (!isLoading && members && members.length <= 1) {
    return null;
  }

  // Format display name for a member
  const getDisplayName = (member: HouseholdMember): string => {
    if (member.display_name) return member.display_name;
    if (member.first_name && member.last_name) {
      return `${member.first_name} ${member.last_name}`;
    }
    if (member.first_name) return member.first_name;
    return member.email.split('@')[0]; // Use email username as fallback
  };

  return (
    <Select
      value={currentUserId || 'combined'}
      onChange={(e) => {
        const value = e.target.value;
        onUserChange(value === 'combined' ? null : value);
      }}
      size={size}
      maxWidth="250px"
      isDisabled={isLoading}
    >
      <option value="combined">Combined Household</option>
      {members?.map((member) => (
        <option key={member.id} value={member.id}>
          {getDisplayName(member)}
          {member.is_primary_household_member && ' (Primary)'}
        </option>
      ))}
    </Select>
  );
};
