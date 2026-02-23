/**
 * Shared hook for fetching household members.
 * Single definition ensures the query key is consistent and React Query
 * deduplicates the request wherever the hook is called.
 */

import { useQuery } from '@tanstack/react-query';
import api from '../services/api';

export interface HouseholdMember {
  id: string;
  email: string;
  display_name?: string;
  first_name?: string;
  last_name?: string;
  is_org_admin: boolean;
  is_primary_household_member: boolean;
}

export const HOUSEHOLD_MEMBERS_QUERY_KEY = ['household-members'] as const;

export const useHouseholdMembers = () =>
  useQuery<HouseholdMember[]>({
    queryKey: HOUSEHOLD_MEMBERS_QUERY_KEY,
    queryFn: async () => {
      const response = await api.get('/household/members');
      return response.data as HouseholdMember[];
    },
  });
