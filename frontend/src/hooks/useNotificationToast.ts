/**
 * useNotificationToast
 *
 * A drop-in replacement for Chakra's `useToast` that, in addition to showing
 * the ephemeral toast, persists the notification to the backend so it also
 * appears in the notification bell at the top of the page.
 *
 * Usage:
 *   const notificationToast = useNotificationToast();
 *
 *   notificationToast({
 *     title: "Goal completed!",
 *     description: "You hit your emergency fund target.",
 *     status: "success",
 *     notification: {
 *       type: NotificationType.GOAL_COMPLETED,
 *       priority: NotificationPriority.HIGH,
 *       action_url: "/goals",
 *       action_label: "View goals",
 *       expires_in_days: 30,
 *     },
 *   });
 *
 * The `notification` field is optional — omit it for transient toasts
 * (e.g. rate-limit warnings) that should NOT appear in the bell.
 *
 * The bell persist is fire-and-forget: a network failure silently logs a
 * warning and never breaks the toast or the calling component.
 */

import { useToast } from "@chakra-ui/react";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { notificationsApi } from "../api/notifications";
import type { NotificationCreate } from "../types/notification";

type UseToastOptions = Parameters<ReturnType<typeof useToast>>[0];

export interface NotificationToastOptions extends NonNullable<UseToastOptions> {
  /**
   * When provided the notification is also persisted to the backend and will
   * appear in the notification bell dropdown.  Omit for transient/error toasts
   * that should not clutter the bell (e.g. rate-limit, server errors).
   */
  notification?: Omit<NotificationCreate, "title" | "message"> & {
    /** Override the bell title; defaults to the toast `title`. */
    title?: string;
    /** Override the bell message; defaults to the toast `description`. */
    message?: string;
  };
}

export function useNotificationToast() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useCallback(
    (options: NotificationToastOptions) => {
      // Always show the Chakra toast first so the user gets instant feedback.
      toast(options);

      // Persist to backend if a notification descriptor was supplied.
      if (!options.notification) return;

      const { notification } = options;

      const payload: NotificationCreate = {
        type: notification.type,
        priority: notification.priority,
        title: notification.title ?? (typeof options.title === "string" ? options.title : "Notification"),
        message:
          notification.message ??
          (typeof options.description === "string"
            ? options.description
            : typeof options.title === "string"
              ? options.title
              : ""),
        action_url: notification.action_url,
        action_label: notification.action_label,
        related_entity_type: notification.related_entity_type,
        related_entity_id: notification.related_entity_id,
        expires_in_days: notification.expires_in_days ?? 30,
      };

      notificationsApi
        .createNotification(payload)
        .then(() => {
          // Refresh the bell badge so the new notification shows immediately.
          queryClient.invalidateQueries({ queryKey: ["notifications"] });
        })
        .catch((err) => {
          // Fire-and-forget: log but never surface this error to the user.
          console.warn("[useNotificationToast] Failed to persist notification to bell:", err);
        });
    },
    [toast, queryClient],
  );
}
