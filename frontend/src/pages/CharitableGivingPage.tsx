/**
 * Charitable Giving page.
 *
 * Helps users optimize their charitable strategy with tax-smart giving:
 * DAF contributions, gift bunching, qualified charitable distributions,
 * and appreciated securities.
 *
 * Donations are pulled from transactions tagged with user-selected labels.
 */

import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Checkbox,
  CheckboxGroup,
  Container,
  Divider,
  Heading,
  HStack,
  Icon,
  Input,
  InputGroup,
  InputRightAddon,
  Select,
  SimpleGrid,
  Spinner,
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
  Wrap,
  WrapItem,
} from "@chakra-ui/react";
import { useState } from "react";
import { FiInfo } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useCurrency } from "../contexts/CurrencyContext";

function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip label={label} placement="top" hasArrow maxW="260px">
      <Box as="span" display="inline-flex" ml={1} verticalAlign="middle" cursor="help">
        <Icon as={FiInfo} boxSize={3} color="text.muted" />
      </Box>
    </Tooltip>
  );
}

function fmt(n: number) {
  return n.toLocaleString("en-US", { style: "currency", currency, maximumFractionDigits: 0 });
}

interface OrgLabel {
  id: string;
  name: string;
  color?: string | null;
  is_income: boolean;
}

interface Donation {
  id: string;
  date: string | null;
  description: string;
  amount: number;
  account_id: string;
  notes: string | null;
}

interface DonationsResult {
  donations: Donation[];
  ytd_total: number;
  year: number;
}

interface BunchingResult {
  standard_deduction: number;
  filing_status: string;
  annual_giving: number;
  annual_strategy: {
    itemized_amount: number;
    tax_savings_per_year: number;
    two_year_savings: number;
  };
  bunching_strategy: {
    year1_giving: number;
    year1_tax_savings: number;
    year2_giving: number;
    year2_tax_savings: number;
    avg_annual_savings: number;
    two_year_savings: number;
  };
  bunching_advantage: number;
}

interface QcdResult {
  qcd_annual_limit: number;
  ira_balance: number;
  eligible_for_qcd: boolean | null;
  age_required: number;
  note: string;
}

export const CharitableGivingPage = () => {
  const { selectedUserId, effectiveUserId } = useUserView();
  const currentYear = new Date().getFullYear();

  // ── Label selection ─────────────────────────────────────────────────────────
  const [selectedLabelIds, setSelectedLabelIds] = useState<string[]>([]);

  // ── Bunching analysis inputs ────────────────────────────────────────────────
  const [annualGiving, setAnnualGiving] = useState("");
  const [marginalRate, setMarginalRate] = useState("22");
  const [filingStatus, setFilingStatus] = useState("single");
  const [bunchEnabled, setBunchEnabled] = useState(false);

  // ── Fetch all org labels ────────────────────────────────────────────────────
  const { data: labels = [], isLoading: labelsLoading } = useQuery<OrgLabel[]>({
    queryKey: ["charitable-labels", effectiveUserId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (selectedUserId) params.user_id = effectiveUserId;
      const { data } = await api.get("/charitable-giving/labels", { params });
      return data;
    },
    staleTime: 60_000,
  });

  // ── Fetch donations based on selected labels ────────────────────────────────
  const { data: donationsResult, isLoading: donationsLoading } = useQuery<DonationsResult>({
    queryKey: ["charitable-donations", selectedLabelIds.join(","), currentYear, effectiveUserId],
    queryFn: async () => {
      const p: Record<string, string> = {
        label_ids: selectedLabelIds.join(","),
        year: String(currentYear),
      };
      if (effectiveUserId) p.user_id = effectiveUserId;
      const { data } = await api.get("/charitable-giving/donations", { params: p });
      return data;
    },
    enabled: selectedLabelIds.length > 0,
    staleTime: 30_000,
  });

  // ── Bunching analysis ───────────────────────────────────────────────────────
  const { data: bunchResult } = useQuery<BunchingResult>({
    queryKey: ["bunching", annualGiving, marginalRate, filingStatus, effectiveUserId],
    queryFn: async () => {
      const p: Record<string, string | number> = {
        annual_giving: Number(annualGiving),
        marginal_rate: Number(marginalRate) / 100,
        filing_status: filingStatus,
      };
      if (effectiveUserId) p.user_id = effectiveUserId;
      const { data } = await api.get("/charitable-giving/bunching-analysis", { params: p });
      return data;
    },
    enabled: bunchEnabled && !!annualGiving,
    staleTime: 30_000,
  });

  // ── QCD ─────────────────────────────────────────────────────────────────────
  const { data: qcdResult } = useQuery<QcdResult>({
    queryKey: ["qcd", effectiveUserId],
    queryFn: async () => {
      const p: Record<string, string> = {};
      if (effectiveUserId) p.user_id = effectiveUserId;
      const { data } = await api.get("/charitable-giving/qcd-opportunity", { params: p });
      return data;
    },
    staleTime: 60_000,
  });

  const donations = donationsResult?.donations ?? [];
  const ytdTotal = donationsResult?.ytd_total ?? 0;

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        <Box>
          <Heading size="lg">Charitable Giving</Heading>
          <Text color="text.secondary" mt={1}>
            Optimize your charitable strategy with tax-smart giving — DAF
            contributions, gift bunching, qualified charitable distributions,
            and appreciated securities.
          </Text>
        </Box>

        {/* ── Label Selector ────────────────────────────────────────────── */}
        <Card variant="outline" w="full">
          <CardHeader pb={0}>
            <Heading size="sm">
              Charitable Labels
              <InfoTip label="Select the transaction labels you use to categorize charitable donations. Transactions tagged with these labels will appear in the donation history below." />
            </Heading>
          </CardHeader>
          <CardBody>
            {labelsLoading ? (
              <Spinner size="sm" />
            ) : labels.length === 0 ? (
              <Text fontSize="sm" color="text.secondary">
                No labels found. Create labels in the Transactions page and tag
                your charitable donations, then select them here.
              </Text>
            ) : (
              <CheckboxGroup
                value={selectedLabelIds}
                onChange={(vals) => setSelectedLabelIds(vals as string[])}
              >
                <Wrap spacing={3}>
                  {labels.map((lbl) => (
                    <WrapItem key={lbl.id}>
                      <Checkbox value={lbl.id}>
                        <HStack spacing={1}>
                          {lbl.color && (
                            <Box
                              w={3}
                              h={3}
                              borderRadius="full"
                              bg={lbl.color}
                              display="inline-block"
                            />
                          )}
                          <Text fontSize="sm">{lbl.name}</Text>
                        </HStack>
                      </Checkbox>
                    </WrapItem>
                  ))}
                </Wrap>
              </CheckboxGroup>
            )}
            {selectedLabelIds.length === 0 && labels.length > 0 && (
              <Text fontSize="xs" color="text.secondary" mt={2}>
                Select one or more labels to load donation history.
              </Text>
            )}
          </CardBody>
        </Card>

        {/* ── Donation History ──────────────────────────────────────────── */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Donation History
            <InfoTip label="Transactions tagged with your selected charitable labels for the current year." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <HStack justify="space-between">
                <Heading size="sm">YTD Giving — {currentYear}</Heading>
                <Stat textAlign="right" minW="120px">
                  <StatLabel>YTD Total</StatLabel>
                  <StatNumber fontSize="lg">
                    {selectedLabelIds.length > 0 ? fmt(ytdTotal) : "—"}
                  </StatNumber>
                  <StatHelpText>{currentYear}</StatHelpText>
                </Stat>
              </HStack>
            </CardHeader>
            <CardBody overflowX="auto">
              {donationsLoading ? (
                <Spinner size="sm" />
              ) : (
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Date</Th>
                      <Th>Organization / Description</Th>
                      <Th isNumeric>Amount</Th>
                      <Th>Notes</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {donations.length > 0 ? (
                      donations.map((d) => (
                        <Tr key={d.id}>
                          <Td>{d.date ?? "—"}</Td>
                          <Td>{d.description}</Td>
                          <Td isNumeric>{fmt(d.amount)}</Td>
                          <Td color="text.secondary">{d.notes ?? "—"}</Td>
                        </Tr>
                      ))
                    ) : (
                      <Tr>
                        <Td colSpan={4}>
                          <Text
                            color="text.secondary"
                            fontSize="sm"
                            textAlign="center"
                            py={4}
                          >
                            {selectedLabelIds.length === 0
                              ? "Select charitable labels above to load donation history."
                              : "No transactions found with the selected labels for this year."}
                          </Text>
                        </Td>
                      </Tr>
                    )}
                  </Tbody>
                </Table>
              )}
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* ── Bunching Analysis ──────────────────────────────────────────── */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Bunching Analysis
            <InfoTip label="Bunching concentrates two or more years of charitable giving into a single tax year to exceed the standard deduction threshold, then takes the standard deduction in the off year." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">Annual vs Bunched Strategy Tax Savings</Heading>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
                <Box>
                  <Text fontSize="sm" mb={1} fontWeight="medium">
                    Annual Giving Amount
                  </Text>
                  <InputGroup size="sm">
                    <Input
                      type="number"
                      placeholder="5000"
                      value={annualGiving}
                      onChange={(e) => {
                        setAnnualGiving(e.target.value);
                        setBunchEnabled(false);
                      }}
                    />
                  </InputGroup>
                </Box>
                <Box>
                  <Text fontSize="sm" mb={1} fontWeight="medium">
                    Marginal Tax Rate
                    <InfoTip label="Your federal marginal income tax rate. Common rates: 22%, 24%, 32%, 35%, 37%." />
                  </Text>
                  <InputGroup size="sm">
                    <Input
                      type="number"
                      placeholder="22"
                      value={marginalRate}
                      onChange={(e) => {
                        setMarginalRate(e.target.value);
                        setBunchEnabled(false);
                      }}
                    />
                    <InputRightAddon>%</InputRightAddon>
                  </InputGroup>
                </Box>
                <Box>
                  <Text fontSize="sm" mb={1} fontWeight="medium">
                    Filing Status
                  </Text>
                  <Select
                    size="sm"
                    value={filingStatus}
                    onChange={(e) => {
                      setFilingStatus(e.target.value);
                      setBunchEnabled(false);
                    }}
                  >
                    <option value="single">Single</option>
                    <option value="mfj">Married Filing Jointly</option>
                  </Select>
                </Box>
              </SimpleGrid>
              <Button
                size="sm"
                colorScheme="blue"
                onClick={() => setBunchEnabled(true)}
                isDisabled={!annualGiving}
                mb={4}
              >
                Analyze
              </Button>

              {bunchResult ? (
                <VStack align="stretch" spacing={3} fontSize="sm">
                  <HStack justify="space-between">
                    <Text color="text.secondary">
                      Standard Deduction ({bunchResult.filing_status === "mfj" ? "MFJ" : "Single"})
                    </Text>
                    <Text fontWeight="semibold">{fmt(bunchResult.standard_deduction)}</Text>
                  </HStack>
                  <Divider />
                  <HStack justify="space-between">
                    <Text color="text.secondary">
                      Annual Strategy — Tax Savings/yr
                      <InfoTip label="If your annual giving alone exceeds the standard deduction, you save on taxes each year. Otherwise, there is no benefit from itemizing." />
                    </Text>
                    <Text fontWeight="semibold">
                      {fmt(bunchResult.annual_strategy.tax_savings_per_year)}
                    </Text>
                  </HStack>
                  <HStack justify="space-between">
                    <Text color="text.secondary">Annual Strategy — 2-Year Total Savings</Text>
                    <Text fontWeight="semibold">
                      {fmt(bunchResult.annual_strategy.two_year_savings)}
                    </Text>
                  </HStack>
                  <Divider />
                  <HStack justify="space-between">
                    <Text color="text.secondary">
                      Bunched Strategy — Year 1 Giving
                    </Text>
                    <Text fontWeight="semibold">{fmt(bunchResult.bunching_strategy.year1_giving)}</Text>
                  </HStack>
                  <HStack justify="space-between">
                    <Text color="text.secondary">Bunched Strategy — Year 1 Tax Savings</Text>
                    <Text fontWeight="semibold" color="green.600">
                      {fmt(bunchResult.bunching_strategy.year1_tax_savings)}
                    </Text>
                  </HStack>
                  <HStack justify="space-between">
                    <Text color="text.secondary">Bunched Strategy — 2-Year Total Savings</Text>
                    <Text fontWeight="semibold" color="green.600">
                      {fmt(bunchResult.bunching_strategy.two_year_savings)}
                    </Text>
                  </HStack>
                  {bunchResult.bunching_advantage > 0 && (
                    <Box
                      bg="green.50"
                      borderRadius="md"
                      px={3}
                      py={2}
                      _dark={{ bg: "green.900" }}
                    >
                      <Text color="green.700" _dark={{ color: "green.200" }} fontWeight="semibold">
                        Bunching saves an extra {fmt(bunchResult.bunching_advantage)} over 2 years
                        compared to annual giving.
                      </Text>
                    </Box>
                  )}
                  {bunchResult.bunching_advantage <= 0 && (
                    <Text color="text.secondary" fontSize="xs">
                      At your giving level, bunching doesn't provide additional tax benefit over
                      annual giving. Consider increasing charitable giving or using a DAF.
                    </Text>
                  )}
                </VStack>
              ) : (
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  <Stat>
                    <StatLabel>
                      {currentYear} Standard Deduction (Single)
                    </StatLabel>
                    <StatNumber fontSize="lg">$15,000</StatNumber>
                    <StatHelpText>est. {currentYear} single filer</StatHelpText>
                  </Stat>
                  <Stat>
                    <StatLabel>
                      {currentYear} Standard Deduction (MFJ)
                    </StatLabel>
                    <StatNumber fontSize="lg">$30,000</StatNumber>
                    <StatHelpText>est. {currentYear} married</StatHelpText>
                  </Stat>
                </SimpleGrid>
              )}
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* ── QCD Opportunity ────────────────────────────────────────────── */}
        <Box w="full">
          <Heading size="md" mb={3}>
            QCD Opportunity
            <InfoTip label="Qualified Charitable Distributions allow IRA owners age 70.5+ to donate up to $105,000 per year (2026) directly from an IRA to a qualified charity. The distribution is excluded from gross income and satisfies RMDs." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">IRA Qualified Charitable Distributions (Age 70.5+)</Heading>
            </CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    {currentYear} QCD Annual Limit (per taxpayer)
                    <InfoTip label="The annual QCD limit is indexed to inflation. A married couple can each do $105,000 from their own IRAs." />
                  </Text>
                  <Text fontWeight="semibold">
                    {qcdResult ? fmt(qcdResult.qcd_annual_limit) : "$105,000"}
                  </Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Eligible Accounts
                    <InfoTip label="QCDs can only be made from Traditional IRAs. They cannot be made from 401(k) or 403(b) accounts directly." />
                  </Text>
                  <Badge colorScheme="blue">Traditional IRA only</Badge>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    RMD Satisfaction
                    <InfoTip label="A QCD counts toward your RMD for the year. One of the only ways to satisfy an RMD without recognizing the income." />
                  </Text>
                  <Badge colorScheme="green">Satisfies RMD</Badge>
                </HStack>
                <Divider />
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Your IRA Balance (Traditional)</Text>
                  <Text fontWeight="semibold">
                    {qcdResult && qcdResult.ira_balance > 0
                      ? fmt(qcdResult.ira_balance)
                      : "—"}
                  </Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Eligibility</Text>
                  {qcdResult?.eligible_for_qcd === true ? (
                    <Badge colorScheme="green">Eligible</Badge>
                  ) : qcdResult?.eligible_for_qcd === false ? (
                    <Badge colorScheme="red">Not yet eligible (age 70.5+ required)</Badge>
                  ) : (
                    <Text color="text.secondary" fontSize="xs">
                      {qcdResult?.note ?? "Connect a Traditional IRA and verify birthdate to check eligibility."}
                    </Text>
                  )}
                </HStack>
              </VStack>
            </CardBody>
          </Card>
        </Box>
      </VStack>
    </Container>
  );
};

export default CharitableGivingPage;
