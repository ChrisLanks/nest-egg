/**
 * Guest access API client
 */

import api from "../services/api";

export interface GuestInvitation {
  id: string;
  email: string;
  role: "viewer" | "advisor";
  label: string | null;
  status: "pending" | "accepted" | "declined" | "expired";
  expires_at: string;
  created_at: string;
  join_url: string;
}

export interface GuestRecord {
  id: string;
  user_id: string;
  user_email: string;
  organization_id: string;
  role: "viewer" | "advisor";
  label: string | null;
  is_active: boolean;
  created_at: string;
  revoked_at: string | null;
  expires_at: string | null;
}

export interface InvitationPreview {
  organization_name: string;
  invited_by_email: string;
  role: "viewer" | "advisor";
  label: string | null;
  expires_at: string;
}

export const guestAccessApi = {
  /** Invite a user as guest (admin only) */
  invite: async (data: {
    email: string;
    role?: "viewer" | "advisor";
    label?: string;
    access_expires_days?: number;
  }): Promise<GuestInvitation> => {
    const { data: result } = await api.post<GuestInvitation>(
      "/guest-access/invite",
      data,
    );
    return result;
  },

  /** List active guests (admin only) */
  listGuests: async (): Promise<GuestRecord[]> => {
    const { data } = await api.get<GuestRecord[]>("/guest-access/guests");
    return data;
  },

  /** Revoke guest access (admin only) */
  revokeGuest: async (guestId: string): Promise<void> => {
    await api.delete(`/guest-access/guests/${guestId}`);
  },

  /** Update guest role/label (admin only) */
  updateGuest: async (
    guestId: string,
    data: { role?: "viewer" | "advisor"; label?: string },
  ): Promise<GuestRecord> => {
    const { data: result } = await api.patch<GuestRecord>(
      `/guest-access/guests/${guestId}`,
      data,
    );
    return result;
  },

  /** List pending invitations (admin only) */
  listInvitations: async (): Promise<GuestInvitation[]> => {
    const { data } = await api.get<GuestInvitation[]>(
      "/guest-access/invitations",
    );
    return data;
  },

  /** Cancel a pending invitation (admin only) */
  cancelInvitation: async (invitationId: string): Promise<void> => {
    await api.delete(`/guest-access/invitations/${invitationId}`);
  },

  /** Accept a guest invitation */
  acceptInvitation: async (code: string): Promise<{ detail: string }> => {
    const { data } = await api.post<{ detail: string }>(
      `/guest-access/accept/${code}`,
    );
    return data;
  },

  /** Decline a guest invitation */
  declineInvitation: async (code: string): Promise<{ detail: string }> => {
    const { data } = await api.post<{ detail: string }>(
      `/guest-access/decline/${code}`,
    );
    return data;
  },

  /** Leave a guest household */
  leaveHousehold: async (orgId: string): Promise<void> => {
    await api.delete(`/guest-access/leave/${orgId}`);
  },

  /** Preview an invitation (public) */
  previewInvitation: async (code: string): Promise<InvitationPreview> => {
    const { data } = await api.get<InvitationPreview>(
      `/guest-access/invitation/${code}`,
    );
    return data;
  },
};
