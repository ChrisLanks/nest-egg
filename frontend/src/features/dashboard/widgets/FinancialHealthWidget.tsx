import {
  Box,
  Card,
  CardBody,
  Heading,
  HStack,
  Progress,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { memo } from "react";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface HealthComponent {
  score: number;
  value: number;
  label: string;
  detail: string;
}

interface FinancialHealthData {
  overall_score: number;
  grade: string;
  components: {
    savings_rate: HealthComponent;
    emergency_fund: HealthComponent;
    debt_to_income: HealthComponent;
    retirement_progress: HealthComponent;
  };
  recommendations: string[];
}

const gradeColor = (grade: string): string => {
  switch (grade) {
    case "A":
      return "green.400";
    case "B":
      return "green.300";
    case "C":
      return "yellow.400";
    case "D":
      return "orange.400";
    default:
      return "red.400";
  }
};

const scoreColorScheme = (score: number): string => {
  if (score >= 75) return "green";
  if (score >= 50) return "yellow";
  if (score >= 25) return "orange";
  return "red";
};

const gaugeColor = (score: number): string => {
  if (score >= 75) return "green.400";
  if (score >= 50) return "yellow.400";
  if (score >= 25) return "orange.400";
  return "red.400";
};

const FinancialHealthWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<FinancialHealthData>({
    queryKey: ["financial-health", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get("/dashboard/financial-health", { params });
      return response.data;
    },
    retry: false,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <Card h="100%">
        <CardBody display="flex" alignItems="center" justifyContent="center">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Financial Health
          </Heading>
          <Text color="text.muted" fontSize="sm">
            Add accounts and transactions to see your financial health score.
          </Text>
        </CardBody>
      </Card>
    );
  }

  const components = [
    data.components.savings_rate,
    data.components.emergency_fund,
    data.components.debt_to_income,
    data.components.retirement_progress,
  ];

  return (
    <Card h="100%">
      <CardBody>
        <Heading size="md" mb={4}>
          Financial Health
        </Heading>

        {/* Overall score with gauge */}
        <VStack spacing={1} mb={5}>
          <HStack spacing={3} align="baseline">
            <Text fontSize="4xl" fontWeight="bold" lineHeight={1}>
              {Math.round(data.overall_score)}
            </Text>
            <Text
              fontSize="2xl"
              fontWeight="bold"
              color={gradeColor(data.grade)}
            >
              {data.grade}
            </Text>
          </HStack>
          <Box w="100%">
            <Progress
              value={data.overall_score}
              size="lg"
              borderRadius="full"
              colorScheme={scoreColorScheme(data.overall_score)}
              bg="gray.100"
            />
          </Box>
          <HStack w="100%" justify="space-between">
            <Text fontSize="2xs" color="text.muted">
              0
            </Text>
            <Text fontSize="2xs" color="text.muted">
              100
            </Text>
          </HStack>
        </VStack>

        {/* Component scores */}
        <VStack align="stretch" spacing={3} mb={4}>
          {components.map((comp) => (
            <Box key={comp.label}>
              <HStack justify="space-between" mb={1}>
                <Text fontSize="sm" fontWeight="medium">
                  {comp.label}
                </Text>
                <Text
                  fontSize="sm"
                  fontWeight="bold"
                  color={gaugeColor(comp.score)}
                >
                  {Math.round(comp.score)}
                </Text>
              </HStack>
              <Progress
                value={comp.score}
                size="sm"
                borderRadius="full"
                colorScheme={scoreColorScheme(comp.score)}
              />
              <Text fontSize="xs" color="text.muted" mt={0.5}>
                {comp.detail}
              </Text>
            </Box>
          ))}
        </VStack>

        {/* Top recommendation */}
        {data.recommendations.length > 0 && (
          <Box bg="blue.50" _dark={{ bg: "blue.900" }} p={3} borderRadius="md">
            <Text
              fontSize="xs"
              fontWeight="medium"
              color="blue.700"
              _dark={{ color: "blue.200" }}
            >
              Tip
            </Text>
            <Text fontSize="xs" color="blue.600" _dark={{ color: "blue.300" }}>
              {data.recommendations[0]}
            </Text>
          </Box>
        )}
      </CardBody>
    </Card>
  );
};

export const FinancialHealthWidget = memo(FinancialHealthWidgetBase);
