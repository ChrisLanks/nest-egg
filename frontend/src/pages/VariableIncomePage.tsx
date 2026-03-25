/**
 * Variable Income Planner page.
 *
 * Helps freelancers and self-employed users smooth out income volatility,
 * set a minimum monthly floor, and stay on top of quarterly estimated taxes.
 *
 * Settings (income label filter, tax rates) are persisted to localStorage so
 * they survive page reloads without requiring a backend settings endpoint.
 */

import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Collapse,
  Container,
  Divider,
  FormControl,
  FormHelperText,
  FormLabel,
  Heading,
  HStack,
  Icon,
  NumberInput,
  NumberInputField,
  Select,
  SimpleGrid,
  Skeleton,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tooltip,
  Tr,
  VStack,
  useDisclosure,
} from "@chakra-ui/react";
import { FiInfo, FiSettings } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";

interface MonthlyTrend {
  month: string; // "YYYY-MM"
  income: number;
  expenses: number;
  net: number;
}

interface LabelResponse {
  id: string;
  name: string;
  color?: string;
  is_income?: boolean;
}

const STORAGE_KEY = "nest-egg-variable-income-settings";

interface VariableIncomeSettings {
  incomeLabelName: string; // "" = all income
  seTaxRate: number; // e.g. 14.13 (percent)
  fedTaxRate: number; // e.g. 22 (percent)
  stateTaxRate: number; // e.g. 5 (percent)
}

const DEFAULTS: VariableIncomeSettings = {
  incomeLabelName: "",
  seTaxRate: 14.13, // effective rate after 50% SE tax deduction: 15.3% × 92.35%
  fedTaxRate: 22,
  stateTaxRate: 0,
};

function loadSettings(): VariableIncomeSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS;
  } catch {
    return DEFAULTS;
  }
}

function saveSettings(s: VariableIncomeSettings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip label={label} placement="top" hasArrow maxW="280px">
      <Box as="span" display="inline-flex" ml={1} verticalAlign="middle" cursor="help">
        <Icon as={FiInfo} boxSize={3} color="text.muted" />
      </Box>
    </Tooltip>
  );
}

function fmt(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function getQuarterlySchedule(year: number) {
  return [
    { quarter: `Q1 ${year}`, period: "Jan 1 – Mar 31", dueDate: `Apr 15, ${year}` },
    { quarter: `Q2 ${year}`, period: "Apr 1 – May 31", dueDate: `Jun 16, ${year}` },
    { quarter: `Q3 ${year}`, period: "Jun 1 – Aug 31", dueDate: `Sep 15, ${year}` },
    { quarter: `Q4 ${year}`, period: "Sep 1 – Dec 31", dueDate: `Jan 15, ${year + 1}` },
  ];
}

export const VariableIncomePage = () => {
  const { selectedUserId } = useUserView();
  const today = new Date();
  const currentYear = today.getFullYear();
  const { isOpen: settingsOpen, onToggle: toggleSettings } = useDisclosure();

  const [settings, setSettings] = useState<VariableIncomeSettings>(loadSettings);

  const updateSetting = <K extends keyof VariableIncomeSettings>(
    key: K,
    value: VariableIncomeSettings[K],
  ) => {
    setSettings((prev) => {
      const next = { ...prev, [key]: value };
      saveSettings(next);
      return next;
    });
  };

  // Trailing 13 months so we always have a full 12 + current partial month
  const start = new Date(today.getFullYear() - 1, today.getMonth(), 1);
  const startStr = start.toISOString().slice(0, 10);
  const endStr = today.toISOString().slice(0, 10);

  const { data: trend = [], isLoading } = useQuery<MonthlyTrend[]>({
    queryKey: [
      "variable-income-trend",
      selectedUserId,
      startStr,
      endStr,
      settings.incomeLabelName,
    ],
    queryFn: async () => {
      const params: Record<string, string> = { start_date: startStr, end_date: endStr };
      if (selectedUserId) params.user_id = selectedUserId;
      if (settings.incomeLabelName) params.label_name = settings.incomeLabelName;
      const res = await api.get("/income-expenses/trend", { params });
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  // All labels for the picker (income labels first, but show all so user can
  // choose any label they've applied to income transactions)
  const { data: labels = [] } = useQuery<LabelResponse[]>({
    queryKey: ["labels-all"],
    queryFn: async () => {
      const res = await api.get("/labels/");
      return res.data;
    },
    staleTime: 10 * 60 * 1000,
  });

  const combinedRate =
    (settings.seTaxRate + settings.fedTaxRate + settings.stateTaxRate) / 100;

  const stats = useMemo(() => {
    if (!trend.length) return null;

    const currentMonthKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
    const currentMonthData = trend.find((t) => t.month === currentMonthKey);
    const thisMonthIncome = currentMonthData?.income ?? 0;
    const thisMonthSpend = currentMonthData ? Math.abs(currentMonthData.expenses) : 0;

    // Trailing 12 full months (exclude current partial month)
    const fullMonths = trend.filter((t) => t.month < currentMonthKey);
    const last12 = fullMonths.slice(-12);

    const avgMonthlyIncome =
      last12.length > 0 ? last12.reduce((s, m) => s + m.income, 0) / last12.length : 0;

    const avgMonthlySpend =
      last12.length > 0
        ? last12.reduce((s, m) => s + Math.abs(m.expenses), 0) / last12.length
        : 0;

    const lowestIncome =
      last12.length > 0 ? Math.min(...last12.map((m) => m.income)) : 0;

    const variance = thisMonthIncome - avgMonthlyIncome;

    // Safe spending floor: 80% of lowest monthly income
    const safeFloor = lowestIncome * 0.8;

    // Quarterly estimated tax
    const projectedAnnual = avgMonthlyIncome * 12;
    const quarterlyTaxEst = (projectedAnnual * combinedRate) / 4;

    return {
      thisMonthIncome,
      thisMonthSpend,
      avgMonthlyIncome,
      avgMonthlySpend,
      lowestIncome,
      variance,
      safeFloor,
      projectedAnnual,
      quarterlyTaxEst,
      monthsOfData: last12.length,
    };
  }, [trend, today, combinedRate]);

  const hasData = !isLoading && stats !== null && stats.monthsOfData > 0;

  const quarterlySchedule = getQuarterlySchedule(currentYear);

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <HStack justify="space-between" w="full" align="start">
          <Box>
            <Heading size="lg">Variable Income Planner</Heading>
            <Text color="text.secondary" mt={1}>
              Smooth out income volatility with rolling averages, set a minimum
              monthly floor, and stay on top of quarterly estimated tax payments.
            </Text>
          </Box>
          <Button
            leftIcon={<Icon as={FiSettings} />}
            variant="outline"
            size="sm"
            onClick={toggleSettings}
            flexShrink={0}
          >
            Settings
          </Button>
        </HStack>

        {/* Settings Panel */}
        <Collapse in={settingsOpen} animateOpacity style={{ width: "100%" }}>
          <Card variant="outline" w="full">
            <CardHeader pb={1}>
              <Heading size="sm">Planner Settings</Heading>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
                <FormControl>
                  <FormLabel fontSize="sm">Income Label Filter</FormLabel>
                  <Select
                    size="sm"
                    value={settings.incomeLabelName}
                    onChange={(e) => updateSetting("incomeLabelName", e.target.value)}
                  >
                    <option value="">All income transactions</option>
                    {labels.map((l) => (
                      <option key={l.id} value={l.name}>
                        {l.name}
                      </option>
                    ))}
                  </Select>
                  <FormHelperText fontSize="xs">
                    Isolate self-employment or business income by label
                  </FormHelperText>
                </FormControl>

                <FormControl>
                  <FormLabel fontSize="sm">
                    SE Tax Rate (%)
                    <InfoTip label="Self-employment tax (Social Security + Medicare). The effective rate is ~14.13% because you deduct half the SE tax before applying it. The statutory rate is 15.3%." />
                  </FormLabel>
                  <NumberInput
                    size="sm"
                    min={0}
                    max={20}
                    step={0.1}
                    precision={2}
                    value={settings.seTaxRate}
                    onChange={(_, v) => !isNaN(v) && updateSetting("seTaxRate", v)}
                  >
                    <NumberInputField />
                  </NumberInput>
                  <FormHelperText fontSize="xs">
                    Effective rate after 50% SE deduction (~14.13%)
                  </FormHelperText>
                </FormControl>

                <FormControl>
                  <FormLabel fontSize="sm">
                    Federal Income Tax Rate (%)
                    <InfoTip label="Your marginal federal income tax bracket. Common rates: 10%, 12%, 22%, 24%, 32%, 35%, 37%. Use your expected bracket for the year." />
                  </FormLabel>
                  <NumberInput
                    size="sm"
                    min={0}
                    max={50}
                    step={1}
                    value={settings.fedTaxRate}
                    onChange={(_, v) => !isNaN(v) && updateSetting("fedTaxRate", v)}
                  >
                    <NumberInputField />
                  </NumberInput>
                  <FormHelperText fontSize="xs">
                    Your marginal bracket (10–37%)
                  </FormHelperText>
                </FormControl>

                <FormControl>
                  <FormLabel fontSize="sm">
                    State Income Tax Rate (%)
                    <InfoTip label="Your state marginal income tax rate. Set to 0 if you live in a no-income-tax state (TX, FL, WA, NV, WY, SD, TN, AK, NH)." />
                  </FormLabel>
                  <NumberInput
                    size="sm"
                    min={0}
                    max={15}
                    step={0.5}
                    value={settings.stateTaxRate}
                    onChange={(_, v) => !isNaN(v) && updateSetting("stateTaxRate", v)}
                  >
                    <NumberInputField />
                  </NumberInput>
                  <FormHelperText fontSize="xs">
                    0% for no-income-tax states
                  </FormHelperText>
                </FormControl>
              </SimpleGrid>
            </CardBody>
          </Card>
        </Collapse>

        {/* Income Smoothing */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Income Smoothing
            <InfoTip label="The 12-month rolling average normalizes volatile income for consistent budgeting. The IRS safe harbor for avoiding underpayment penalties is paying 100% of prior-year tax (110% if AGI exceeded $150k) or 90% of current-year tax." />
          </Heading>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} w="full">
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel>
                    This Month
                    <InfoTip label="Gross income recognized in the current calendar month." />
                  </StatLabel>
                  <Skeleton isLoaded={!isLoading}>
                    <StatNumber fontSize="lg">
                      {hasData ? fmt(stats!.thisMonthIncome) : "—"}
                    </StatNumber>
                  </Skeleton>
                  <StatHelpText>
                    {settings.incomeLabelName ? `label: ${settings.incomeLabelName}` : "all income"}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel>
                    12-Month Rolling Avg
                    <InfoTip label="Average monthly gross income over the trailing 12 months. Use this as your budgeting baseline." />
                  </StatLabel>
                  <Skeleton isLoaded={!isLoading}>
                    <StatNumber fontSize="lg">
                      {hasData ? fmt(stats!.avgMonthlyIncome) : "—"}
                    </StatNumber>
                  </Skeleton>
                  <StatHelpText>
                    {hasData ? `based on ${stats!.monthsOfData} months` : "per month avg"}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel>
                    Variance vs Average
                    <InfoTip label="How much this month deviates from your 12-month average. Large positive swings are a good time to fund estimated taxes and savings goals." />
                  </StatLabel>
                  <Skeleton isLoaded={!isLoading}>
                    <StatNumber
                      fontSize="lg"
                      color={
                        !hasData
                          ? undefined
                          : stats!.variance >= 0
                          ? "green.500"
                          : "red.500"
                      }
                    >
                      {hasData
                        ? `${stats!.variance >= 0 ? "+" : ""}${fmt(stats!.variance)}`
                        : "—"}
                    </StatNumber>
                  </Skeleton>
                  <StatHelpText>this month vs avg</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>
        </Box>

        <Divider />

        {/* Quarterly Tax Estimates */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Quarterly Tax Estimates
            <InfoTip label="Self-employed individuals must pay estimated taxes quarterly to avoid underpayment penalties. The safe harbor is the lesser of 90% of current-year tax or 100%/110% of prior-year tax." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <HStack justify="space-between" wrap="wrap" gap={2}>
                <Heading size="sm">Q1–Q4 Payment Schedule</Heading>
                {hasData && (
                  <Text fontSize="xs" color="text.secondary">
                    ~{fmt(stats!.quarterlyTaxEst)} / quarter · {Math.round(combinedRate * 100)}%
                    combined rate
                  </Text>
                )}
              </HStack>
            </CardHeader>
            <CardBody overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>Quarter</Th>
                    <Th>Income Period</Th>
                    <Th>Due Date</Th>
                    <Th isNumeric>Est. Payment</Th>
                    <Th>Status</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {quarterlySchedule.map((q) => {
                    const due = new Date(q.dueDate);
                    const isPast = due < today;
                    const isCurrent =
                      !isPast && due.getTime() - today.getTime() < 60 * 24 * 60 * 60 * 1000;
                    return (
                      <Tr key={q.quarter}>
                        <Td fontWeight="medium">{q.quarter}</Td>
                        <Td color="text.secondary">{q.period}</Td>
                        <Td>{q.dueDate}</Td>
                        <Td isNumeric>
                          <Skeleton isLoaded={!isLoading} display="inline-block">
                            {hasData ? fmt(stats!.quarterlyTaxEst) : "—"}
                          </Skeleton>
                        </Td>
                        <Td>
                          <Badge
                            colorScheme={isPast ? "gray" : isCurrent ? "orange" : "blue"}
                          >
                            {isPast ? "past" : isCurrent ? "due soon" : "upcoming"}
                          </Badge>
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
              <Text fontSize="xs" color="text.secondary" mt={3}>
                Estimates use {settings.seTaxRate}% SE tax + {settings.fedTaxRate}% federal
                {settings.stateTaxRate > 0 ? ` + ${settings.stateTaxRate}% state` : ""} applied
                to your projected annual income of{" "}
                {hasData ? fmt(stats!.projectedAnnual) : "—"}.{" "}
                {settings.incomeLabelName
                  ? `Counting only transactions labeled "${settings.incomeLabelName}".`
                  : ""}{" "}
                Not tax advice — consult a CPA for your actual liability.
              </Text>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* Minimum Budget Floor */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Minimum Budget Floor
            <InfoTip label="Your safe spending floor is based on the lowest-income month in the trailing 12 months. Keeping monthly spending at or below this floor ensures you can cover expenses even in a dry month." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">Safe Spending Floor</Heading>
            </CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Lowest Monthly Income (trailing 12 mo)
                    <InfoTip label="The minimum monthly income in the past year. Used as the conservative baseline for setting your spending floor." />
                  </Text>
                  <Skeleton isLoaded={!isLoading} display="inline-block">
                    <Text fontWeight="semibold">
                      {hasData ? fmt(stats!.lowestIncome) : "—"}
                    </Text>
                  </Skeleton>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Recommended Monthly Spending Cap
                    <InfoTip label="80% of your lowest monthly income, leaving a 20% buffer for taxes and savings even in your worst month." />
                  </Text>
                  <Skeleton isLoaded={!isLoading} display="inline-block">
                    <Text fontWeight="semibold" color="green.500">
                      {hasData ? fmt(stats!.safeFloor) : "—"}
                    </Text>
                  </Skeleton>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Your Average Monthly Spend</Text>
                  <Skeleton isLoaded={!isLoading} display="inline-block">
                    <Text
                      fontWeight="semibold"
                      color={
                        hasData && stats!.avgMonthlySpend > stats!.safeFloor
                          ? "red.500"
                          : undefined
                      }
                    >
                      {hasData ? fmt(stats!.avgMonthlySpend) : "—"}
                    </Text>
                  </Skeleton>
                </HStack>
                {hasData && stats!.avgMonthlySpend > stats!.safeFloor && (
                  <Text fontSize="xs" color="red.500">
                    Your average spending exceeds your safe floor by{" "}
                    {fmt(stats!.avgMonthlySpend - stats!.safeFloor)}/mo. Consider reducing
                    discretionary spend or building a larger buffer.
                  </Text>
                )}
                {hasData && stats!.avgMonthlySpend <= stats!.safeFloor && (
                  <Text fontSize="xs" color="green.600">
                    Your average spending is within your safe floor.
                  </Text>
                )}
                {!hasData && !isLoading && (
                  <Text fontSize="xs" color="text.secondary">
                    No transaction data found for the trailing 12 months.
                  </Text>
                )}
              </VStack>
            </CardBody>
          </Card>
        </Box>
      </VStack>
    </Container>
  );
};

export default VariableIncomePage;
