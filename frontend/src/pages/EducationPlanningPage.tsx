/**
 * Education Planning page — 529 savings projections vs college costs
 */

import { useState } from "react";
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  Center,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Input,
  NumberInput,
  NumberInputField,
  Select,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Text,
  VStack,
  Badge,
  Progress,
  useColorModeValue,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import {
  educationApi,
  type EducationPlansResponse,
  type EducationProjectionResponse,
  type EducationPlanAccount,
} from "../api/education";
import { useUserView } from "../contexts/UserViewContext";
import { EmptyState } from "../components/EmptyState";
import { FiBookOpen } from "react-icons/fi";

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const COLLEGE_TYPE_LABELS: Record<string, string> = {
  public_in_state: "Public (In-State)",
  public_out_of_state: "Public (Out-of-State)",
  private: "Private",
};

// ---------------------------------------------------------------------------
// Per-account projection card
// ---------------------------------------------------------------------------

interface AccountProjectionProps {
  plan: EducationPlanAccount;
}

function AccountProjection({ plan }: AccountProjectionProps) {
  const currentYear = new Date().getFullYear();
  const [childName, setChildName] = useState("");
  const [birthYear, setBirthYear] = useState<number | "">("");
  // Auto-compute years until college from birth year (college at age 18), or let user set manually
  const autoYears =
    birthYear !== "" ? Math.max(1, 18 - (currentYear - birthYear)) : null;
  const [manualYears, setManualYears] = useState(18);
  const yearsUntilCollege = autoYears ?? manualYears;
  const [monthlyContribution, setMonthlyContribution] = useState(
    plan.monthly_contribution || 200,
  );
  const [collegeType, setCollegeType] = useState("public_in_state");
  const [annualReturn, setAnnualReturn] = useState(6);

  const areaFill = useColorModeValue("#3182ce", "#00B5D8");
  const areaStroke = useColorModeValue("#2B6CB0", "#00A3C4");
  const costColor = useColorModeValue("#E53E3E", "#FC8181");

  const { data: projection, isLoading } = useQuery<EducationProjectionResponse>(
    {
      queryKey: [
        "education-projection",
        plan.account_id,
        plan.current_balance,
        monthlyContribution,
        yearsUntilCollege,
        collegeType,
        annualReturn,
      ],
      queryFn: () =>
        educationApi.getProjection({
          current_balance: plan.current_balance,
          monthly_contribution: monthlyContribution,
          years_until_college: yearsUntilCollege,
          college_type: collegeType,
          annual_return: annualReturn / 100,
        }),
      enabled: yearsUntilCollege >= 1,
    },
  );

  const fundingPct = projection?.funding_percentage ?? 0;
  const progressColor =
    fundingPct >= 100 ? "green" : fundingPct >= 60 ? "yellow" : "red";

  return (
    <Card variant="outline">
      <CardHeader pb={2}>
        <HStack justify="space-between" flexWrap="wrap">
          <VStack align="start" spacing={0}>
            <Heading size="sm">
              {childName ? `${childName} — ` : ""}
              {plan.account_name}
            </Heading>
            <Text fontSize="sm" color="text.secondary">
              Balance: {formatCurrency(plan.current_balance)}
              {birthYear !== "" &&
                ` · Born ${birthYear} · ${yearsUntilCollege} yrs to college`}
            </Text>
          </VStack>
          {projection && (
            <Badge
              colorScheme={progressColor}
              fontSize="md"
              px={3}
              py={1}
              borderRadius="md"
            >
              {fundingPct.toFixed(0)}% Funded
            </Badge>
          )}
        </HStack>
      </CardHeader>
      <CardBody pt={2}>
        <VStack align="stretch" spacing={5}>
          {/* Child profile */}
          <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={3}>
            <FormControl size="sm">
              <FormLabel fontSize="xs">Child's Name (optional)</FormLabel>
              <Input
                size="sm"
                placeholder="e.g. Emma"
                value={childName}
                onChange={(e) => setChildName(e.target.value)}
              />
            </FormControl>
            <FormControl size="sm">
              <FormLabel fontSize="xs">
                Birth Year (auto-calculates timeline)
              </FormLabel>
              <NumberInput
                size="sm"
                min={currentYear - 25}
                max={currentYear}
                value={birthYear === "" ? "" : birthYear}
                onChange={(_, val) => setBirthYear(isNaN(val) ? "" : val)}
              >
                <NumberInputField placeholder={`e.g. ${currentYear - 5}`} />
              </NumberInput>
            </FormControl>
          </SimpleGrid>

          {/* Projection controls */}
          <SimpleGrid columns={{ base: 1, sm: 2, md: 4 }} spacing={3}>
            <FormControl size="sm">
              <FormLabel fontSize="xs">College Type</FormLabel>
              <Select
                size="sm"
                value={collegeType}
                onChange={(e) => setCollegeType(e.target.value)}
              >
                {Object.entries(COLLEGE_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </FormControl>
            <FormControl size="sm">
              <FormLabel fontSize="xs">
                Years Until College
                {autoYears !== null && (
                  <Text as="span" color="text.muted" fontWeight="normal">
                    {" "}
                    (auto)
                  </Text>
                )}
              </FormLabel>
              <NumberInput
                size="sm"
                min={1}
                max={30}
                value={yearsUntilCollege}
                onChange={(_, val) => setManualYears(isNaN(val) ? 18 : val)}
                isReadOnly={autoYears !== null}
              >
                <NumberInputField
                  bg={autoYears !== null ? "bg.subtle" : undefined}
                />
              </NumberInput>
            </FormControl>
            <FormControl size="sm">
              <FormLabel fontSize="xs">Monthly Contribution</FormLabel>
              <NumberInput
                size="sm"
                min={0}
                max={10000}
                step={50}
                value={monthlyContribution}
                onChange={(_, val) =>
                  setMonthlyContribution(isNaN(val) ? 0 : val)
                }
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
            <FormControl size="sm">
              <FormLabel fontSize="xs">Annual Return (%)</FormLabel>
              <NumberInput
                size="sm"
                min={0}
                max={20}
                step={0.5}
                precision={1}
                value={annualReturn}
                onChange={(_, val) => setAnnualReturn(isNaN(val) ? 6 : val)}
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
          </SimpleGrid>

          {isLoading && (
            <Center py={6}>
              <Spinner />
            </Center>
          )}

          {projection && !isLoading && (
            <>
              {/* Funding progress bar */}
              <Box>
                <HStack justify="space-between" mb={1}>
                  <Text fontSize="sm" fontWeight="medium">
                    Projected Savings
                  </Text>
                  <Text fontSize="sm" fontWeight="medium">
                    {formatCurrency(projection.projected_balance)} /{" "}
                    {formatCurrency(projection.total_college_cost)}
                  </Text>
                </HStack>
                <Progress
                  value={Math.min(fundingPct, 100)}
                  colorScheme={progressColor}
                  size="lg"
                  borderRadius="md"
                  hasStripe={fundingPct < 100}
                  isAnimated={fundingPct < 100}
                />
              </Box>

              {/* Summary stats */}
              <SimpleGrid columns={{ base: 2, md: 4 }} spacing={3}>
                <Stat size="sm">
                  <StatLabel>Projected Balance</StatLabel>
                  <StatNumber fontSize="lg">
                    {formatCurrency(projection.projected_balance)}
                  </StatNumber>
                  <StatHelpText>at college start</StatHelpText>
                </Stat>
                <Stat size="sm">
                  <StatLabel>Est. College Cost</StatLabel>
                  <StatNumber fontSize="lg">
                    {formatCurrency(projection.total_college_cost)}
                  </StatNumber>
                  <StatHelpText>4 years, inflation-adjusted</StatHelpText>
                </Stat>
                {projection.funding_gap > 0 ? (
                  <Stat size="sm">
                    <StatLabel>Funding Gap</StatLabel>
                    <StatNumber fontSize="lg" color="red.400">
                      {formatCurrency(projection.funding_gap)}
                    </StatNumber>
                    <StatHelpText>shortfall</StatHelpText>
                  </Stat>
                ) : (
                  <Stat size="sm">
                    <StatLabel>Surplus</StatLabel>
                    <StatNumber fontSize="lg" color="green.400">
                      {formatCurrency(projection.funding_surplus)}
                    </StatNumber>
                    <StatHelpText>extra savings</StatHelpText>
                  </Stat>
                )}
                <Stat size="sm">
                  <StatLabel>Recommended Monthly</StatLabel>
                  <StatNumber fontSize="lg">
                    {formatCurrency(
                      projection.recommended_monthly_to_close_gap,
                    )}
                  </StatNumber>
                  <StatHelpText>to close gap</StatHelpText>
                </Stat>
              </SimpleGrid>

              {/* Projection chart */}
              {projection.projections.length > 0 && (
                <Box>
                  <ResponsiveContainer width="100%" height={250}>
                    <AreaChart
                      data={projection.projections}
                      margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                      <XAxis
                        dataKey="year"
                        tickFormatter={(y: number) => `Yr ${y}`}
                        fontSize={12}
                      />
                      <YAxis
                        tickFormatter={(v: number) =>
                          `$${(v / 1000).toFixed(0)}k`
                        }
                        fontSize={12}
                      />
                      <RechartsTooltip
                        formatter={(value: number) => [
                          formatCurrency(value),
                          "Projected Savings",
                        ]}
                        labelFormatter={(y: number) => `Year ${y}`}
                      />
                      <ReferenceLine
                        y={projection.total_college_cost}
                        stroke={costColor}
                        strokeDasharray="6 3"
                        label={{
                          value: `College Cost: ${formatCurrency(projection.total_college_cost)}`,
                          position: "insideTopRight",
                          fill: costColor,
                          fontSize: 11,
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="projected_savings"
                        stroke={areaStroke}
                        fill={areaFill}
                        fillOpacity={0.3}
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              )}
            </>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function EducationPlanningPage() {
  const {
    selectedUserId,
    isCombinedView,
    memberEffectiveUserId,
    selectedMemberIdsKey,
  } = useUserView();

  const effectiveUserId = isCombinedView
    ? memberEffectiveUserId
    : effectiveUserId;

  const { data: plansData, isLoading, isError } = useQuery<EducationPlansResponse>({
    queryKey: ["education-plans", effectiveUserId, selectedMemberIdsKey],
    queryFn: () => educationApi.getPlans(effectiveUserId || undefined),
  });

  const plans = plansData?.plans ?? [];
  const totalSavings = plansData?.total_529_savings ?? 0;

  return (
    <Box p={8}>
      <VStack align="stretch" spacing={6}>
        {/* Header */}
        <VStack align="start" spacing={1}>
          <Heading size="lg">Education Planning</Heading>
          <Text color="text.secondary">
            Project 529 savings against estimated college costs
          </Text>
        </VStack>

        {/* Loading */}
        {isLoading && (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        )}

        {/* Error */}
        {isError && !isLoading && (
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            Failed to load education plans. Please refresh and try again.
          </Alert>
        )}

        {/* Empty state */}
        {!isLoading && plans.length === 0 && (
          <VStack spacing={4} align="stretch">
            <EmptyState
              icon={FiBookOpen}
              title="No 529 accounts found"
              description="Add a 529 education savings account to start planning for college costs. You can add one from the Accounts page."
            />
            <Alert status="info" borderRadius="md">
              <AlertIcon />
              Don&apos;t see your 529? Make sure the account type is set to
              &ldquo;529 Plan&rdquo; in Account Settings &mdash; go to Accounts,
              click the account, and change the type to &ldquo;529 Plan&rdquo;.
            </Alert>
          </VStack>
        )}

        {/* Summary stats */}
        {!isLoading && plans.length > 0 && (
          <>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>Total 529 Savings</StatLabel>
                    <StatNumber>{formatCurrency(totalSavings)}</StatNumber>
                    <StatHelpText>
                      across {plans.length}{" "}
                      {plans.length === 1 ? "account" : "accounts"}
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>529 Accounts</StatLabel>
                    <StatNumber>{plans.length}</StatNumber>
                    <StatHelpText>beneficiaries</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>Monthly Contributions</StatLabel>
                    <StatNumber>
                      {formatCurrency(
                        plans.reduce(
                          (sum, p) => sum + p.monthly_contribution,
                          0,
                        ),
                      )}
                    </StatNumber>
                    <StatHelpText>total across all 529s</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>

            {/* Per-account projections */}
            <VStack align="stretch" spacing={4}>
              {plans.map((plan) => (
                <AccountProjection key={plan.account_id} plan={plan} />
              ))}
            </VStack>
          </>
        )}
      </VStack>
    </Box>
  );
}
