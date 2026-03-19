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
  FormLabel,
  Heading,
  HStack,
  Input,
  InputGroup,
  InputLeftAddon,
  Select,
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
  Tr,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  financialPlanningApi,
  type SSClaimingParams,
} from "../api/financialPlanning";
import { useUserView } from "../contexts/UserViewContext";

// ── Helpers ───────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const CURRENT_YEAR = new Date().getFullYear();

// ── Page ──────────────────────────────────────────────────────────────────

export const SSClaimingPage = () => {
  const { selectedUserId } = useUserView();

  // Form state
  const [salary, setSalary] = useState("80000");
  const [birthYear, setBirthYear] = useState(String(CURRENT_YEAR - 58));
  const [careerStartAge, setCareerStartAge] = useState("22");
  const [manualPia, setManualPia] = useState("");
  const [spousePia, setSpousePia] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const salaryNum = parseFloat(salary) || 0;
  const birthYearNum = parseInt(birthYear) || CURRENT_YEAR - 58;

  const params: SSClaimingParams = {
    user_id: selectedUserId || undefined,
    current_salary: salaryNum,
    birth_year: birthYearNum,
    career_start_age: parseInt(careerStartAge) || 22,
    manual_pia: manualPia ? parseFloat(manualPia) : undefined,
    spouse_pia: spousePia ? parseFloat(spousePia) : undefined,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ss-claiming", selectedUserId, params],
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
                  <FormLabel fontSize="xs">Current Annual Salary</FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      value={salary}
                      onChange={(e) => setSalary(e.target.value)}
                    />
                  </InputGroup>
                </FormControl>
                <FormControl isRequired>
                  <FormLabel fontSize="xs">Birth Year</FormLabel>
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
                  <FormLabel fontSize="xs">Career Start Age</FormLabel>
                  <Select
                    size="sm"
                    value={careerStartAge}
                    onChange={(e) => setCareerStartAge(e.target.value)}
                  >
                    {[18, 20, 22, 24, 26].map((a) => (
                      <option key={a} value={a}>
                        {a}
                      </option>
                    ))}
                  </Select>
                </FormControl>
              </SimpleGrid>
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} w="full">
                <FormControl>
                  <FormLabel fontSize="xs">
                    Your PIA from SSA Statement (optional)
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
                Analyse
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
                    <StatLabel>Estimated PIA</StatLabel>
                    <StatNumber fontSize="lg">
                      {fmt(data.estimated_pia)}/mo
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>Full Retirement Age</StatLabel>
                    <StatNumber fontSize="lg">{data.fra_age}</StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>Optimal Age (Base)</StatLabel>
                    <StatNumber fontSize="lg">
                      {data.optimal_age_base_scenario}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>Your Current Age</StatLabel>
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
                      <Th isNumeric>Monthly</Th>
                      <Th isNumeric>Annual</Th>
                      <Th isNumeric>Lifetime (die 78)</Th>
                      <Th isNumeric>Lifetime (die 85)</Th>
                      <Th isNumeric>Lifetime (die 92)</Th>
                      <Th isNumeric>Break-even vs 62</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {data.options.map((opt) => {
                      const isOptBase =
                        opt.claiming_age === data.optimal_age_base_scenario;
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
                  <Heading size="sm">Spousal Benefit Estimate</Heading>
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
                        </Text>
                        <Text fontWeight="bold">
                          {fmt(data.spousal.spousal_monthly_at_fra)}/mo
                        </Text>
                      </Box>
                      <Box>
                        <Text fontSize="xs" color="text.secondary">
                          At 62
                        </Text>
                        <Text fontWeight="bold">
                          {fmt(data.spousal.spousal_monthly_at_62)}/mo
                        </Text>
                      </Box>
                      <Box>
                        <Text fontSize="xs" color="text.secondary">
                          At 70
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
