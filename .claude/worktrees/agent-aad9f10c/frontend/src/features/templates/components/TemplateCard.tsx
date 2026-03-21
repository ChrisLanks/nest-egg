/**
 * Card for a single financial template — shows name, description, and activation state.
 */

import {
  Badge,
  Button,
  Card,
  CardBody,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react";
import { FiCheck, FiPlus } from "react-icons/fi";
import type { TemplateInfo } from "../../../api/financial-templates";

const categoryColor: Record<string, string> = {
  goal: "green",
  rule: "purple",
  retirement: "blue",
  budget: "orange",
};

const categoryLabel: Record<string, string> = {
  goal: "Goal",
  rule: "Rule",
  retirement: "Retirement",
  budget: "Budget",
};

interface TemplateCardProps {
  template: TemplateInfo;
  onActivate: (id: string) => void;
  isLoading?: boolean;
}

export default function TemplateCard({
  template,
  onActivate,
  isLoading,
}: TemplateCardProps) {
  return (
    <Card
      variant="outline"
      size="sm"
      _hover={
        template.is_activated
          ? undefined
          : { borderColor: "blue.300", shadow: "sm" }
      }
      transition="all 0.15s"
      opacity={template.is_activated ? 0.75 : 1}
    >
      <CardBody>
        <VStack align="stretch" spacing={3}>
          <HStack justify="space-between">
            <Text fontWeight="semibold" fontSize="sm" noOfLines={1}>
              {template.name}
            </Text>
            <Badge
              colorScheme={categoryColor[template.category] || "gray"}
              size="sm"
            >
              {categoryLabel[template.category] || template.category}
            </Badge>
          </HStack>

          <Text fontSize="xs" color="text.secondary" noOfLines={3}>
            {template.description}
          </Text>

          {template.is_activated ? (
            <Button
              size="sm"
              variant="ghost"
              colorScheme="green"
              leftIcon={<FiCheck />}
              isDisabled
              w="full"
            >
              Active
            </Button>
          ) : (
            <Button
              size="sm"
              variant="outline"
              colorScheme="blue"
              leftIcon={<FiPlus />}
              onClick={() => onActivate(template.id)}
              isLoading={isLoading}
              w="full"
            >
              Set Up
            </Button>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
}
