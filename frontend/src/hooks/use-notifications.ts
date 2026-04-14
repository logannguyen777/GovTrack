import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { NotificationResponse } from "@/lib/types";

// ---- Query key factory ----
export const notificationKeys = {
  all: ["notifications"] as const,
  list: (unreadOnly?: boolean) =>
    [...notificationKeys.all, { unreadOnly }] as const,
};

// ---- Hooks ----

/**
 * Fetch notifications for the authenticated user.
 *
 * @param unreadOnly - When true, returns only unread notifications
 */
export function useNotifications(unreadOnly?: boolean) {
  const params: Record<string, string> = {};
  if (unreadOnly !== undefined) params.unread_only = String(unreadOnly);

  return useQuery<NotificationResponse[]>({
    queryKey: notificationKeys.list(unreadOnly),
    queryFn: () =>
      apiClient.get<NotificationResponse[]>("/api/notifications", params),
  });
}

/**
 * Mark a single notification as read.
 * Optimistically invalidates the notifications cache on success.
 */
export function useMarkNotificationRead() {
  const queryClient = useQueryClient();

  return useMutation<NotificationResponse, Error, string>({
    mutationFn: (id) =>
      apiClient.patch<NotificationResponse>(`/api/notifications/${id}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}
