/**
 * Social Security Claiming Strategy page.
 *
 * Accepts current salary, birth year, and optional spouse PIA.
 * Shows per-age benefit comparison (62–70), lifetime value under three
 * longevity scenarios, and the recommended optimal claiming age.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Center,
  Container,
  FormControl,
  FormHelperText,
  FormLabel,
  Heading,
  HStack,
  Icon,
  Input,
  InputGroup,
  InputLeftAddon,
  NumberDecrementStepper,
  NumberIncrementStepper,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  SimpleGrid,
  Spinner,
  Stat,
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
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { FiInfo } from "react-icons/fi";
import {
  financialPlanningApi,
  type SSClaimingParams,
} from "../api/financialPlanning";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useLocalStorage } from "../hooks/useLocalStorage";

// ── Helpers ───────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const CURRENT_YEAR = new Date().getFullYear();

function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip label={label} placement="top" hasArrow maxW="260px">
      <Box
        as="span"
        display="inline-flex"
        ml={1}
        verticalAlign="middle"
        cursor="help"
      >
        <Icon as={FiInfo} boxSize={3} color="text.muted" />
      </Box>
    </Tooltip>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export const SSClaimingPage = () => {
  const { selectedUserId, effectiveUserId } = useUserView();

  // Form state — persisted across page refreshes
  // Salary and retirementAge defaults seeded from /settings/financial-defaults
  const [salary, setSalary] = useLocalStorage("ss-salary", "");
  const [birthYear, setBirthYear] = useLocalStorage(
    "ss-birth-year",
    String(CURRENT_YEAR - 58),
  );
  const [careerStartAge, setCareerStartAge] = useLocalStorage(
    "ss-career-start-age",
    "22",
  );
  const [manualPia, setManualPia] = useLocalStorage("ss-manual-pia", "");
  const [spousePia, setSpousePia] = useLocalStorage("ss-spouse-pia", "");
  const [plannedRetirementAge, setPlannedRetirementAge] = useLocalStorage(
    "ss-planned-retirement-age",
    "",
  );

  // Seed defaults from backend when no localStorage value exists
  useEffect(() => {
    const hasSalary = (localStorage.getItem("ss-salary") ?? "").length > 0;
    const hasRetAge = (localStorage.getItem("ss-planned-retirement-age") ?? "").length > 0;
    if (hasSalary && hasRetAge) return;
    api.get("/settings/financial-defaults").then((r) => {
      const d = r.data;
      if (!hasSalary) setSalary(String(d.default_annual_spending ?? 80000));
      if (!hasRetAge) setPlannedRetirementAge(String(d.default_retirement_age ?? 67));
    }).catch(() => {
      if (!hasSalary) setSalary("80000");
      if (!hasRetAge) setPlannedRetirementAge("67");
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // Auto-submit on load if persisted salary exists (returning users see results immediately)
  const [submitted, setSubmitted] = useState(
    () => (parseFloat(localStorage.getItem("ss-salary") ?? "") || 0) > 0,
  );

  const salaryNum = parseFloat(salary) || 0;
  const birthYearNum = parseInt(birthYear) || CURRENT_YEAR - 58;
  const plannedRetirementAgeNum = parseInt(plannedRetirementAge) || 65;

  const params: SSClaimingParams = {
    user_id: effectiveUserId || undefined,
    current_salary: salaryNum,
    birth_year: birthYearNum,
    career_start_age: parseInt(careerStartAge) || 22,
    manual_pia: manualPia ? parseFloat(manualPia) : undefined,
    spouse_pia: spousePia ? parseFloat(spousePia) : undefined,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ss-claiming", effectiveUserId, params],
    queryFn: () => financialPlanningApi.getSSClaiming(params),
    enabled: submitted && salaryNum > 0,
  });

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">Social Security Optimizer</Heading>
          <Text color="text.secondary" mt={1}>
            Compare lifetime benefits for every claiming age from 62 to 70
            across pessimistic, base, and optimistic longevity scenarios.
          </Text>
        </Box>

        {/* Inputs */}
        <Card variant="outline" w="full">
          <CardHeader pb={0}>
            <Heading size="sm">Your Details</Heading>
          </CardHeader>
          <CardBody>
            <VStack spacing={4}>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} w="full">
                <FormControl isRequired>
                  <FormLabel fontSize="xs">
                    Current Annual Salary
                    <InfoTip label="Your current yearly earnings from work (W-2 wages or self-employment). This is used to estimate your Social Security benefit if you don't have an official SSA statement." />
                  </FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      value={salary}
                      onChange={(e) => setSalary(e.target.value)}
                    />
                  </InputGroup>
                  <FormHelperText fontSize="xs">
                    Used to estimate your benefit. If left at 0, a $75,000
                    salary baseline is assumed.
                  </FormHelperText>
                </FormControl>
                <FormControl isRequired>
                  <FormLabel fontSize="xs">
                    Birth Year
                    <InfoTip label="The year you were born. Social Security uses this to determine your Full Retirement Age (FRA) — the age at which you receive 100% of your benefit." />
                  </FormLabel>
                  <Input
                    size="sm"
                    type="number"
                    min={1940}
                    max={2000}
                    value={birthYear}
                    onChange={(e) => setBirthYear(e.target.value)}
                  />
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="xs">
                    Career Start Age
                    <InfoTip label="The age you started working and paying into Social Security. Social Security averages your highest 35 years of earnings — a longer career generally means a higher benefit." />
                  </FormLabel>
                  <NumberInput
                    size="sm"
                    min={14}
                    max={80}
                    value={careerStartAge}
                    onChange={(val) => setCareerStartAge(val)}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </FormControl>
              </SimpleGrid>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} w="full">
                <FormControl>
                  <FormLabel fontSize="xs">
                    Planned Retirement Age
                    <InfoTip label="The age at which you plan to stop working. This is used to show how many years you'd wait between retirement and when you start claiming Social Security." />
                  </FormLabel>
                  <NumberInput
                    size="sm"
                    min={50}
                    max={80}
                    value={plannedRetirementAge}
                    onChange={(val) => setPlannedRetirementAge(val)}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                  <FormHelperText fontSize="xs">
                    Used to show years from retirement until claiming starts.
                  </FormHelperText>
                </FormControl>
              </SimpleGrid>
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} w="full">
                <FormControl>
                  <FormLabel fontSize="xs">
                    Your PIA from SSA Statement (optional)
                    <InfoTip label="Your Primary Insurance Amount (PIA) is the exact monthly benefit you'd receive at Full Retirement Age, found on your Social Security statement at ssa.gov. If you have this number, enter it here for the most accurate results — otherwise we'll estimate it from your salary." />
                  </FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder="Leave blank to estimate"
                      value={manualPia}
                      onChange={(e) => setManualPia(e.target.value)}
                    />
                  </InputGroup>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="xs">
                    Spouse&apos;s Estimated PIA (optional)
                    <InfoTip label="Your spouse's Primary Insurance Amount. Enter this to see spousal benefit options — a spouse can claim up to 50% of your benefit at FRA if it's higher than their own earned benefit." />
                  </FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder="Leave blank if single"
                      value={spousePia}
                      onChange={(e) => setSpousePia(e.target.value)}
                    />
                  </InputGroup>
                </FormControl>
              </SimpleGrid>
              <Button
                colorScheme="brand"
                size="sm"
                onClick={() => {
                  setSubmitted(true);
                  refetch();
                }}
                isDisabled={salaryNum <= 0}
              >
                Analyze
              </Button>
            </VStack>
          </CardBody>
        </Card>

        {/* Loading / error */}
        {isLoading && (
          <Center w="full" py={8}>
            <Spinner size="lg" color="brand.500" />
          </Center>
        )}
        {isError && (
          <Alert status="error" borderRadius="lg" w="full">
            <AlertIcon />
            Failed to load SS analysis. Please check your inputs.
          </Alert>
        )}

        {/* Results */}
        {data && (
          <>
            {/* Key stats */}
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} w="full">
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Estimated PIA
                      <InfoTip label="Your Primary Insurance Amount — the monthly benefit you'd receive if you claim at exactly your Full Retirement Age (FRA). Claiming earlier reduces this; claiming later increases it." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {fmt(data.estimated_pia)}/mo
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Full Retirement Age
                      <InfoTip label="The age at which you receive 100% of your earned benefit. For people born 1960 or later, FRA is 67. Claiming before FRA permanently reduces your benefit; claiming after FRA increases it by 8% per year up to age 70." />
                    </StatLabel>
                    <StatNumber fontSize="lg">{data.fra_age}</StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Optimal Age (Base)
                      <InfoTip label="The claiming age that maximizes your total lifetime Social Security income assuming an average life expectancy (base scenario). This balances starting earlier (more checks) against starting later (larger checks)." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {data.optimal_age_base_scenario}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Your Current Age
                      <InfoTip label="Your age today, calculated from your birth year. Used to show how many years until each potential claiming age." />
                    </StatLabel>
                    <StatNumber fontSize="lg">{data.current_age}</StatNumber>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>

            {/* Summary narrative */}
            <Alert status="info" borderRadius="lg" w="full">
              <AlertIcon />
              <Text fontSize="sm">{data.summary}</Text>
            </Alert>

            {/* Age comparison table */}
            <Card variant="outline" w="full">
              <CardHeader pb={0}>
                <Heading size="sm">Claiming Age Comparison (62–70)</Heading>
              </CardHeader>
              <CardBody overflowX="auto">
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Age</Th>
                      <Th isNumeric>
                        Monthly
                        <InfoTip label="The monthly Social Security check you'd receive if you start claiming at this age. Claiming at 62 gives the smallest check; claiming at 70 gives the largest (up to 32% more than FRA)." />
                      </Th>
                      <Th isNumeric>Annual</Th>
                      <Th isNumeric>
                        Lifetime (to 78)
                        <InfoTip label="Total Social Security income if you live to age 78 — a pessimistic scenario. Shorter lifespans favor claiming earlier to collect more years of payments." />
                      </Th>
                      <Th isNumeric>
                        Lifetime (to 85)
                        <InfoTip label="Total Social Security income if you live to age 85 — the average U.S. life expectancy. This is the base scenario used to determine the optimal claiming age." />
                      </Th>
                      <Th isNumeric>
                        Lifetime (to 92)
                        <InfoTip label="Total Social Security income if you live to age 92 — an optimistic scenario. Longer lifespans strongly favor delaying to 70 for the highest monthly amount." />
                      </Th>
                      <Th isNumeric>
                        After Retirement
                        <InfoTip label={`Years you'd wait after your planned retirement age (${plannedRetirementAgeNum}) before claiming. Negative means you'd still be working when you start claiming.`} />
                      </Th>
                      <Th isNumeric>
                        Break-even vs 62
                        <InfoTip label="How long you need to live after claiming before this age 'pays off' compared to claiming at 62. For example, if the break-even is 12y 3m, you need to collect benefits for at least that long before the higher monthly amount catches up." />
                      </Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {data.options.map((opt) => {
                      const isOptBase =
                        opt.claiming_age === data.optimal_age_base_scenario;
                      const yearsAfterRetirement = opt.claiming_age - plannedRetirementAgeNum;
                      return (
                        <Tr
                          key={opt.claiming_age}
                          bg={isOptBase ? "brand.50" : undefined}
                        >
                          <Td>
                            <HStack spacing={1}>
                              <Text fontWeight={isOptBase ? "bold" : "normal"}>
                                {opt.claiming_age}
                              </Text>
                              {isOptBase && (
                                <Badge colorScheme="brand" size="sm">
                                  optimal
                                </Badge>
                              )}
                            </HStack>
                          </Td>
                          <Td
                            isNumeric
                            fontWeight={isOptBase ? "bold" : "normal"}
                          >
                            {fmt(opt.monthly_benefit)}
                          </Td>
                          <Td isNumeric>{fmt(opt.annual_benefit)}</Td>
                          <Td isNumeric>{fmt(opt.lifetime_pessimistic)}</Td>
                          <Td isNumeric>{fmt(opt.lifetime_base)}</Td>
                          <Td isNumeric>{fmt(opt.lifetime_optimistic)}</Td>
                          <Td isNumeric color={yearsAfterRetirement < 0 ? "orange.500" : undefined}>
                            {yearsAfterRetirement > 0
                              ? `+${yearsAfterRetirement}y`
                              : yearsAfterRetirement === 0
                              ? "At retirement"
                              : `${yearsAfterRetirement}y`}
                          </Td>
                          <Td isNumeric>
                            {opt.breakeven_vs_62_months == null
                              ? "—"
                              : `${Math.floor(opt.breakeven_vs_62_months / 12)}y ${opt.breakeven_vs_62_months % 12}m`}
                          </Td>
                        </Tr>
                      );
                    })}
                  </Tbody>
                </Table>
              </CardBody>
            </Card>

            {/* Spousal benefits */}
            {data.spousal && (
              <Card variant="outline" w="full">
                <CardHeader pb={0}>
                  <Heading size="sm">
                    Spousal Benefit Estimate
                    <InfoTip label="A spouse can claim up to 50% of the higher earner's FRA benefit if it exceeds their own earned benefit. The actual amount depends on when the spouse claims — earlier means a reduced spousal benefit." />
                  </Heading>
                </CardHeader>
                <CardBody>
                  <VStack align="start" spacing={3}>
                    <SimpleGrid
                      columns={{ base: 2, md: 4 }}
                      spacing={4}
                      w="full"
                    >
                      <Box>
                        <Text fontSize="xs" color="text.secondary">
                          At FRA
                          <InfoTip label="The spousal benefit if the spouse claims at their own Full Retirement Age — this is the maximum spousal amount (50% of the higher earner's PIA)." />
                        </Text>
                        <Text fontWeight="bold">
                          {fmt(data.spousal.spousal_monthly_at_fra)}/mo
                        </Text>
                      </Box>
                      <Box>
                        <Text fontSize="xs" color="text.secondary">
                          At 62
                          <InfoTip label="The spousal benefit if the spouse claims at 62 — the earliest possible age. Claiming early permanently reduces the spousal benefit below the 50% maximum." />
                        </Text>
                        <Text fontWeight="bold">
                          {fmt(data.spousal.spousal_monthly_at_62)}/mo
                        </Text>
                      </Box>
                      <Box>
                        <Text fontSize="xs" color="text.secondary">
                          At 70
                          <InfoTip label="Note: spousal benefits do NOT increase past FRA the way earned benefits do. Claiming spousal benefits at 70 gives the same amount as at FRA." />
                        </Text>
                        <Text fontWeight="bold">
                          {fmt(data.spousal.spousal_monthly_at_70)}/mo
                        </Text>
                      </Box>
                    </SimpleGrid>
                    <Text
                      fontSize="xs"
                      color="text.secondary"
                      fontStyle="italic"
                    >
                      {data.spousal.note}
                    </Text>
                  </VStack>
                </CardBody>
              </Card>
            )}
          </>
        )}
      </VStack>
    </Container>
  );
};

export default SSClaimingPage;
