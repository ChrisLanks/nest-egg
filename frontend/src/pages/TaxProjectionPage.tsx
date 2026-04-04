/**
 * Tax Projection & Quarterly Estimated Taxes page.
 *
 * Automatically annualises income from YTD transaction data.
 * User can provide additional income sources and override deductions.
 * Shows federal tax estimate, bracket breakdown, and quarterly payment
 * schedule (IRS Form 1040-ES due dates).
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
  Collapse,
  Container,
  Divider,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Icon,
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
  Tooltip,
  Tr,
  VStack,
  useColorModeValue,
} from "@chakra-ui/react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { FiChevronDown, FiChevronUp, FiInfo } from "react-icons/fi";
import {
  financialPlanningApi,
  type TaxProjectionParams,
  type WithholdingCheckRequest,
} from "../api/financialPlanning";
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

const fmtPct = (n: number) => `${(n * 100).toFixed(1)}%`;

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

export const TaxProjectionPage = () => {
  const { selectedUserId } = useUserView();
  const [showW4, setShowW4] = useState(true);
  const [w4Salary, setW4Salary] = useState("");
  const [w4YtdWithheld, setW4YtdWithheld] = useState("");
  const [w4OtherIncome, setW4OtherIncome] = useState("");
  const activeBracketBg = useColorModeValue("orange.50", "orange.900");

  const [filingStatus, setFilingStatus] = useLocalStorage<"single" | "married">(
    "tax-filing-status",
    "single",
  );
  const [selfEmploymentIncome, setSelfEmploymentIncome] = useLocalStorage(
    "tax-se-income",
    "",
  );
  const [capitalGains, setCapitalGains] = useLocalStorage(
    "tax-capital-gains",
    "",
  );
  const [additionalDeductions, setAdditionalDeductions] = useLocalStorage(
    "tax-additional-deductions",
    "",
  );
  const [priorYearTax, setPriorYearTax] = useLocalStorage(
    "tax-prior-year-tax",
    "",
  );
  const [selectedState, setSelectedState] = useLocalStorage(
    "tax-state",
    "",
  );

  const params: TaxProjectionParams = {
    user_id: selectedUserId || undefined,
    filing_status: filingStatus,
    self_employment_income: selfEmploymentIncome
      ? parseFloat(selfEmploymentIncome)
      : undefined,
    estimated_capital_gains: capitalGains
      ? parseFloat(capitalGains)
      : undefined,
    additional_deductions: additionalDeductions
      ? parseFloat(additionalDeductions)
      : undefined,
    prior_year_tax: priorYearTax ? parseFloat(priorYearTax) : undefined,
    state: selectedState || undefined,
  };

  // Debounce params so the query only fires after 500ms of inactivity
  const [debouncedParams, setDebouncedParams] = useState(params);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedParams(params), 500);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(params)]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["tax-projection", selectedUserId, debouncedParams],
    queryFn: () => financialPlanningApi.getTaxProjection(debouncedParams),
    placeholderData: (prev) => prev,
  });

  const monthsRemaining = Math.max(0, 12 - new Date().getMonth());
  const w4Mutation = useMutation({
    mutationFn: (req: WithholdingCheckRequest) =>
      financialPlanningApi.checkWithholding(req),
  });

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">Tax Projection</Heading>
          <Text color="text.secondary" mt={1}>
            Estimated {new Date().getFullYear()} federal income tax and
            quarterly payment schedule. Income is auto-sourced from your
            year-to-date transaction data.
          </Text>
        </Box>

        {/* Inputs */}
        <Card variant="outline" w="full">
          <CardHeader pb={0}>
            <Heading size="sm">Adjustments</Heading>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
              <FormControl>
                <FormLabel fontSize="xs">
                  Filing Status
                  <InfoTip label="How you file your federal taxes. 'Married Filing Jointly' combines both spouses' income but also doubles the standard deduction and uses wider tax brackets — usually the most favorable option for couples." />
                </FormLabel>
                <Select
                  size="sm"
                  value={filingStatus}
                  onChange={(e) =>
                    setFilingStatus(e.target.value as "single" | "married")
                  }
                >
                  <option value="single">Single</option>
                  <option value="married">Married Filing Jointly</option>
                </Select>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs">
                  Self-Employment Income
                  <InfoTip label="Money you earn from freelancing, a side business, or as an independent contractor — income where no employer withholds taxes for you. This is taxed at a higher rate because you pay both the employee and employer portions of Social Security and Medicare (15.3% SE tax)." />
                </FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>$</InputLeftAddon>
                  <Input
                    type="number"
                    placeholder="0"
                    value={selfEmploymentIncome}
                    onChange={(e) => setSelfEmploymentIncome(e.target.value)}
                  />
                </InputGroup>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs">
                  Estimated Capital Gains
                  <InfoTip label="Profit from selling investments (stocks, funds, real estate) held longer than one year. Long-term capital gains are taxed at lower rates (0%, 15%, or 20%) than regular income." />
                </FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>$</InputLeftAddon>
                  <Input
                    type="number"
                    placeholder="0"
                    value={capitalGains}
                    onChange={(e) => setCapitalGains(e.target.value)}
                  />
                </InputGroup>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs">
                  Additional Deductions
                  <InfoTip label="Extra deductions beyond the standard deduction — for example mortgage interest, charitable donations, or student loan interest. Only enter this if you plan to itemize and your total itemized deductions exceed the standard deduction." />
                </FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>$</InputLeftAddon>
                  <Input
                    type="number"
                    placeholder="Mortgage interest, charitable, etc."
                    value={additionalDeductions}
                    onChange={(e) => setAdditionalDeductions(e.target.value)}
                  />
                </InputGroup>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs">
                  Prior Year Total Tax (for safe harbor)
                  <InfoTip label="The total federal tax you paid last year (from your prior year Form 1040, line 24). The IRS 'safe harbor' rule says you won't owe a penalty if you pay at least 100% of last year's tax (110% if your income exceeds $150k). Enter this to see if your projected payments are on track." />
                </FormLabel>
                <InputGroup size="sm">
                  <InputLeftAddon>$</InputLeftAddon>
                  <Input
                    type="number"
                    placeholder="Optional"
                    value={priorYearTax}
                    onChange={(e) => setPriorYearTax(e.target.value)}
                  />
                </InputGroup>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="xs">
                  State
                  <InfoTip label="Select your state to include a state income tax estimate alongside the federal estimate. Uses simplified effective rates at ~$75k AGI (Adjusted Gross Income — your total income minus certain deductions). No-income-tax states (FL, TX, WA, etc.) show $0." />
                </FormLabel>
                <Select
                  size="sm"
                  value={selectedState}
                  onChange={(e) => setSelectedState(e.target.value)}
                  placeholder="None (federal only)"
                >
                  <option value="AL">Alabama</option>
                  <option value="AK">Alaska (no income tax)</option>
                  <option value="AZ">Arizona</option>
                  <option value="AR">Arkansas</option>
                  <option value="CA">California</option>
                  <option value="CO">Colorado</option>
                  <option value="CT">Connecticut</option>
                  <option value="DE">Delaware</option>
                  <option value="DC">Washington D.C.</option>
                  <option value="FL">Florida (no income tax)</option>
                  <option value="GA">Georgia</option>
                  <option value="HI">Hawaii</option>
                  <option value="ID">Idaho</option>
                  <option value="IL">Illinois</option>
                  <option value="IN">Indiana</option>
                  <option value="IA">Iowa</option>
                  <option value="KS">Kansas</option>
                  <option value="KY">Kentucky</option>
                  <option value="LA">Louisiana</option>
                  <option value="ME">Maine</option>
                  <option value="MD">Maryland</option>
                  <option value="MA">Massachusetts</option>
                  <option value="MI">Michigan</option>
                  <option value="MN">Minnesota</option>
                  <option value="MS">Mississippi</option>
                  <option value="MO">Missouri</option>
                  <option value="MT">Montana</option>
                  <option value="NE">Nebraska</option>
                  <option value="NV">Nevada (no income tax)</option>
                  <option value="NH">New Hampshire (no income tax)</option>
                  <option value="NJ">New Jersey</option>
                  <option value="NM">New Mexico</option>
                  <option value="NY">New York</option>
                  <option value="NC">North Carolina</option>
                  <option value="ND">North Dakota</option>
                  <option value="OH">Ohio</option>
                  <option value="OK">Oklahoma</option>
                  <option value="OR">Oregon</option>
                  <option value="PA">Pennsylvania</option>
                  <option value="RI">Rhode Island</option>
                  <option value="SC">South Carolina</option>
                  <option value="SD">South Dakota (no income tax)</option>
                  <option value="TN">Tennessee (no income tax)</option>
                  <option value="TX">Texas (no income tax)</option>
                  <option value="UT">Utah</option>
                  <option value="VT">Vermont</option>
                  <option value="VA">Virginia</option>
                  <option value="WA">Washington (no income tax)</option>
                  <option value="WV">West Virginia</option>
                  <option value="WI">Wisconsin</option>
                  <option value="WY">Wyoming (no income tax)</option>
                </Select>
              </FormControl>
            </SimpleGrid>
          </CardBody>
        </Card>

        {/* Loading */}
        {isLoading && (
          <Center w="full" py={8}>
            <Spinner size="lg" color="brand.500" />
          </Center>
        )}
        {isError && (
          <Alert status="error" borderRadius="lg" w="full">
            <AlertIcon />
            Failed to load tax projection. Please try again.
          </Alert>
        )}

        {/* Results */}
        {data && (
          <>
            {/* Summary stats */}
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} w="full">
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Total Tax
                      <InfoTip label="Estimated federal income tax for the full year — includes ordinary income tax, self-employment tax, and any long-term capital gains tax. Does not include state taxes." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {fmt(data.total_tax_before_credits)}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Effective Rate
                      <InfoTip label="Your average tax rate — total tax divided by total gross income. This is how much of every dollar you earned actually goes to federal taxes. Most people's effective rate is well below their marginal (top bracket) rate." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {fmtPct(data.effective_rate)}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Marginal Rate
                      <InfoTip label="The tax rate on your next dollar of income — the highest bracket you fall into. This is the rate that matters for decisions like whether to take a bonus, do a Roth conversion, or harvest capital gains." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {fmtPct(data.marginal_rate)}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel>
                      Taxable Income
                      <InfoTip label="The portion of your income that is actually subject to tax after deductions. Federal brackets are applied to this number, not your gross income." />
                    </StatLabel>
                    <StatNumber fontSize="lg">
                      {fmt(data.taxable_income)}
                    </StatNumber>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>

            {/* Summary narrative */}
            <Alert status="info" borderRadius="lg" w="full">
              <AlertIcon />
              <Text fontSize="sm">{data.summary}</Text>
            </Alert>

            {/* Safe harbor */}
            {data.safe_harbour_amount != null && (
              <Alert
                status={data.safe_harbour_met ? "success" : "warning"}
                borderRadius="lg"
                w="full"
              >
                <AlertIcon />
                <Text fontSize="sm">
                  Safe harbor amount (100% of prior year):{" "}
                  {fmt(data.safe_harbour_amount)}.{" "}
                  {data.safe_harbour_met
                    ? "Your projected tax is within safe harbor — no underpayment penalty expected."
                    : "Your projected tax exceeds safe harbor — consider increasing quarterly payments."}
                </Text>
              </Alert>
            )}

            <Divider />

            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6} w="full">
              {/* Income & deductions breakdown */}
              <Card variant="outline">
                <CardHeader pb={0}>
                  <Heading size="sm">Income &amp; Deductions</Heading>
                </CardHeader>
                <CardBody>
                  <VStack align="start" spacing={2} fontSize="sm">
                    <HStack justify="space-between" w="full">
                      <Text color="text.secondary">
                        Ordinary Income
                        <InfoTip label="Your projected annual salary or wages (W-2 income — the form your employer sends at year-end showing what you earned and what was withheld), annualized from your year-to-date transactions." />
                      </Text>
                      <Text fontWeight="semibold">
                        {fmt(data.ordinary_income)}
                      </Text>
                    </HStack>
                    {data.self_employment_income > 0 && (
                      <HStack justify="space-between" w="full">
                        <Text color="text.secondary">
                          Self-Employment Income
                        </Text>
                        <Text>{fmt(data.self_employment_income)}</Text>
                      </HStack>
                    )}
                    {data.estimated_capital_gains > 0 && (
                      <HStack justify="space-between" w="full">
                        <Text color="text.secondary">Capital Gains</Text>
                        <Text>{fmt(data.estimated_capital_gains)}</Text>
                      </HStack>
                    )}
                    <HStack justify="space-between" w="full">
                      <Text color="text.secondary">Total Gross Income</Text>
                      <Text fontWeight="semibold">
                        {fmt(data.total_gross_income)}
                      </Text>
                    </HStack>
                    <Divider />
                    <HStack justify="space-between" w="full">
                      <Text color="text.secondary">
                        Standard Deduction
                        <InfoTip label="A flat dollar amount the IRS lets you subtract from income before calculating taxes — no receipts needed. For 2024 it's $14,600 (single) or $29,200 (married filing jointly). Most people take this instead of itemizing." />
                      </Text>
                      <Text color="green.600">
                        −{fmt(data.standard_deduction)}
                      </Text>
                    </HStack>
                    {data.se_deduction > 0 && (
                      <HStack justify="space-between" w="full">
                        <Text color="text.secondary">
                          SE Tax Deduction
                          <InfoTip label="Self-employed people pay the full 15.3% Social Security + Medicare tax, but the IRS lets you deduct half of that (the 'employer' share) from your income before calculating income tax." />
                        </Text>
                        <Text color="green.600">−{fmt(data.se_deduction)}</Text>
                      </HStack>
                    )}
                    {data.additional_deductions > 0 && (
                      <HStack justify="space-between" w="full">
                        <Text color="text.secondary">
                          Additional Deductions
                        </Text>
                        <Text color="green.600">
                          −{fmt(data.additional_deductions)}
                        </Text>
                      </HStack>
                    )}
                    <HStack justify="space-between" w="full">
                      <Text fontWeight="semibold">Taxable Income</Text>
                      <Text fontWeight="bold">{fmt(data.taxable_income)}</Text>
                    </HStack>
                    <Divider />
                    <HStack justify="space-between" w="full">
                      <Text color="text.secondary">Ordinary Tax</Text>
                      <Text>{fmt(data.ordinary_tax)}</Text>
                    </HStack>
                    {data.se_tax > 0 && (
                      <HStack justify="space-between" w="full">
                        <Text color="text.secondary">
                          SE Tax (15.3%)
                          <InfoTip label="Self-employment tax covers Social Security (12.4%) and Medicare (2.9%) — totaling 15.3%. Employees split this with their employer; self-employed individuals pay the full amount." />
                        </Text>
                        <Text>{fmt(data.se_tax)}</Text>
                      </HStack>
                    )}
                    {data.ltcg_tax > 0 && (
                      <HStack justify="space-between" w="full">
                        <Text color="text.secondary">
                          LTCG Tax
                          <InfoTip label="Long-Term Capital Gains tax on investments held over one year. Taxed at preferential rates (0%, 15%, or 20% depending on total income) — much lower than ordinary income tax rates." />
                        </Text>
                        <Text>{fmt(data.ltcg_tax)}</Text>
                      </HStack>
                    )}
                    <HStack justify="space-between" w="full">
                      <Text fontWeight="semibold">Total Federal Tax</Text>
                      <Text fontWeight="bold" color="red.500">
                        {fmt(data.total_tax_before_credits)}
                      </Text>
                    </HStack>
                    {data.state && (
                      <>
                        <HStack justify="space-between" w="full">
                          <Text color="text.secondary">
                            State Tax ({data.state})
                            <InfoTip label={`Simplified state income tax estimate for ${data.state} using an effective rate of ${(data.state_tax_rate * 100).toFixed(2)}% applied to taxable income. Approximate only — does not account for state-specific deductions or credits.`} />
                          </Text>
                          <Text color="red.500">
                            {fmt(data.state_tax)}
                          </Text>
                        </HStack>
                        <Divider />
                        <HStack justify="space-between" w="full">
                          <Text fontWeight="semibold">
                            Combined Total
                            <InfoTip label="Federal + state income tax combined. This is the total estimated tax burden across both levels." />
                          </Text>
                          <Text fontWeight="bold" color="red.600" fontSize="md">
                            {fmt(data.combined_tax)}
                          </Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text color="text.secondary" fontSize="xs">
                            Combined effective rate
                          </Text>
                          <Text fontSize="xs" color="text.secondary">
                            {fmtPct(data.combined_effective_rate)}
                          </Text>
                        </HStack>
                      </>
                    )}
                  </VStack>
                </CardBody>
              </Card>

              {/* Bracket breakdown */}
              <Card variant="outline">
                <CardHeader pb={0}>
                  <Heading size="sm">
                    Bracket Breakdown
                    <InfoTip label="The U.S. uses a progressive tax system — you only pay each rate on the income within that bracket, not on your full income. For example, if you're in the 22% bracket, only the income above the 12% bracket cutoff is taxed at 22%." />
                  </Heading>
                </CardHeader>
                <CardBody overflowX="auto">
                  <Table size="sm">
                    <Thead>
                      <Tr>
                        <Th>Rate</Th>
                        <Th isNumeric>
                          Income in Bracket
                          <InfoTip label="The slice of your taxable income that falls within this tax bracket." />
                        </Th>
                        <Th isNumeric>Tax Owed</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {data.bracket_breakdown.map((b, i) => (
                        <Tr
                          key={i}
                          bg={
                            i === data.bracket_breakdown.length - 1
                              ? activeBracketBg
                              : undefined
                          }
                        >
                          <Td>
                            <Badge
                              colorScheme={
                                b.rate >= 0.32
                                  ? "red"
                                  : b.rate >= 0.22
                                    ? "orange"
                                    : "green"
                              }
                            >
                              {fmtPct(b.rate)}
                            </Badge>
                          </Td>
                          <Td isNumeric>{fmt(b.income_in_bracket)}</Td>
                          <Td isNumeric>{fmt(b.tax_owed)}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </CardBody>
              </Card>
            </SimpleGrid>

            {/* Quarterly payment schedule */}
            <Card variant="outline" w="full">
              <CardHeader pb={0}>
                <HStack justify="space-between">
                  <Heading size="sm">
                    Quarterly Estimated Payments (Form 1040-ES)
                    <InfoTip label="If you have income without tax withholding (self-employment, investments, rental income), the IRS requires you to pay taxes in four installments throughout the year. Missing or underpaying these can result in a penalty." />
                  </Heading>
                  <Text fontSize="xs" color="text.secondary">
                    Total: {fmt(data.total_quarterly_due)}
                  </Text>
                </HStack>
              </CardHeader>
              <CardBody overflowX="auto">
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Quarter</Th>
                      <Th>
                        Due Date
                        <InfoTip label="IRS 1040-ES payment deadlines. Q1 covers Jan–Mar (due April 15), Q2 covers Apr–May (due June 15), Q3 covers Jun–Aug (due Sept 15), Q4 covers Sep–Dec (due Jan 15 of next year)." />
                      </Th>
                      <Th isNumeric>Amount Due</Th>
                      <Th>Status</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {data.quarterly_payments.map((q) => (
                      <Tr key={q.quarter}>
                        <Td fontWeight="semibold">{q.quarter}</Td>
                        <Td>{q.due_date}</Td>
                        <Td isNumeric>{fmt(q.amount_due)}</Td>
                        <Td>
                          <Badge
                            colorScheme={q.paid ? "green" : "gray"}
                            variant="subtle"
                          >
                            {q.paid ? "paid" : "pending"}
                          </Badge>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </CardBody>
            </Card>
          </>
        )}
        {/* W-4 Withholding Check */}
        <Card variant="outline" w="full">
          <CardHeader
            pb={0}
            cursor="pointer"
            onClick={() => setShowW4((v) => !v)}
          >
            <HStack justify="space-between">
              <Heading size="sm">
                W-4 Withholding Check
                <InfoTip label="For salaried employees (W-2 workers): enter your salary and year-to-date federal tax withheld to see if you're on track. W-4 is the form you file with your employer to set how much tax to withhold from each paycheck. If you're under-withheld, we'll show the extra amount to add on W-4 Line 4(c)." />
              </Heading>
              <Icon as={showW4 ? FiChevronUp : FiChevronDown} />
            </HStack>
          </CardHeader>
          <Collapse in={showW4}>
            <CardBody>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
                <FormControl>
                  <FormLabel fontSize="xs">Annual Salary</FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder="75000"
                      value={w4Salary}
                      onChange={(e) => setW4Salary(e.target.value)}
                    />
                  </InputGroup>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="xs">
                    YTD Federal Tax Withheld
                    <InfoTip label="From your most recent pay stub — usually labeled 'Federal Income Tax' in the withholding section." />
                  </FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder="0"
                      value={w4YtdWithheld}
                      onChange={(e) => setW4YtdWithheld(e.target.value)}
                    />
                  </InputGroup>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="xs">
                    Other Income (investments, side work)
                    <InfoTip label="Income from sources that aren't subject to employer withholding. This may increase your tax owed." />
                  </FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder="0"
                      value={w4OtherIncome}
                      onChange={(e) => setW4OtherIncome(e.target.value)}
                    />
                  </InputGroup>
                </FormControl>
              </SimpleGrid>
              <Tooltip
                label={!w4Salary ? "Enter your annual salary above to run the withholding check" : ""}
                isDisabled={!!w4Salary}
                placement="top"
                hasArrow
              >
                <Box display="inline-block">
                  <Button
                    size="sm"
                    colorScheme="brand"
                    isLoading={w4Mutation.isPending}
                    isDisabled={!w4Salary}
                    onClick={() => {
                      w4Mutation.mutate({
                        filing_status: filingStatus,
                        annual_salary: parseFloat(w4Salary),
                        ytd_withheld: parseFloat(w4YtdWithheld || "0"),
                        months_remaining: monthsRemaining,
                        other_income: parseFloat(w4OtherIncome || "0"),
                      });
                    }}
                  >
                    Check Withholding
                  </Button>
                </Box>
              </Tooltip>

              {w4Mutation.data && (
                <Box mt={4}>
                  <Alert
                    status={w4Mutation.data.underpayment_risk ? "warning" : "success"}
                    borderRadius="md"
                    mb={3}
                  >
                    <AlertIcon />
                    <Box>
                      {w4Mutation.data.underpayment_risk ? (
                        <Text fontWeight="semibold">
                          Under-withholding risk — consider increasing W-4 withholding
                        </Text>
                      ) : (
                        <Text fontWeight="semibold">
                          On track — projected withholding covers your tax liability
                        </Text>
                      )}
                      {w4Mutation.data.w4_extra_amount > 0 && (
                        <Text fontSize="sm" mt={1}>
                          Add <strong>{fmt(w4Mutation.data.w4_extra_amount)}/paycheck</strong> on{" "}
                          W-4 Line 4(c) to avoid an underpayment penalty.
                        </Text>
                      )}
                    </Box>
                  </Alert>
                  <SimpleGrid columns={{ base: 2, md: 4 }} spacing={3} fontSize="sm">
                    <Box>
                      <Text color="gray.500" fontSize="xs">Projected Tax</Text>
                      <Text fontWeight="semibold">{fmt(w4Mutation.data.projected_tax)}</Text>
                    </Box>
                    <Box>
                      <Text color="gray.500" fontSize="xs">YTD Withheld</Text>
                      <Text fontWeight="semibold">{fmt(w4Mutation.data.ytd_withheld)}</Text>
                    </Box>
                    <Box>
                      <Text color="gray.500" fontSize="xs">Projected Year-End Withholding</Text>
                      <Text fontWeight="semibold">{fmt(w4Mutation.data.projected_year_end_withholding)}</Text>
                    </Box>
                    <Box>
                      <Text color="gray.500" fontSize="xs">Safe Harbor Amount</Text>
                      <Text fontWeight="semibold">{fmt(w4Mutation.data.safe_harbour_amount)}</Text>
                    </Box>
                  </SimpleGrid>
                  {w4Mutation.data.notes.length > 0 && (
                    <VStack align="start" mt={3} spacing={1}>
                      {w4Mutation.data.notes.map((note, i) => (
                        <Text key={i} fontSize="xs" color="gray.600">• {note}</Text>
                      ))}
                    </VStack>
                  )}
                </Box>
              )}
              {w4Mutation.isError && (
                <Alert status="error" mt={3} borderRadius="md">
                  <AlertIcon />
                  Failed to check withholding. Please try again.
                </Alert>
              )}
            </CardBody>
          </Collapse>
        </Card>
      </VStack>
    </Container>
  );
};

export default TaxProjectionPage;
