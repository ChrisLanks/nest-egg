/**
 * Financial Plan Summary — unified financial health view.
 * Aggregates retirement, education, debt, insurance, estate, and emergency fund
 * into a single dashboard with a composite health score and action items.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  CircularProgress,
  CircularProgressLabel,
  Grid,
  GridItem,
  Heading,
  HStack,
  Icon,
  LinkBox,
  LinkOverlay,
  List,
  ListIcon,
  ListItem,
  Spinner,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  Tooltip,
  VStack,
  Center,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import {
  FiAlertTriangle,
  FiCheckCircle,
  FiDollarSign,
  FiHeart,
  FiHome,
  FiShield,
  FiTrendingUp,
  FiUsers,
} from "react-icons/fi";
import api from "../services/api";

interface FinancialPlanSummary {
  net_worth: { total: number; assets: number; liabilities: number };
  retirement: {
    on_track: boolean;
    projected_at_retirement: number;
    monthly_income_projected: number;
    monthly_income_needed: number;
    gap: number;
    retirement_age: number;
    years_until_retirement: number;
  };
  education: { total_children: number; total_education_gap: number; children: any[] };
  debt: {
    total_debt: number;
    high_interest_debt: number;
    payoff_date_mortgage: string | null;
    monthly_debt_payments: number;
  };
  insurance: {
    life_coverage_gap: number;
    has_disability: boolean;
    has_umbrella: boolean;
    umbrella_recommended: boolean;
  };
  estate: {
    has_will: boolean;
    has_poa: boolean;
    beneficiaries_complete: boolean;
    estate_tax_exposure: boolean;
  };
  emergency_fund: { months_covered: number; recommended_months: number; shortfall: number };
  health_score: number;
  top_actions: string[];
}

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

const SummaryCard = ({
  title,
  icon,
  to,
  children,
}: {
  title: string;
  icon: any;
  to: string;
  children: React.ReactNode;
}) => (
  <LinkBox
    as={Box}
    bg="white"
    _dark={{ bg: "gray.800" }}
    borderRadius="lg"
    boxShadow="sm"
    p={5}
    _hover={{ boxShadow: "md", transform: "translateY(-1px)" }}
    transition="all 0.2s"
  >
    <HStack mb={3} spacing={2}>
      <Icon as={icon} boxSize={5} color="brand.500" />
      <LinkOverlay as={RouterLink} to={to}>
        <Heading size="sm">{title}</Heading>
      </LinkOverlay>
    </HStack>
    {children}
  </LinkBox>
);

const FinancialPlanPage = () => {
  const { data, isLoading, error } = useQuery<FinancialPlanSummary>({
    queryKey: ["financial-plan-summary"],
    queryFn: async () => {
      const res = await api.get("/financial-plan/summary");
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <Center py={20}>
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  if (error || !data) {
    return (
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        Unable to load financial plan summary.
      </Alert>
    );
  }

  const scoreColor =
    data.health_score >= 70 ? "green.400" : data.health_score >= 40 ? "yellow.400" : "red.400";

  return (
    <Box maxW="1200px" mx="auto" px={4} py={6}>
      <Heading size="lg" mb={6}>
        Financial Plan
      </Heading>

      {/* Health Score */}
      <Box textAlign="center" mb={8}>
        <CircularProgress
          value={data.health_score}
          size="160px"
          thickness="8px"
          color={scoreColor}
          trackColor="gray.100"
        >
          <CircularProgressLabel>
            <VStack spacing={0}>
              <Text fontSize="3xl" fontWeight="bold">
                {data.health_score}
              </Text>
              <Text fontSize="xs" color="gray.500">
                Health Score
              </Text>
            </VStack>
          </CircularProgressLabel>
        </CircularProgress>
      </Box>

      {/* Top Actions */}
      {data.top_actions.length > 0 && (
        <Box bg="orange.50" _dark={{ bg: "orange.900" }} borderRadius="lg" p={4} mb={6}>
          <Heading size="sm" mb={2}>
            Top Actions
          </Heading>
          <List spacing={2}>
            {data.top_actions.map((action, idx) => (
              <ListItem key={idx} fontSize="sm">
                <ListIcon as={FiAlertTriangle} color="orange.500" />
                {action}
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {/* Summary Cards Grid */}
      <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" }} gap={4}>
        {/* Net Worth */}
        <SummaryCard title="Net Worth" icon={FiDollarSign} to="/dashboard">
          <Stat>
            <StatNumber fontSize="xl">{fmt(data.net_worth.total)}</StatNumber>
            <StatHelpText>
              Assets: {fmt(data.net_worth.assets)} | Liabilities: {fmt(data.net_worth.liabilities)}
            </StatHelpText>
          </Stat>
        </SummaryCard>

        {/* Retirement */}
        <SummaryCard title="Retirement" icon={FiTrendingUp} to="/retirement">
          <HStack mb={1}>
            <Badge colorScheme={data.retirement.on_track ? "green" : "red"}>
              {data.retirement.on_track ? "On Track" : "Needs Attention"}
            </Badge>
          </HStack>
          <Text fontSize="sm">
            Projected: {fmt(data.retirement.projected_at_retirement)} at age{" "}
            {data.retirement.retirement_age}
          </Text>
          {data.retirement.gap > 0 && (
            <Text fontSize="sm" color="red.500">
              Monthly gap: {fmt(data.retirement.gap)}
            </Text>
          )}
        </SummaryCard>

        {/* Education */}
        <SummaryCard title="Education" icon={FiUsers} to="/education">
          <Text fontSize="sm">
            {data.education.total_children} {data.education.total_children === 1 ? "child" : "children"}
          </Text>
          {data.education.total_education_gap > 0 && (
            <Text fontSize="sm" color="orange.500">
              Funding gap: {fmt(data.education.total_education_gap)}
            </Text>
          )}
        </SummaryCard>

        {/* Debt */}
        <SummaryCard title="Debt" icon={FiHome} to="/debt-payoff">
          <Stat>
            <StatNumber fontSize="xl">{fmt(data.debt.total_debt)}</StatNumber>
            <StatHelpText>Monthly payments: {fmt(data.debt.monthly_debt_payments)}</StatHelpText>
          </Stat>
          {data.debt.high_interest_debt > 0 && (
            <Text fontSize="xs" color="red.500">
              High-interest: {fmt(data.debt.high_interest_debt)}
            </Text>
          )}
        </SummaryCard>

        {/* Insurance */}
        <SummaryCard title="Insurance" icon={FiShield} to="/life-planning">
          <VStack align="start" spacing={1}>
            <HStack>
              <Icon
                as={data.insurance.has_disability ? FiCheckCircle : FiAlertTriangle}
                color={data.insurance.has_disability ? "green.500" : "orange.500"}
              />
              <Text fontSize="sm">Disability</Text>
            </HStack>
            <HStack>
              <Icon
                as={data.insurance.has_umbrella ? FiCheckCircle : FiAlertTriangle}
                color={data.insurance.has_umbrella ? "green.500" : "orange.500"}
              />
              <Text fontSize="sm">Umbrella</Text>
            </HStack>
            {data.insurance.life_coverage_gap > 0 && (
              <Text fontSize="xs" color="orange.500">
                Life coverage gap: {fmt(data.insurance.life_coverage_gap)}
              </Text>
            )}
          </VStack>
        </SummaryCard>

        {/* Estate */}
        <SummaryCard title="Estate" icon={FiHeart} to="/life-planning">
          <VStack align="start" spacing={1}>
            <HStack>
              <Icon
                as={data.estate.has_will ? FiCheckCircle : FiAlertTriangle}
                color={data.estate.has_will ? "green.500" : "red.500"}
              />
              <Text fontSize="sm">Will</Text>
            </HStack>
            <HStack>
              <Icon
                as={data.estate.has_poa ? FiCheckCircle : FiAlertTriangle}
                color={data.estate.has_poa ? "green.500" : "red.500"}
              />
              <Text fontSize="sm">Power of Attorney</Text>
            </HStack>
            <HStack>
              <Icon
                as={data.estate.beneficiaries_complete ? FiCheckCircle : FiAlertTriangle}
                color={data.estate.beneficiaries_complete ? "green.500" : "orange.500"}
              />
              <Text fontSize="sm">Beneficiaries</Text>
            </HStack>
          </VStack>
        </SummaryCard>

        {/* Emergency Fund */}
        <GridItem colSpan={{ base: 1, md: 2, lg: 3 }}>
          <Box
            bg="white"
            _dark={{ bg: "gray.800" }}
            borderRadius="lg"
            boxShadow="sm"
            p={5}
          >
            <Heading size="sm" mb={3}>
              Emergency Fund
            </Heading>
            <HStack spacing={8} wrap="wrap">
              <Stat>
                <StatLabel>Months Covered</StatLabel>
                <StatNumber
                  color={data.emergency_fund.months_covered >= 6 ? "green.500" : "orange.500"}
                >
                  {data.emergency_fund.months_covered}
                </StatNumber>
                <StatHelpText>Target: {data.emergency_fund.recommended_months} months</StatHelpText>
              </Stat>
              {data.emergency_fund.shortfall > 0 && (
                <Stat>
                  <StatLabel>Shortfall</StatLabel>
                  <StatNumber color="red.500" fontSize="lg">
                    {fmt(data.emergency_fund.shortfall)}
                  </StatNumber>
                </Stat>
              )}
            </HStack>
          </Box>
        </GridItem>
      </Grid>
    </Box>
  );
};

export default FinancialPlanPage;
