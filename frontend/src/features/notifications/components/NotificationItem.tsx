/**
 * Individual notification item
 */

import {
  Box,
  HStack,
  VStack,
  Text,
  IconButton,
  Badge,
  useToast,
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { Notification } from '../../../types/notification';
import { NotificationPriority } from '../../../types/notification';
import { notificationsApi } from '../../../api/notifications';

interface NotificationItemProps {
  notification: Notification;
}

export default function NotificationItem({ notification }: NotificationItemProps) {
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Mark as read mutation
  const markReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAsRead(notification.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  // Dismiss mutation
  const dismissMutation = useMutation({
    mutationFn: () => notificationsApi.dismiss(notification.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast({
        title: 'Notification dismissed',
        status: 'success',
        duration: 2000,
      });
    },
  });

  const handleClick = () => {
    // Mark as read
    if (!notification.is_read) {
      markReadMutation.mutate();
    }

    // Navigate if action URL provided
    if (notification.action_url) {
      navigate(notification.action_url);
    }
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    dismissMutation.mutate();
  };

  const getPriorityColor = (priority: NotificationPriority) => {
    switch (priority) {
      case NotificationPriority.URGENT:
        return 'red';
      case NotificationPriority.HIGH:
        return 'orange';
      case NotificationPriority.MEDIUM:
        return 'blue';
      case NotificationPriority.LOW:
        return 'gray';
      default:
        return 'gray';
    }
  };

  return (
    <Box
      p={3}
      borderBottom="1px"
      borderColor="gray.200"
      bg={notification.is_read ? 'white' : 'blue.50'}
      _hover={{ bg: 'gray.50', cursor: 'pointer' }}
      onClick={handleClick}
      position="relative"
    >
      <HStack align="start" spacing={3}>
        <Badge
          colorScheme={getPriorityColor(notification.priority)}
          fontSize="xs"
          borderRadius="full"
          px={2}
        >
          {notification.priority}
        </Badge>

        <VStack align="start" spacing={1} flex={1}>
          <Text fontWeight={notification.is_read ? 'normal' : 'bold'} fontSize="sm">
            {notification.title}
          </Text>
          <Text fontSize="xs" color="gray.600">
            {notification.message}
          </Text>
          {notification.action_label && (
            <Text fontSize="xs" color="blue.600" fontWeight="medium">
              {notification.action_label} →
            </Text>
          )}
          <Text fontSize="xs" color="gray.400">
            {new Date(notification.created_at).toLocaleString()}
          </Text>
        </VStack>

        <IconButton
          aria-label="Dismiss"
          icon={<CloseIcon />}
          size="xs"
          variant="ghost"
          onClick={handleDismiss}
          isLoading={dismissMutation.isPending}
        />
      </HStack>
    </Box>
  );
}
