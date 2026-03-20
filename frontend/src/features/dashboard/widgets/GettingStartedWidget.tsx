import React, { memo, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
  HStack,
  Icon,
  IconButton,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { FiCheckCircle, FiCircle } from "react-icons/fi";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import api from "../../../services/api";

const DISMISSED_KEY = "nest-egg-getting-started-dismissed";
const NET_WORTH_VIEWED_KEY = "nest-egg-net-worth-viewed";

interface StepProps {
  label: string;
  to: string;
  done: boolean;
}

const Step: React.FC<StepProps> = ({ label, to, done }) => {
  const navigate = useNavigate();

  return (
    <HStack spacing={3} w="100%">
      <Icon
        as={done ? FiCheckCircle : FiCircle}
        color={done ? "green.500" : "gray.400"}
        boxSize={5}
        flexShrink={0}
      />
      <Text
        as={RouterLink}
        to={to}
        fontSize="sm"
        fontWeight="medium"
        color={done ? "text.muted" : "inherit"}
        textDecoration={done ? "line-through" : "none"}
        _hover={{ textDecoration: "underline" }}
        flex={1}
      >
        {label}
      </Text>
      {!done && (
        <Button
          variant="link"
          size="xs"
          colorScheme="brand"
          onClick={() => navigate(to)}
        >
          → Do it now
        </Button>
      )}
    </HStack>
  );
};

const GettingStartedWidgetBase: React.FC = () => {
  const [dismissed, setDismissed] = useState<boolean>(
    () => localStorage.getItem(DISMISSED_KEY) === "true",
  );

  const { data: accounts } = useQuery({
    queryKey: ["getting-started-accounts"],
    queryFn: () => api.get("/accounts/").then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: budgets } = useQuery({
    queryKey: ["getting-started-budgets"],
    queryFn: () => api.get("/budgets/").then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: savingsGoals } = useQuery({
    queryKey: ["getting-started-savings-goals"],
    queryFn: () => api.get("/savings-goals/").then((r) => r.data),
    staleTime: 60_000,
  });

  if (dismissed) return null;

  const step1Done = Array.isArray(accounts) && accounts.length > 0;
  const step2Done = Array.isArray(budgets) && budgets.length > 0;
  const step3Done = Array.isArray(savingsGoals) && savingsGoals.length > 0;
  const step4Done = localStorage.getItem(NET_WORTH_VIEWED_KEY) === "true";

  if (step1Done && step2Done && step3Done && step4Done) return null;

  const handleDismiss = () => {
    localStorage.setItem(DISMISSED_KEY, "true");
    setDismissed(true);
  };

  return (
    <Card h="100%">
      <CardHeader pb={2}>
        <HStack justify="space-between" align="center">
          <Heading size="md">Getting Started</Heading>
          <IconButton
            aria-label="Dismiss getting started checklist"
            icon={
              <Text fontSize="lg" lineHeight={1}>
                ×
              </Text>
            }
            variant="ghost"
            size="sm"
            onClick={handleDismiss}
          />
        </HStack>
      </CardHeader>
      <CardBody pt={2}>
        <VStack align="stretch" spacing={3}>
          <Step
            label="Connect a bank account"
            to="/accounts"
            done={step1Done}
          />
          <Step label="Set your first budget" to="/budgets" done={step2Done} />
          <Step label="Create a savings goal" to="/goals" done={step3Done} />
          <Step
            label="Review your net worth"
            to="/net-worth-timeline"
            done={step4Done}
          />
        </VStack>
      </CardBody>
    </Card>
  );
};

export const GettingStartedWidget = memo(GettingStartedWidgetBase);
