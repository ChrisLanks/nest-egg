/**
 * Roth Conversion Analyzer
 *
 * Helps users decide whether to convert traditional IRA/401k funds to Roth.
 * Shows break-even analysis, RMD reduction, and lifetime tax impact.
 */

import {
  Box,
  Card,
  CardBody,
  Heading,
  HStack,
  VStack,
  Text,
  SimpleGrid,
  Select,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Badge,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Center,
  Alert,
  AlertIcon,
  FormControl,
  FormLabel,
  Tooltip,
  Icon,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import { FiInfo } from 'react-icons/fi';
import api from '../../../services/api';
import { useUserView } from '../../../contexts/UserViewContext';

interface RothAnalysisData {
  traditional_balance: number;
  projected_rmd_at_73: number | null;
  current_age: number | null;
  accounts: Array<{
    id: string;
    name: string;
    balance: number;
    type: string;
  }>;
}

const TAX_BRACKETS = [10, 12, 22, 24, 32, 35, 37];

// IRS Uniform Lifetime Table factor at age 73
const RMD_FACTOR_AT_73 = 26.5;

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const formatCurrencyPrecise = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

export const RothConversionAnalyzer: React.FC = () => {
  const { selectedUserId } = useUserView();

  const [currentBracket, setCurrentBracket] = useState(22);
  const [retirementBracket, setRetirementBracket] = useState(22);
  const [annualReturn, setAnnualReturn] = useState(7);
  const [annualConversion, setAnnualConversion] = useState(10000);
  // User-editable balance override — lets anyone use the calculator hypothetically
  const [balanceInput, setBalanceInput] = useState<string>('');

  const { data, isLoading, error } = useQuery<RothAnalysisData>({
    queryKey: ['roth-analysis', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const { data: res } = await api.get('/holdings/roth-analysis', { params });
      return res;
    },
  });

  // Years until RMD age (73). Default to 20 if age unknown.
  const yearsUntilRmd = useMemo(() => {
    if (data?.current_age) return Math.max(1, 73 - data.current_age);
    return 20;
  }, [data]);

  const fetchedBalance = data?.traditional_balance ?? 0;

  // Effective balance: user override takes priority, otherwise use fetched value
  const traditionalBalance = balanceInput !== ''
    ? Math.max(0, Number(balanceInput) || 0)
    : fetchedBalance;

  // How many years of conversions fit before retirement (capped to yearsUntilRmd)
  const yearsConverting = yearsUntilRmd;

  // Total amount converted out before retirement
  const totalConverted = Math.min(annualConversion * yearsConverting, traditionalBalance);

  // Total taxes paid on conversions today (in today's dollars)
  const totalTaxesPaid = totalConverted * (currentBracket / 100);

  // Remaining traditional balance after conversions
  const balanceAfterConversions = Math.max(0, traditionalBalance - totalConverted);

  // RMD at 73 — current balance vs. after conversions
  const rmdOriginal = traditionalBalance / RMD_FACTOR_AT_73;
  const rmdAfterConversions = balanceAfterConversions / RMD_FACTOR_AT_73;
  const annualRmdReduction = rmdOriginal - rmdAfterConversions;

  // Annual tax savings in retirement from reduced RMD
  const annualRmdTaxSavings = annualRmdReduction * (retirementBracket / 100);

  // Break-even: years after retirement to recoup conversion taxes via RMD savings
  const breakEvenYears =
    annualRmdTaxSavings > 0
      ? Math.ceil(totalTaxesPaid / annualRmdTaxSavings)
      : null;

  // Net benefit vs. keeping in traditional:
  // Roth is better if retirement bracket > current bracket (accounting for tax-free growth)
  // Simplified: (1+r)^Y × retirementBracket vs currentBracket
  const futureTaxRate =
    Math.pow(1 + annualReturn / 100, yearsUntilRmd) * (retirementBracket / 100);
  const isConversionBeneficial = futureTaxRate > currentBracket / 100;

  // Break-even table — years 1–15 in retirement
  const breakEvenRows = useMemo(() => {
    return Array.from({ length: 15 }, (_, i) => {
      const year = i + 1;
      const cumulativeSaved = annualRmdTaxSavings * year;
      const net = cumulativeSaved - totalTaxesPaid;
      return { year, cumulativeSaved, net };
    });
  }, [annualRmdTaxSavings, totalTaxesPaid]);

  if (isLoading) {
    return (
      <Center py={12}>
        <Spinner size="lg" color="brand.500" />
      </Center>
    );
  }

  if (error) {
    return (
      <Alert status="error">
        <AlertIcon />
        Failed to load retirement account data.
      </Alert>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      {/* Header */}
      <Box>
        <Heading size="md" mb={1}>Roth Conversion Analyzer</Heading>
        <Text fontSize="sm" color="gray.600">
          Model the long-term tax impact of converting traditional retirement funds to Roth.
        </Text>
      </Box>

      {/* No accounts notice */}
      {!isLoading && fetchedBalance === 0 && (
        <Alert status="info">
          <AlertIcon />
          No traditional IRA or 401(k) accounts found. Enter a balance below to run a hypothetical analysis.
        </Alert>
      )}

      {/* Input + Summary in two columns */}
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
        {/* Inputs */}
        <Card variant="outline">
          <CardBody>
            <Heading size="sm" mb={4}>Your Assumptions</Heading>
            <VStack spacing={5} align="stretch">

              <FormControl>
                <FormLabel fontSize="sm">
                  Traditional Balance to Analyze
                  <Tooltip label={fetchedBalance > 0 ? `Auto-filled from your accounts (${formatCurrency(fetchedBalance)}). Edit to run a hypothetical.` : 'Enter your traditional IRA or 401(k) balance'} placement="top">
                    <Icon as={FiInfo} ml={1} boxSize={3} color="gray.400" />
                  </Tooltip>
                </FormLabel>
                <input
                  type="number"
                  value={balanceInput !== '' ? balanceInput : fetchedBalance}
                  onChange={(e) => setBalanceInput(e.target.value)}
                  onFocus={(e) => { if (balanceInput === '' && fetchedBalance > 0) setBalanceInput(String(fetchedBalance)); }}
                  style={{
                    width: '100%',
                    padding: '6px 12px',
                    fontSize: '14px',
                    border: '1px solid #E2E8F0',
                    borderRadius: '6px',
                    outline: 'none',
                  }}
                  placeholder="e.g. 250000"
                  min={0}
                />
              </FormControl>

              <FormControl>
                <FormLabel fontSize="sm">
                  Current Tax Bracket
                  <Tooltip label="Your marginal federal income tax rate today" placement="top">
                    <Icon as={FiInfo} ml={1} boxSize={3} color="gray.400" />
                  </Tooltip>
                </FormLabel>
                <Select
                  size="sm"
                  value={currentBracket}
                  onChange={(e) => setCurrentBracket(Number(e.target.value))}
                >
                  {TAX_BRACKETS.map((b) => (
                    <option key={b} value={b}>{b}%</option>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel fontSize="sm">
                  Expected Retirement Tax Bracket
                  <Tooltip label="Your estimated marginal rate in retirement" placement="top">
                    <Icon as={FiInfo} ml={1} boxSize={3} color="gray.400" />
                  </Tooltip>
                </FormLabel>
                <Select
                  size="sm"
                  value={retirementBracket}
                  onChange={(e) => setRetirementBracket(Number(e.target.value))}
                >
                  {TAX_BRACKETS.map((b) => (
                    <option key={b} value={b}>{b}%</option>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <HStack justify="space-between">
                  <FormLabel fontSize="sm" mb={0}>
                    Annual Conversion Amount
                  </FormLabel>
                  <Text fontSize="sm" fontWeight="semibold" color="brand.600">
                    {formatCurrency(annualConversion)}
                  </Text>
                </HStack>
                <Slider
                  min={1000}
                  max={Math.max(1000, Math.min(100000, traditionalBalance))}
                  step={1000}
                  value={annualConversion}
                  onChange={setAnnualConversion}
                  mt={2}
                >
                  <SliderTrack>
                    <SliderFilledTrack bg="brand.500" />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
                <HStack justify="space-between" mt={1}>
                  <Text fontSize="xs" color="gray.500">$1K</Text>
                  <Text fontSize="xs" color="gray.500">
                    {formatCurrency(Math.max(1000, Math.min(100000, traditionalBalance)))}
                  </Text>
                </HStack>
              </FormControl>

              <FormControl>
                <HStack justify="space-between">
                  <FormLabel fontSize="sm" mb={0}>
                    Expected Annual Return
                  </FormLabel>
                  <Text fontSize="sm" fontWeight="semibold" color="brand.600">
                    {annualReturn}%
                  </Text>
                </HStack>
                <Slider
                  min={3}
                  max={12}
                  step={0.5}
                  value={annualReturn}
                  onChange={setAnnualReturn}
                  mt={2}
                >
                  <SliderTrack>
                    <SliderFilledTrack bg="brand.500" />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
                <HStack justify="space-between" mt={1}>
                  <Text fontSize="xs" color="gray.500">3%</Text>
                  <Text fontSize="xs" color="gray.500">12%</Text>
                </HStack>
              </FormControl>

              {data?.current_age && (
                <Box p={3} bg="gray.50" borderRadius="md">
                  <Text fontSize="sm" color="gray.600">
                    Current age: <strong>{data.current_age}</strong> ·{' '}
                    Years until RMD age (73): <strong>{yearsUntilRmd}</strong>
                  </Text>
                </Box>
              )}
            </VStack>
          </CardBody>
        </Card>

        {/* Key Metrics */}
        <VStack spacing={4} align="stretch">
          {/* Recommendation banner */}
          <Card
            variant="outline"
            borderColor={isConversionBeneficial ? 'green.300' : 'yellow.300'}
            bg={isConversionBeneficial ? 'green.50' : 'yellow.50'}
          >
            <CardBody>
              <HStack justify="space-between" align="start">
                <VStack align="start" spacing={1}>
                  <HStack>
                    <Badge
                      colorScheme={isConversionBeneficial ? 'green' : 'yellow'}
                      fontSize="sm"
                      px={2}
                      py={0.5}
                    >
                      {isConversionBeneficial ? 'Recommended' : 'Consider Carefully'}
                    </Badge>
                  </HStack>
                  <Text fontSize="sm" color={isConversionBeneficial ? 'green.700' : 'yellow.700'}>
                    {isConversionBeneficial
                      ? `With ${annualReturn}% growth over ${yearsUntilRmd} years, your retirement tax burden will likely exceed today's conversion cost.`
                      : `At the same tax bracket, conversions offer estate planning benefits but no immediate tax savings.`}
                  </Text>
                </VStack>
              </HStack>
            </CardBody>
          </Card>

          {/* Stat cards */}
          <SimpleGrid columns={2} spacing={3}>
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Traditional Balance</StatLabel>
                  <StatNumber fontSize="lg">{formatCurrency(traditionalBalance)}</StatNumber>
                </Stat>
              </CardBody>
            </Card>

            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Projected RMD at 73 (today)</StatLabel>
                  <StatNumber fontSize="lg">
                    {data?.projected_rmd_at_73
                      ? formatCurrency(data.projected_rmd_at_73)
                      : '—'}
                  </StatNumber>
                  <StatHelpText fontSize="xs">Before conversions</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Taxes Paid on Conversions</StatLabel>
                  <StatNumber fontSize="lg" color="red.600">
                    {formatCurrency(totalTaxesPaid)}
                  </StatNumber>
                  <StatHelpText fontSize="xs">
                    {formatCurrency(annualConversion * (currentBracket / 100))}/yr × {yearsConverting} yrs
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Annual RMD Tax Savings</StatLabel>
                  <StatNumber fontSize="lg" color="green.600">
                    {formatCurrency(annualRmdTaxSavings)}
                  </StatNumber>
                  <StatHelpText fontSize="xs">
                    {formatCurrency(annualRmdReduction)} less RMD/yr
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* Break-even highlight */}
          <Card variant="outline" borderColor="brand.300">
            <CardBody>
              <Stat>
                <StatLabel>Break-Even Point</StatLabel>
                {breakEvenYears !== null && annualRmdTaxSavings > 0 ? (
                  <>
                    <StatNumber color="brand.600">
                      {breakEvenYears} {breakEvenYears === 1 ? 'year' : 'years'} after RMD begins
                    </StatNumber>
                    <StatHelpText>
                      RMD tax savings cover conversion costs by age {73 + breakEvenYears}
                    </StatHelpText>
                  </>
                ) : (
                  <StatNumber color="gray.500">N/A</StatNumber>
                )}
              </Stat>
            </CardBody>
          </Card>
        </VStack>
      </SimpleGrid>

      {/* Account list */}
      {data?.accounts && data.accounts.length > 0 && (
        <Card variant="outline">
          <CardBody>
            <Heading size="sm" mb={3}>Traditional Accounts Included</Heading>
            <HStack spacing={4} flexWrap="wrap">
              {data.accounts.map((acc) => (
                <HStack key={acc.id} spacing={2}>
                  <Badge colorScheme="purple" variant="subtle">
                    {acc.type === 'retirement_401k' ? '401(k)' : 'IRA'}
                  </Badge>
                  <Text fontSize="sm">{acc.name}</Text>
                  <Text fontSize="sm" fontWeight="semibold">
                    {formatCurrency(acc.balance)}
                  </Text>
                </HStack>
              ))}
            </HStack>
          </CardBody>
        </Card>
      )}

      {/* Break-even table */}
      <Card variant="outline">
        <CardBody>
          <Heading size="sm" mb={1}>Retirement Break-Even Table</Heading>
          <Text fontSize="xs" color="gray.600" mb={4}>
            Cumulative RMD tax savings vs. taxes paid on conversions. Positive = conversion has paid off.
          </Text>
          <Box overflowX="auto">
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Year in Retirement</Th>
                  <Th>Age</Th>
                  <Th isNumeric>Cumulative RMD Tax Saved</Th>
                  <Th isNumeric>Conversion Taxes Paid</Th>
                  <Th isNumeric>Net Position</Th>
                </Tr>
              </Thead>
              <Tbody>
                {breakEvenRows.map((row) => {
                  const isPaidOff = row.net >= 0;
                  return (
                    <Tr
                      key={row.year}
                      bg={isPaidOff ? 'green.50' : undefined}
                      fontWeight={isPaidOff && breakEvenYears === row.year ? 'bold' : undefined}
                    >
                      <Td>Year {row.year}</Td>
                      <Td>Age {73 + row.year}</Td>
                      <Td isNumeric color="green.700">
                        {formatCurrencyPrecise(row.cumulativeSaved)}
                      </Td>
                      <Td isNumeric color="red.600">
                        {formatCurrencyPrecise(totalTaxesPaid)}
                      </Td>
                      <Td isNumeric>
                        <HStack justify="flex-end" spacing={1}>
                          <StatArrow type={isPaidOff ? 'increase' : 'decrease'} />
                          <Text color={isPaidOff ? 'green.700' : 'red.600'}>
                            {formatCurrencyPrecise(Math.abs(row.net))}
                          </Text>
                          {isPaidOff && breakEvenYears === row.year && (
                            <Badge colorScheme="green" fontSize="xs">Break-even!</Badge>
                          )}
                        </HStack>
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          </Box>
          <Text fontSize="xs" color="gray.500" mt={3}>
            * This analysis uses simplified estimates. Consult a tax advisor before making conversion decisions.
            RMD calculation uses IRS life expectancy factor of 26.5 at age 73.
          </Text>
        </CardBody>
      </Card>
    </VStack>
  );
};
