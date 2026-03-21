/**
 * Dashboard page — thin shell that delegates to the customizable widget grid.
 *
 * All chart/data logic lives in individual widget components under
 * src/features/dashboard/widgets/. Layout persistence is handled by
 * the useWidgetLayout hook.
 */

import {
  Badge,
  Box,
  Button,
  Container,
  Heading,
  HStack,
  Icon,
  Text,
  Tooltip,
  useDisclosure,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { AddIcon, EditIcon, RepeatIcon } from "@chakra-ui/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { FiLink, FiDollarSign, FiBarChart2 } from "react-icons/fi";
import { useAuthStore } from "../features/auth/stores/authStore";
import { DashboardGrid } from "../features/dashboard/DashboardGrid";
import { AddWidgetDrawer } from "../features/dashboard/AddWidgetDrawer";
import { useWidgetLayout } from "../features/dashboard/useWidgetLayout";
import { WIDGET_REGISTRY } from "../features/dashboard/widgetRegistry";
import type { LayoutItem } from "../features/dashboard/types";
import api from "../services/api";
import { AddAccountModal } from "../features/accounts/components/AddAccountModal";
import { GoalContextBanner } from "../features/dashboard/GoalContextBanner";

const GettingStartedEmptyState = ({
  onConnectBank,
}: {
  onConnectBank: () => void;
}) => (
  <Box
    p={8}
    borderRadius="xl"
    bg="bg.surface"
    boxShadow="sm"
    border="1px dashed"
    borderColor="border.default"
    textAlign="center"
  >
    <VStack spacing={6} maxW="md" mx="auto">
      <Icon as={FiBarChart2} boxSize={12} color="brand.500" />
      <VStack spacing={2}>
        <Heading size="md">Your financial picture starts here</Heading>
        <Text color="text.secondary">
          In about 2 minutes you'll see your full financial picture — net worth,
          spending by category, and where your money goes — all in one place.
        </Text>
      </VStack>
      <VStack spacing={3} w="full">
        {[
          {
            icon: FiLink,
            label: "Connect a bank account",
            hint: "We import your transactions automatically — nothing to enter by hand.",
            action: true,
          },
          {
            icon: FiDollarSign,
            label: "Set your first budget",
            hint: "Pick one spending category and give it a monthly limit.",
            action: false,
          },
          {
            icon: FiBarChart2,
            label: "Check your net worth",
            hint: "Everything you own minus everything you owe — your most important number.",
            action: false,
          },
        ].map((step, i) => (
          <HStack
            key={step.label}
            w="full"
            p={3}
            bg="bg.subtle"
            borderRadius="md"
            spacing={3}
            align="start"
          >
            <Icon
              as={step.icon}
              color={step.action ? "brand.500" : "text.muted"}
              boxSize={5}
              mt="2px"
              flexShrink={0}
            />
            <VStack align="start" spacing={0} flex={1}>
              <Text
                fontSize="sm"
                fontWeight="medium"
                color={step.action ? "text.primary" : "text.muted"}
                textAlign="left"
              >
                {i + 1}. {step.label}
              </Text>
              {step.action && (
                <Text fontSize="xs" color="text.secondary" textAlign="left">
                  {step.hint}
                </Text>
              )}
            </VStack>
            {step.action && (
              <Badge colorScheme="brand" fontSize="xs" flexShrink={0}>
                Start here
              </Badge>
            )}
          </HStack>
        ))}
      </VStack>
      <Button
        colorScheme="brand"
        size="lg"
        leftIcon={<FiLink />}
        onClick={onConnectBank}
      >
        Connect a Bank Account
      </Button>
      <Text fontSize="xs" color="text.muted">
        Prefer to enter accounts manually? You can do that from the{" "}
        <Text as="span" fontWeight="medium">
          Accounts
        </Text>{" "}
        page in the sidebar.
      </Text>
    </VStack>
  </Box>
);

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
  const {
    isOpen: isAddAccountOpen,
    onOpen: onAddAccountOpen,
    onClose: onAddAccountClose,
  } = useDisclosure();

  const { data: accounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const res = await api.get("/accounts");
      return res.data as Array<{ id: string }>;
    },
    staleTime: 30_000,
  });
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
              label="Get the latest data from all your accounts right now"
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

      <GoalContextBanner />

      {accounts !== undefined && accounts.length === 0 && (
        <GettingStartedEmptyState onConnectBank={onAddAccountOpen} />
      )}

      {(accounts === undefined || accounts.length > 0) && (
        <DashboardGrid
          layout={layout}
          isEditing={isEditing}
          onLayoutChange={setPendingLayout}
          onAddWidget={onOpen}
        />
      )}

      <AddWidgetDrawer
        isOpen={isOpen}
        onClose={onClose}
        currentLayout={layout}
        onAdd={handleAddWidget}
      />

      <AddAccountModal isOpen={isAddAccountOpen} onClose={onAddAccountClose} />
    </Container>
  );
};
