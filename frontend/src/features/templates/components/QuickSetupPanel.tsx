/**
 * Quick Setup panel — shows all financial templates grouped by category.
 * Shown on the dashboard for new users or accessible from /quick-setup.
 */

import {
  Box,
  Heading,
  HStack,
  Icon,
  SimpleGrid,
  Skeleton,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { FiZap } from "react-icons/fi";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  financialTemplatesApi,
  type TemplateInfo,
} from "../../../api/financial-templates";
import TemplateCard from "./TemplateCard";

const CATEGORY_ORDER = ["goal", "rule", "retirement", "budget"] as const;
const CATEGORY_TITLES: Record<string, string> = {
  goal: "Savings Goals",
  rule: "Auto-Categorization Rules",
  retirement: "Retirement Planning",
  budget: "Budgeting",
};

export default function QuickSetupPanel() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [activatingId, setActivatingId] = useState<string | null>(null);

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ["financial-templates"],
    queryFn: financialTemplatesApi.getAll,
    staleTime: 5 * 60 * 1000,
  });

  const activateMutation = useMutation({
    mutationFn: financialTemplatesApi.activate,
    onSuccess: (_data, templateId) => {
      queryClient.invalidateQueries({ queryKey: ["financial-templates"] });
      // Also invalidate related queries so the UI updates
      if (templateId.startsWith("goal:")) {
        queryClient.invalidateQueries({ queryKey: ["savings-goals"] });
      } else if (templateId.startsWith("rule:")) {
        queryClient.invalidateQueries({ queryKey: ["rules"] });
      } else if (templateId === "retirement:default") {
        queryClient.invalidateQueries({ queryKey: ["retirement"] });
      }
      const t = templates.find((t) => t.id === templateId);
      toast({
        title: `${t?.name || "Template"} activated`,
        status: "success",
        duration: 3000,
      });
      setActivatingId(null);
    },
    onError: (error: unknown) => {
      const detail = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast({
        title: "Failed to activate template",
        description: detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
      setActivatingId(null);
    },
  });

  const handleActivate = (id: string) => {
    setActivatingId(id);
    activateMutation.mutate(id);
  };

  // Group templates by category
  const grouped = CATEGORY_ORDER.reduce(
    (acc, cat) => {
      const items = templates.filter((t) => t.category === cat);
      if (items.length > 0) acc[cat] = items;
      return acc;
    },
    {} as Record<string, TemplateInfo[]>,
  );

  if (isLoading) {
    return (
      <VStack align="stretch" spacing={4}>
        <HStack>
          <Icon as={FiZap} color="yellow.500" />
          <Heading size="sm">Quick Setup</Heading>
        </HStack>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} height="140px" borderRadius="md" />
          ))}
        </SimpleGrid>
      </VStack>
    );
  }

  const allActivated = templates.every((t) => t.is_activated);
  if (allActivated && templates.length > 0) {
    return null; // Everything is set up — no need to show the panel
  }

  return (
    <VStack align="stretch" spacing={6}>
      <HStack>
        <Icon as={FiZap} color="yellow.500" />
        <Heading size="md">Quick Setup</Heading>
        <Text fontSize="sm" color="text.secondary">
          Get started with recommended financial tools
        </Text>
      </HStack>

      {CATEGORY_ORDER.map((cat) => {
        const items = grouped[cat];
        if (!items) return null;
        return (
          <Box key={cat}>
            <Text
              fontSize="sm"
              fontWeight="semibold"
              color="text.secondary"
              mb={2}
              textTransform="uppercase"
              letterSpacing="wider"
            >
              {CATEGORY_TITLES[cat]}
            </Text>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={3}>
              {items.map((t) => (
                <TemplateCard
                  key={t.id}
                  template={t}
                  onActivate={handleActivate}
                  isLoading={activatingId === t.id}
                />
              ))}
            </SimpleGrid>
          </Box>
        );
      })}
    </VStack>
  );
}
