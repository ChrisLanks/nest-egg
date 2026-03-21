/**
 * Milestone celebration overlay with confetti animation.
 * Triggered when the user has unread MILESTONE notifications.
 */

import { useEffect, useCallback, useState } from "react";
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalBody,
  VStack,
  Text,
  Button,
  Box,
} from "@chakra-ui/react";
import confetti from "canvas-confetti";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../../../api/notifications";
import { NotificationType } from "../../../types/notification";
import type { Notification } from "../../../types/notification";
import { extractThreshold, getEmoji } from "../../../utils/milestoneUtils";

function fireConfetti() {
  const duration = 3000;
  const end = Date.now() + duration;

  const frame = () => {
    confetti({
      particleCount: 3,
      angle: 60,
      spread: 55,
      origin: { x: 0, y: 0.7 },
      colors: ["#FFD700", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"],
    });
    confetti({
      particleCount: 3,
      angle: 120,
      spread: 55,
      origin: { x: 1, y: 0.7 },
      colors: ["#FFD700", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"],
    });

    if (Date.now() < end) {
      requestAnimationFrame(frame);
    }
  };

  // Initial burst
  confetti({
    particleCount: 100,
    spread: 70,
    origin: { y: 0.6 },
    colors: ["#FFD700", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"],
  });

  frame();
}

export default function MilestoneCelebration() {
  const queryClient = useQueryClient();
  const [milestone, setMilestone] = useState<Notification | null>(null);
  // IDs of all milestone notifications we'll mark as read when dismissed
  const [allMilestoneIds, setAllMilestoneIds] = useState<string[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem("nest-egg-celebrated-milestones");
      return stored ? new Set(JSON.parse(stored)) : new Set();
    } catch {
      return new Set();
    }
  });

  // Fetch unread notifications — look for MILESTONE type
  const { data: notifications = [] } = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: () =>
      notificationsApi.getNotifications({ include_read: false, limit: 50 }),
    refetchInterval: 120_000,
    refetchIntervalInBackground: false,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  // Find ALL unread milestone notifications, show only the highest one
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (milestone) return; // already showing one

    const unreadMilestones = notifications.filter(
      (n) =>
        n.type === NotificationType.MILESTONE &&
        !n.is_read &&
        !dismissed.has(n.id),
    );

    if (unreadMilestones.length === 0) return;

    // Pick the highest threshold milestone to celebrate
    const highest = unreadMilestones.reduce((best, current) =>
      extractThreshold(current.title) > extractThreshold(best.title)
        ? current
        : best,
    );

    setMilestone(highest);
    setAllMilestoneIds(unreadMilestones.map((n) => n.id));
  }, [notifications, milestone, dismissed]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Fire confetti when milestone is shown
  useEffect(() => {
    if (milestone) {
      fireConfetti();
    }
  }, [milestone]);

  const handleDismiss = useCallback(() => {
    if (!milestone) return;

    // Mark ALL unread milestone notifications as read (not just the displayed one)
    for (const id of allMilestoneIds) {
      markReadMutation.mutate(id);
    }

    // Track all in localStorage so we don't celebrate them again
    const next = new Set(dismissed);
    for (const id of allMilestoneIds) {
      next.add(id);
    }
    setDismissed(next);
    try {
      localStorage.setItem(
        "nest-egg-celebrated-milestones",
        JSON.stringify([...next]),
      );
    } catch {
      // localStorage full — ignore
    }

    setMilestone(null);
    setAllMilestoneIds([]);
  }, [milestone, allMilestoneIds, dismissed, markReadMutation]);

  if (!milestone) return null;

  const emoji = getEmoji(milestone.title);

  return (
    <Modal isOpen onClose={handleDismiss} isCentered size="md">
      <ModalOverlay bg="blackAlpha.600" backdropFilter="blur(4px)" />
      <ModalContent bg="bg.surface" borderRadius="xl" overflow="hidden">
        <Box
          bgGradient="linear(to-br, yellow.400, orange.400, pink.400)"
          py={2}
        />
        <ModalBody py={8} px={6}>
          <VStack spacing={4} textAlign="center">
            <Text fontSize="6xl" lineHeight={1}>
              {emoji}
            </Text>
            <Text fontSize="2xl" fontWeight="bold">
              {milestone.title}
            </Text>
            <Text fontSize="md" color="text.secondary">
              {milestone.message}
            </Text>
            <Button
              colorScheme="yellow"
              size="lg"
              onClick={handleDismiss}
              mt={2}
            >
              Keep Going!
            </Button>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
