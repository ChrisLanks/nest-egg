/**
 * Dashboard page — thin shell that delegates to the customizable widget grid.
 *
 * All chart/data logic lives in individual widget components under
 * src/features/dashboard/widgets/. Layout persistence is handled by
 * the useWidgetLayout hook.
 */

import {
  Box,
  Button,
  Container,
  Heading,
  HStack,
  Text,
  Tooltip,
  useDisclosure,
  useToast,
} from "@chakra-ui/react";
import { AddIcon, EditIcon, RepeatIcon } from "@chakra-ui/icons";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useAuthStore } from "../features/auth/stores/authStore";
import { DashboardGrid } from "../features/dashboard/DashboardGrid";
import { AddWidgetDrawer } from "../features/dashboard/AddWidgetDrawer";
import { useWidgetLayout } from "../features/dashboard/useWidgetLayout";
import { WIDGET_REGISTRY } from "../features/dashboard/widgetRegistry";
import type { LayoutItem } from "../features/dashboard/types";

export const DashboardPage = () => {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const {
    layout,
    isEditing,
    isSaving,
    startEditing,
    saveLayout,
    cancelEditing,
    setPendingLayout,
  } = useWidgetLayout();
  const { isOpen, onOpen, onClose } = useDisclosure();

  const handleAddWidget = (widgetId: string) => {
    const def = WIDGET_REGISTRY[widgetId];
    if (!def) return;
    const newItem: LayoutItem = { id: widgetId, span: def.defaultSpan };
    setPendingLayout([...layout, newItem]);
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      // Invalidate all dashboard-related queries to force a fresh fetch on every widget
      await queryClient.invalidateQueries({ predicate: () => true });
      toast({
        title: "Dashboard refreshed",
        status: "success",
        duration: 2000,
        isClosable: true,
        position: "bottom-right",
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <Container maxW="container.xl" py={8}>
      <HStack justify="space-between" mb={8} align="start">
        <Box>
          <Heading size="lg">
            Welcome back,{" "}
            {user?.display_name ||
              user?.first_name ||
              user?.email?.split("@")[0] ||
              "User"}
            !
          </Heading>
          <Text color="text.secondary" mt={1}>
            Here's your financial overview
          </Text>
        </Box>

        {!isEditing ? (
          <HStack flexShrink={0} spacing={2}>
            <Tooltip
              label="Force-refresh all widget data, bypassing the cache"
              hasArrow
            >
              <Button
                leftIcon={<RepeatIcon />}
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                isLoading={isRefreshing}
                loadingText="Refreshing…"
              >
                Refresh
              </Button>
            </Tooltip>
            <Button
              leftIcon={<EditIcon />}
              variant="ghost"
              size="sm"
              onClick={startEditing}
            >
              Customize
            </Button>
          </HStack>
        ) : (
          <HStack flexShrink={0}>
            <Button
              leftIcon={<AddIcon />}
              variant="outline"
              colorScheme="brand"
              size="sm"
              onClick={onOpen}
              isDisabled={isSaving}
            >
              Add Widget
            </Button>
            <Button
              colorScheme="brand"
              size="sm"
              onClick={saveLayout}
              isLoading={isSaving}
            >
              Done
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={cancelEditing}
              isDisabled={isSaving}
            >
              Cancel
            </Button>
          </HStack>
        )}
      </HStack>

      <DashboardGrid
        layout={layout}
        isEditing={isEditing}
        onLayoutChange={setPendingLayout}
        onAddWidget={onOpen}
      />

      <AddWidgetDrawer
        isOpen={isOpen}
        onClose={onClose}
        currentLayout={layout}
        onAdd={handleAddWidget}
      />
    </Container>
  );
};
