/**
 * Notification bell icon with unread count badge
 */

import {
  IconButton,
  Badge,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverHeader,
  PopoverBody,
  PopoverFooter,
  VStack,
  Text,
  Button,
  Box,
  HStack,
  useToast,
} from "@chakra-ui/react";
import { BellIcon } from "@chakra-ui/icons";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../../../api/notifications";
import NotificationItem from "./NotificationItem";

export default function NotificationBell() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [showAll, setShowAll] = useState(false);

  // Get unread count — poll every 2 min, pause when tab not focused,
  // refresh instantly when popover opens
  const { data: unreadCount } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: notificationsApi.getUnreadCount,
    refetchInterval: 120_000,
    refetchIntervalInBackground: false,
  });

  // Get notifications — recent unread by default, all when expanded
  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ["notifications", showAll ? "all" : "recent"],
    queryFn: () =>
      notificationsApi.getNotifications(
        showAll ? { include_read: true } : { include_read: false, limit: 10 },
      ),
    refetchInterval: 120_000,
    refetchIntervalInBackground: false,
  });

  const onPopoverOpen = () => {
    setShowAll(false);
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  };

  // Mark all as read mutation
  const markAllReadMutation = useMutation({
    mutationFn: notificationsApi.markAllAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast({
        title: "All notifications marked as read",
        status: "success",
        duration: 2000,
      });
    },
  });

  const hasUnread = (unreadCount?.count ?? 0) > 0;

  return (
    <Popover placement="bottom-end" onOpen={onPopoverOpen}>
      <PopoverTrigger>
        <IconButton
          aria-label="Notifications"
          icon={
            <Box position="relative" display="inline-flex">
              <BellIcon boxSize={5} />
              {hasUnread && (
                <Badge
                  colorScheme="red"
                  variant="solid"
                  fontSize="2xs"
                  position="absolute"
                  top="-2"
                  right="-2"
                  borderRadius="full"
                  minW="16px"
                  h="16px"
                  display="flex"
                  alignItems="center"
                  justifyContent="center"
                  px={0}
                >
                  {(unreadCount?.count ?? 0) > 99 ? "99+" : unreadCount?.count}
                </Badge>
              )}
            </Box>
          }
          variant="ghost"
        />
      </PopoverTrigger>

      <PopoverContent width="400px" maxH="600px" overflowY="auto">
        <PopoverHeader>
          <HStack justify="space-between">
            <Text fontWeight="bold">Notifications</Text>
            {hasUnread && (
              <Button
                size="xs"
                variant="ghost"
                onClick={() => markAllReadMutation.mutate()}
                isLoading={markAllReadMutation.isPending}
              >
                Mark all read
              </Button>
            )}
          </HStack>
        </PopoverHeader>

        <PopoverBody p={0}>
          {isLoading ? (
            <Box p={4}>
              <Text color="text.muted">Loading...</Text>
            </Box>
          ) : notifications.length === 0 ? (
            <Box p={4} textAlign="center">
              <Text color="text.muted">No notifications</Text>
            </Box>
          ) : (
            <VStack spacing={0} align="stretch">
              {notifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                />
              ))}
            </VStack>
          )}
        </PopoverBody>

        {!showAll && notifications.length > 0 && (
          <PopoverFooter>
            <Button
              size="sm"
              variant="ghost"
              width="full"
              onClick={() => setShowAll(true)}
            >
              View all notifications
            </Button>
          </PopoverFooter>
        )}
      </PopoverContent>
    </Popover>
  );
}
