/**
 * Rental Properties P&L page with Schedule E-style breakdown
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Container,
  Heading,
  Text,
  Tooltip,
  VStack,
  HStack,
  Card,
  CardBody,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Spinner,
  Center,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Select,
  Divider,
  useColorModeValue,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  rentalPropertiesApi,
  type PropertiesSummary,
  type PropertyPnl,
} from "../api/rental-properties";
import { useUserView } from "../contexts/UserViewContext";
import { EmptyState } from "../components/EmptyState";
import { FiHome } from "react-icons/fi";
import { useCurrency } from "../contexts/CurrencyContext";

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const formatPercent = (value: number) => `${value.toFixed(1)}%`;

const currentYear = new Date().getFullYear();
const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i);

export const RentalPropertiesPage = () => {
  const { currency } = useCurrency();

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);

  const formatCurrencyDetailed = (amount: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  const {
    selectedUserId,
    isCombinedView,
    memberEffectiveUserId,
    selectedMemberIdsKey,
  } = useUserView();
  const multiEffectiveUserId = memberEffectiveUserId;
  const selectedIdsKey = selectedMemberIdsKey;

  const effectiveUserId = isCombinedView
    ? multiEffectiveUserId
    : effectiveUserId;

  const [year, setYear] = useState(currentYear);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(
    null,
  );

  const cardBg = useColorModeValue("white", "gray.800");
  const barIncomeBg = useColorModeValue("green.400", "green.300");
  const barExpenseBg = useColorModeValue("red.400", "red.300");

  // Fetch summary
  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useQuery<PropertiesSummary>({
    queryKey: [
      "rental-properties-summary",
      effectiveUserId,
      selectedIdsKey,
      year,
    ],
    queryFn: () =>
      rentalPropertiesApi.getSummary({
        year,
        user_id: effectiveUserId || undefined,
      }),
  });

  // Fetch detail P&L when a property is selected
  const { data: propertyPnl, isLoading: pnlLoading } = useQuery<PropertyPnl>({
    queryKey: ["rental-property-pnl", selectedPropertyId, year],
    queryFn: () =>
      rentalPropertiesApi.getPropertyPnl(selectedPropertyId!, { year }),
    enabled: !!selectedPropertyId,
  });

  if (summaryLoading) {
    return (
      <Container maxW="container.lg" py={8}>
        <Center py={20}>
          <Spinner size="xl" color="brand.500" />
        </Center>
      </Container>
    );
  }

  if (summaryError) {
    return (
      <Container maxW="container.lg" py={8}>
        <Center py={20}>
          <Text color="red.500">Failed to load rental property data.</Text>
        </Center>
      </Container>
    );
  }

  const hasProperties = summary && summary.property_count > 0;

  return (
    <Container maxW="container.lg" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <VStack align="start" spacing={0}>
            <Heading size="lg">Rental Property Profit & Loss</Heading>
            <Text color="text.secondary" fontSize="sm">
              Track income, expenses, and net profit for each rental property
              (organized by Schedule E tax categories)
            </Text>
          </VStack>
          <Select
            w="120px"
            value={year}
            onChange={(e) => {
              setYear(Number(e.target.value));
              setSelectedPropertyId(null);
            }}
          >
            {yearOptions.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </Select>
        </HStack>

        {!hasProperties ? (
          <EmptyState
            icon={FiHome}
            title="No Rental Properties"
            description='Add a property account and classify it as "Investment Property" — it will appear here automatically for Schedule E P&L tracking, cap rate analysis, and STR reporting.'
          />
        ) : (
          <>
            {/* Summary Cards */}
            <SimpleGrid columns={{ base: 1, md: 4 }} spacing={4}>
              <Card bg={cardBg}>
                <CardBody>
                  <Stat>
                    <StatLabel>Total Rental Income</StatLabel>
                    <StatNumber color="green.500">
                      {formatCurrency(summary!.total_income)}
                    </StatNumber>
                    <StatHelpText>{year}</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
              <Card bg={cardBg}>
                <CardBody>
                  <Stat>
                    <StatLabel>Total Expenses</StatLabel>
                    <StatNumber color="red.500">
                      {formatCurrency(summary!.total_expenses)}
                    </StatNumber>
                    <StatHelpText>{year}</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
              <Card bg={cardBg}>
                <CardBody>
                  <Stat>
                    <StatLabel>Net Income</StatLabel>
                    <StatNumber
                      color={
                        summary!.total_net_income >= 0 ? "green.500" : "red.500"
                      }
                    >
                      {formatCurrency(summary!.total_net_income)}
                    </StatNumber>
                    <StatHelpText>{year}</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
              <Card bg={cardBg}>
                <CardBody>
                  <Stat>
                    <StatLabel>Average Cap Rate</StatLabel>
                    <StatNumber>
                      {formatPercent(summary!.average_cap_rate)}
                    </StatNumber>
                    <StatHelpText>
                      {summary!.property_count} propert
                      {summary!.property_count === 1 ? "y" : "ies"}
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>

            {/* Property List */}
            <VStack spacing={3} align="stretch">
              <Heading size="md">Properties</Heading>
              {summary!.properties.map((prop) => (
                <Card
                  key={prop.account_id}
                  bg={cardBg}
                  cursor="pointer"
                  borderWidth={selectedPropertyId === prop.account_id ? 2 : 1}
                  borderColor={
                    selectedPropertyId === prop.account_id
                      ? "brand.500"
                      : "border.default"
                  }
                  onClick={() =>
                    setSelectedPropertyId(
                      selectedPropertyId === prop.account_id
                        ? null
                        : prop.account_id,
                    )
                  }
                  _hover={{ borderColor: "brand.300" }}
                  transition="all 0.2s"
                >
                  <CardBody py={4}>
                    <HStack justify="space-between" align="start">
                      <VStack align="start" spacing={1} flex={1}>
                        <HStack>
                          <Text fontWeight="semibold" fontSize="md">
                            {prop.name}
                          </Text>
                          {prop.cap_rate > 0 && (
                            <Badge
                              colorScheme={
                                prop.cap_rate >= 5 ? "green" : "yellow"
                              }
                            >
                              {formatPercent(prop.cap_rate)} cap
                            </Badge>
                          )}
                          {prop.is_str && (
                            <Tooltip
                              label="Short-Term Rental (Airbnb/VRBO). May qualify for the IRC §469 STR loophole — rental losses can offset ordinary income if you materially participate."
                              hasArrow
                              placement="top"
                            >
                              <Badge colorScheme="purple" cursor="help">STR</Badge>
                            </Tooltip>
                          )}
                          {prop.rental_type === "long_term_rental" && (
                            <Badge colorScheme="blue" variant="subtle">LTR</Badge>
                          )}
                          {prop.rental_type === "buy_and_hold" && (
                            <Badge colorScheme="gray" variant="subtle">Hold</Badge>
                          )}
                        </HStack>
                        {prop.rental_address && (
                          <Text fontSize="sm" color="text.secondary">
                            {prop.rental_address}
                          </Text>
                        )}
                        <HStack spacing={4} fontSize="sm">
                          <Text color="text.muted">
                            Value: {formatCurrency(prop.current_value)}
                          </Text>
                          {prop.rental_monthly_income > 0 && (
                            <Text color="text.muted">
                              Rent: {formatCurrency(prop.rental_monthly_income)}
                              /mo
                            </Text>
                          )}
                        </HStack>
                      </VStack>
                      <VStack align="end" spacing={0}>
                        <HStack spacing={6}>
                          <VStack spacing={0} align="end">
                            <Text fontSize="xs" color="text.muted">
                              Income
                            </Text>
                            <Text
                              fontWeight="semibold"
                              color="green.500"
                              fontSize="sm"
                            >
                              {formatCurrency(prop.gross_income)}
                            </Text>
                          </VStack>
                          <VStack spacing={0} align="end">
                            <Text fontSize="xs" color="text.muted">
                              Expenses
                            </Text>
                            <Text
                              fontWeight="semibold"
                              color="red.500"
                              fontSize="sm"
                            >
                              {formatCurrency(prop.total_expenses)}
                            </Text>
                          </VStack>
                          <VStack spacing={0} align="end">
                            <Text fontSize="xs" color="text.muted">
                              Net
                            </Text>
                            <Text
                              fontWeight="bold"
                              color={
                                prop.net_income >= 0 ? "green.500" : "red.500"
                              }
                            >
                              {formatCurrency(prop.net_income)}
                            </Text>
                          </VStack>
                        </HStack>
                      </VStack>
                    </HStack>
                  </CardBody>
                </Card>
              ))}
            </VStack>

            {/* Detail P&L when a property is selected */}
            {selectedPropertyId && (
              <VStack spacing={4} align="stretch">
                <Divider />
                {pnlLoading ? (
                  <Center py={10}>
                    <Spinner size="lg" color="brand.500" />
                  </Center>
                ) : propertyPnl ? (
                  <>
                    <Heading size="md">
                      {propertyPnl.name} — {year} P&L Detail
                    </Heading>

                    {/* STR loophole callout */}
                    {propertyPnl.is_str && propertyPnl.str_loophole_active !== false && (
                      <Alert status="info" variant="subtle" borderRadius="md">
                        <AlertIcon />
                        <AlertDescription fontSize="sm">
                          <strong>Short-Term Rental (STR) Tax Note:</strong> Since average rental
                          periods are ≤7 days, this property may qualify for the{" "}
                          <strong>IRC §469 STR loophole</strong>. If you materially participate
                          (≥750 hrs/yr or qualify as a real estate professional), rental losses
                          can offset ordinary income — bypassing the passive activity loss rules
                          that limit long-term rental deductions to $25K/yr. Consult a CPA before
                          claiming this treatment.
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Expense Breakdown Table */}
                    <Card bg={cardBg}>
                      <CardBody>
                        <Heading size="sm" mb={3}>
                          Expense Breakdown (Schedule E)
                        </Heading>
                        {propertyPnl.expense_breakdown.length === 0 ? (
                          <Text color="text.muted" fontSize="sm">
                            No expenses recorded for {year}.
                          </Text>
                        ) : (
                          <Table size="sm" variant="simple">
                            <Thead>
                              <Tr>
                                <Th>Category</Th>
                                <Th isNumeric>Amount</Th>
                              </Tr>
                            </Thead>
                            <Tbody>
                              {propertyPnl.expense_breakdown.map((item) => (
                                <Tr key={item.category}>
                                  <Td>{item.category}</Td>
                                  <Td isNumeric>
                                    {formatCurrencyDetailed(item.amount)}
                                  </Td>
                                </Tr>
                              ))}
                              <Tr fontWeight="bold">
                                <Td>Total Expenses</Td>
                                <Td isNumeric color="red.500">
                                  {formatCurrencyDetailed(
                                    propertyPnl.total_expenses,
                                  )}
                                </Td>
                              </Tr>
                            </Tbody>
                          </Table>
                        )}
                      </CardBody>
                    </Card>

                    {/* Monthly Income/Expense Chart (simple bar representation) */}
                    <Card bg={cardBg}>
                      <CardBody>
                        <Heading size="sm" mb={3}>
                          Monthly Income vs Expenses
                        </Heading>
                        <Table size="sm" variant="simple">
                          <Thead>
                            <Tr>
                              <Th>Month</Th>
                              <Th isNumeric>Income</Th>
                              <Th isNumeric>Expenses</Th>
                              <Th isNumeric>Net</Th>
                              <Th w="200px"></Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {propertyPnl.monthly.map((m) => {
                              const maxVal = Math.max(
                                ...propertyPnl.monthly.map((row) =>
                                  Math.max(row.income, row.expenses),
                                ),
                                1,
                              );
                              const incomePct = (m.income / maxVal) * 100;
                              const expensePct = (m.expenses / maxVal) * 100;
                              return (
                                <Tr key={m.month}>
                                  <Td>{MONTH_NAMES[m.month - 1]}</Td>
                                  <Td isNumeric>
                                    {m.income > 0
                                      ? formatCurrencyDetailed(m.income)
                                      : "-"}
                                  </Td>
                                  <Td isNumeric>
                                    {m.expenses > 0
                                      ? formatCurrencyDetailed(m.expenses)
                                      : "-"}
                                  </Td>
                                  <Td
                                    isNumeric
                                    color={m.net >= 0 ? "green.500" : "red.500"}
                                    fontWeight="medium"
                                  >
                                    {m.income > 0 || m.expenses > 0
                                      ? formatCurrencyDetailed(m.net)
                                      : "-"}
                                  </Td>
                                  <Td>
                                    <VStack spacing={1} align="stretch">
                                      <Box
                                        h="6px"
                                        w={`${incomePct}%`}
                                        bg={barIncomeBg}
                                        borderRadius="sm"
                                        minW={incomePct > 0 ? "4px" : "0px"}
                                      />
                                      <Box
                                        h="6px"
                                        w={`${expensePct}%`}
                                        bg={barExpenseBg}
                                        borderRadius="sm"
                                        minW={expensePct > 0 ? "4px" : "0px"}
                                      />
                                    </VStack>
                                  </Td>
                                </Tr>
                              );
                            })}
                          </Tbody>
                        </Table>
                      </CardBody>
                    </Card>

                    {/* P&L Summary */}
                    <Card bg={cardBg}>
                      <CardBody>
                        <Heading size="sm" mb={3}>
                          Annual Summary
                        </Heading>
                        <SimpleGrid columns={2} spacing={4}>
                          <HStack justify="space-between">
                            <Text>Gross Rental Income</Text>
                            <Text fontWeight="semibold" color="green.500">
                              {formatCurrencyDetailed(propertyPnl.gross_income)}
                            </Text>
                          </HStack>
                          <HStack justify="space-between">
                            <Text>Total Expenses</Text>
                            <Text fontWeight="semibold" color="red.500">
                              {formatCurrencyDetailed(
                                propertyPnl.total_expenses,
                              )}
                            </Text>
                          </HStack>
                          <HStack justify="space-between">
                            <Text fontWeight="bold">Net Income</Text>
                            <Text
                              fontWeight="bold"
                              color={
                                propertyPnl.net_income >= 0
                                  ? "green.500"
                                  : "red.500"
                              }
                            >
                              {formatCurrencyDetailed(propertyPnl.net_income)}
                            </Text>
                          </HStack>
                          <HStack justify="space-between">
                            <Text>Cap Rate</Text>
                            <Text fontWeight="semibold">
                              {formatPercent(propertyPnl.cap_rate)}
                            </Text>
                          </HStack>
                        </SimpleGrid>
                      </CardBody>
                    </Card>
                  </>
                ) : null}
              </VStack>
            )}
          </>
        )}
      </VStack>
    </Container>
  );
};

export default RentalPropertiesPage;
