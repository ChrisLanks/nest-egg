/**
 * Permissions API — grant management for household data sharing.
 */

import api from '../../../services/api';

export type GrantAction = 'read' | 'create' | 'update' | 'delete';

export type ResourceType =
  | 'account'
  | 'transaction'
  | 'bill'
  | 'holding'
  | 'budget'
  | 'category'
  | 'rule'
  | 'savings_goal'
  | 'contribution'
  | 'recurring_transaction'
  | 'report'
  | 'org_settings'
  | 'retirement_scenario';

export interface PermissionGrant {
  id: string;
  organization_id: string;
  grantor_id: string;
  grantee_id: string;
  resource_type: ResourceType;
  resource_id: string | null;
  actions: GrantAction[];
  granted_at: string;
  expires_at: string | null;
  is_active: boolean;
  grantee_display_name?: string | null;
  grantor_display_name?: string | null;
}

export interface GrantAuditEntry {
  id: string;
  grant_id: string | null;
  action: 'created' | 'updated' | 'revoked';
  actor_id: string | null;
  grantor_id: string | null;
  grantee_id: string | null;
  resource_type: string | null;
  resource_id: string | null;
  actions_before: GrantAction[] | null;
  actions_after: GrantAction[] | null;
  ip_address: string | null;
  occurred_at: string;
}

export interface HouseholdMember {
  id: string;
  email: string;
  display_name: string | null;
  first_name: string | null;
  last_name: string | null;
}

export interface GrantCreatePayload {
  grantee_id: string;
  resource_type: ResourceType;
  resource_id?: string | null;
  actions: GrantAction[];
  expires_at?: string | null;
}

export interface GrantUpdatePayload {
  actions: GrantAction[];
  expires_at?: string | null;
}

export const permissionsApi = {
  listGiven: async (): Promise<PermissionGrant[]> => {
    const res = await api.get<PermissionGrant[]>('/permissions/given');
    return res.data;
  },

  listReceived: async (): Promise<PermissionGrant[]> => {
    const res = await api.get<PermissionGrant[]>('/permissions/received');
    return res.data;
  },

  listAudit: async (): Promise<GrantAuditEntry[]> => {
    const res = await api.get<GrantAuditEntry[]>('/permissions/audit');
    return res.data;
  },

  listMembers: async (): Promise<HouseholdMember[]> => {
    const res = await api.get<HouseholdMember[]>('/permissions/members');
    return res.data;
  },

  listResourceTypes: async (): Promise<string[]> => {
    const res = await api.get<string[]>('/permissions/resource-types');
    return res.data;
  },

  createGrant: async (payload: GrantCreatePayload): Promise<PermissionGrant> => {
    const res = await api.post<PermissionGrant>('/permissions/grants', payload);
    return res.data;
  },

  updateGrant: async (grantId: string, payload: GrantUpdatePayload): Promise<PermissionGrant> => {
    const res = await api.put<PermissionGrant>(`/permissions/grants/${grantId}`, payload);
    return res.data;
  },

  revokeGrant: async (grantId: string): Promise<void> => {
    await api.delete(`/permissions/grants/${grantId}`);
  },
};
