/**
 * Capital Gains Harvesting panel for the Investments page.
 *
 * Shows how much long-term capital gain can be realized at the 0% federal
 * LTCG rate given the user's income, lists eligible tax lots, and shows
 * YTD realized gains.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  Center,
  FormControl,
  FormLabel,
  HStack,
  Input,
  InputGroup,
  InputLeftAddon,
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
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "../../../services/api";
import { useUserView } from "../../../contexts/UserViewContext";

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);

const fmtShares = (v: number) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 }).format(v);

const fmtDays = (days: number) => {
  if (days >= 365) return `${(days / 365).toFixed(1)}y`;
  return `${days}d`;
};

interface BracketFill {
  filing_status: string;
  ltcg_0pct_ceiling: number;
  current_taxable_income: number;
  available_0pct_room: number;
  suggested_harvest_amount: number;
}

interface HarvestCandidate {
  tax_lot_id: string;
  ticker: string;
  shares: number;
  cost_basis: number;
  current_value: number;
  unrealized_gain: number;
  acquisition_date: string;
  holding_period_days: number;
  is_long_term: boolean;
}

interface YtdRealized {
  tax_year: number;
  realized_stcg: number;
  realized_ltcg: number;
  total_realized: number;
}

export default function CapitalGainsHarvestingPanel() {
  const { selectedUserId, effectiveUserId } = useUserView();
  const [income, setIncome] = useState<string>("");
  const [filingStatus, setFilingStatus] = useState("single");

  const incomeNum = parseFloat(income) || 0;
  const hasIncome = incomeNum > 0;

  const { data: bracketFill, isLoading: bracketLoading } =
    useQuery<BracketFill>({
      queryKey: ["cgh-bracket", incomeNum, filingStatus],
      queryFn: async () => {
        const res = await api.get("/capital-gains-harvesting/bracket-fill", {
          params: {
            current_income: incomeNum,
            filing_status: filingStatus,
          },
        });
        return res.data;
      },
      enabled: hasIncome,
    });

  const { data: candidates = [], isLoading: candidatesLoading } = useQuery<
    HarvestCandidate[]
  >({
    queryKey: ["cgh-candidates", effectiveUserId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (selectedUserId) params.user_id = effectiveUserId;
      const res = await api.get("/capital-gains-harvesting/candidates", {
        params,
      });
      return res.data;
    },
  });

  const { data: ytd, isLoading: ytdLoading } = useQuery<YtdRealized>({
    queryKey: ["cgh-ytd", effectiveUserId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (selectedUserId) params.user_id = effectiveUserId;
      const res = await api.get("/capital-gains-harvesting/ytd-realized", {
        params,
      });
      return res.data;
    },
  });

  return (
    <VStack spacing={6} align="stretch">
      {/* Disclaimer */}
      <Alert status="warning" variant="subtle" borderRadius="md">
        <AlertIcon />
        <Text fontSize="sm">
          This analysis is for informational purposes only and does not
          constitute tax advice. Consult a qualified tax professional before
          making investment decisions.
        </Text>
      </Alert>

      {/* YTD Realized */}
      <Box>
        <Text fontWeight="semibold" mb={3}>
          YTD Realized Gains ({ytd?.tax_year ?? new Date().getFullYear()})
        </Text>
        {ytdLoading ? (
          <Center py={4}>
            <Spinner />
          </Center>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Card variant="outline">
              <CardBody py={3}>
                <Stat>
                  <StatLabel fontSize="xs">Short-Term Gains</StatLabel>
                  <StatNumber
                    fontSize="lg"
                    color={
                      (ytd?.realized_stcg ?? 0) >= 0
                        ? "finance.positive"
                        : "finance.negative"
                    }
                  >
                    {fmt(ytd?.realized_stcg ?? 0)}
                  </StatNumber>
                  <StatHelpText fontSize="xs">Held ≤ 365 days — taxed as ordinary income</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody py={3}>
                <Stat>
                  <StatLabel fontSize="xs">Long-Term Gains</StatLabel>
                  <StatNumber
                    fontSize="lg"
                    color={
                      (ytd?.realized_ltcg ?? 0) >= 0
                        ? "finance.positive"
                        : "finance.negative"
                    }
                  >
                    {fmt(ytd?.realized_ltcg ?? 0)}
                  </StatNumber>
                  <StatHelpText fontSize="xs">Held &gt; 365 days — 0%, 15%, or 20% rate</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody py={3}>
                <Stat>
                  <StatLabel fontSize="xs">Total Realized</StatLabel>
                  <StatNumber fontSize="lg">
                    {fmt(ytd?.total_realized ?? 0)}
                  </StatNumber>
                  <StatHelpText fontSize="xs">Combined YTD realized gains</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>
        )}
      </Box>

      {/* 0% Bracket Calculator */}
      <Box>
        <Text fontWeight="semibold" mb={3}>
          0% LTCG Bracket Room
        </Text>
        <Text fontSize="sm" color="text.secondary" mb={4}>
          Long-term capital gains are taxed at 0% if your taxable income stays
          below the threshold. Enter your estimated taxable income to see how
          much gain you can realize tax-free this year.
        </Text>
        <HStack spacing={4} mb={4} flexWrap="wrap">
          <FormControl maxW="220px">
            <FormLabel fontSize="sm">Taxable Income</FormLabel>
            <InputGroup>
              <InputLeftAddon>$</InputLeftAddon>
              <Input
                type="number"
                placeholder="e.g. 75000"
                value={income}
                onChange={(e) => setIncome(e.target.value)}
              />
            </InputGroup>
          </FormControl>
          <FormControl maxW="220px">
            <FormLabel fontSize="sm">Filing Status</FormLabel>
            <Select
              value={filingStatus}
              onChange={(e) => setFilingStatus(e.target.value)}
            >
              <option value="single">Single</option>
              <option value="married_filing_jointly">Married Filing Jointly</option>
              <option value="married_filing_separately">Married Filing Separately</option>
              <option value="head_of_household">Head of Household</option>
            </Select>
          </FormControl>
        </HStack>

        {!hasIncome && (
          <Alert status="info" variant="subtle" borderRadius="md">
            <AlertIcon />
            <Text fontSize="sm">
              Enter your estimated taxable income above to see your 0% LTCG bracket room.
            </Text>
          </Alert>
        )}

        {hasIncome && bracketLoading && (
          <Center py={4}>
            <Spinner />
          </Center>
        )}

        {hasIncome && bracketFill && (
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Card variant="outline">
              <CardBody py={3}>
                <Stat>
                  <StatLabel fontSize="xs">0% Rate Ceiling</StatLabel>
                  <StatNumber fontSize="lg">{fmt(bracketFill.ltcg_0pct_ceiling)}</StatNumber>
                  <StatHelpText fontSize="xs">
                    {filingStatus === "married_filing_jointly"
                      ? "MFJ threshold (2026)"
                      : "Single threshold (2026)"}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody py={3}>
                <Stat>
                  <StatLabel fontSize="xs">Available 0% Room</StatLabel>
                  <StatNumber
                    fontSize="lg"
                    color={bracketFill.available_0pct_room > 0 ? "finance.positive" : "text.muted"}
                  >
                    {fmt(bracketFill.available_0pct_room)}
                  </StatNumber>
                  <StatHelpText fontSize="xs">
                    Before hitting the 15% LTCG rate
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody py={3}>
                <Stat>
                  <StatLabel fontSize="xs">Suggested Harvest</StatLabel>
                  <StatNumber fontSize="lg" color="brand.500">
                    {fmt(bracketFill.suggested_harvest_amount)}
                  </StatNumber>
                  <StatHelpText fontSize="xs">
                    Capped at $50,000 per year
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>
        )}
      </Box>

      {/* Harvest Candidates */}
      <Box>
        <Text fontWeight="semibold" mb={3}>
          Long-Term Gain Candidates
        </Text>
        <Text fontSize="sm" color="text.secondary" mb={4}>
          Tax lots held more than 365 days with unrealized gains above $500.
          These are eligible for gain harvesting at the 0% rate if you have
          bracket room available.
        </Text>

        {candidatesLoading ? (
          <Center py={6}>
            <Spinner />
          </Center>
        ) : candidates.length === 0 ? (
          <Alert status="info" variant="subtle" borderRadius="md">
            <AlertIcon />
            <Text fontSize="sm">
              No long-term gain candidates found. Either no tax lots are held
              longer than 365 days, or all lots have gains below $500.
            </Text>
          </Alert>
        ) : (
          <Box overflowX="auto">
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>Ticker</Th>
                  <Th isNumeric>Shares</Th>
                  <Th isNumeric>Cost Basis</Th>
                  <Th isNumeric>Current Value</Th>
                  <Th isNumeric>Unrealized Gain</Th>
                  <Th>Acquired</Th>
                  <Th>Held</Th>
                </Tr>
              </Thead>
              <Tbody>
                {candidates.map((c) => (
                  <Tr key={c.tax_lot_id}>
                    <Td>
                      <HStack spacing={2}>
                        <Text fontWeight="medium" fontSize="sm">
                          {c.ticker}
                        </Text>
                        <Badge colorScheme="green" fontSize="2xs">
                          LT
                        </Badge>
                      </HStack>
                    </Td>
                    <Td isNumeric fontSize="sm">
                      {fmtShares(c.shares)}
                    </Td>
                    <Td isNumeric fontSize="sm">
                      {fmt(c.cost_basis)}
                    </Td>
                    <Td isNumeric fontSize="sm">
                      {fmt(c.current_value)}
                    </Td>
                    <Td isNumeric>
                      <Tooltip
                        label={`${((c.unrealized_gain / c.cost_basis) * 100).toFixed(1)}% gain`}
                      >
                        <Text
                          fontSize="sm"
                          color="finance.positive"
                          fontWeight="medium"
                        >
                          +{fmt(c.unrealized_gain)}
                        </Text>
                      </Tooltip>
                    </Td>
                    <Td fontSize="sm">{c.acquisition_date}</Td>
                    <Td fontSize="sm">{fmtDays(c.holding_period_days)}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        )}
      </Box>
    </VStack>
  );
}
