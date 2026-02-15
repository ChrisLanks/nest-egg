/**
 * Notifications API client
 */

import api from '../services/api';
import type { Notification, UnreadCountResponse } from '../types/notification';

export const notificationsApi = {
  /**
   * Get all notifications for current user
   */
  getNotifications: async (params?: {
    include_read?: boolean;
    limit?: number;
  }): Promise<Notification[]> => {
    const { data } = await api.get<Notification[]>('/notifications/', { params });
    return data;
  },

  /**
   * Get unread notification count
   */
  getUnreadCount: async (): Promise<UnreadCountResponse> => {
    const { data } = await api.get<UnreadCountResponse>('/notifications/unread-count');
    return data;
  },

  /**
   * Mark notification as read
   */
  markAsRead: async (notificationId: string): Promise<Notification> => {
    const { data } = await api.patch<Notification>(`/notifications/${notificationId}/read`);
    return data;
  },

  /**
   * Dismiss notification
   */
  dismiss: async (notificationId: string): Promise<Notification> => {
    const { data } = await api.patch<Notification>(`/notifications/${notificationId}/dismiss`);
    return data;
  },

  /**
   * Mark all notifications as read
   */
  markAllAsRead: async (): Promise<{ marked_read: number }> => {
    const { data } = await api.post<{ marked_read: number }>('/notifications/mark-all-read');
    return data;
  },
};
