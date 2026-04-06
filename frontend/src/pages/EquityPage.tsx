/**
 * Equity Compensation page.
 *
 * Reads stock_options and private_equity accounts from the accounts API and
 * renders a live vesting calendar, exercise modeling, and AMT exposure summary.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Container,
  Divider,
  Heading,
  HStack,
  Icon,
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
} from "@chakra-ui/react";
import { FiInfo } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useCurrency } from "../contexts/CurrencyContext";

// ── Types ────────────────────────────────────────────────────────────────────

interface VestEvent {
  date: string;   // "YYYY-MM-DD"
  quantity: number;
  notes?: string;
}

interface EquityAccount {
  id: string;
  name: string;
  account_type: "stock_options" | "private_equity";
  grant_type?: "iso" | "nso" | "rsu" | "rsa" | "profit_interest" | null;
  grant_date?: string | null;
  quantity?: number | null;
  strike_price?: number | null;
  share_price?: number | null;
  vesting_schedule?: string | null; // JSON string
  current_balance?: number | null;
  company_status?: "private" | "public" | null;
}

interface VestRow {
  accountName: string;
  grantType: string;
  vestDate: string;
  shares: number;
  sharePrice: number;
  estimatedValue: number;
  isFuture: boolean;
}

// ── Constants (mirrors financial.py EQUITY) ───────────────────────────────────

const AMT_EXEMPTION_SINGLE_2026 = 89_075;
const AMT_EXEMPTION_MFJ_2026 = 126_500;
const AMT_RATE_LOWER = 0.26;
const AMT_RATE_UPPER = 0.28;
const AMT_UPPER_THRESHOLD = 220_700; // AMTI where 28% kicks in (approx 2026)

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtShares(v: number) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(v);
}

function grantLabel(type?: string | null) {
  const map: Record<string, string> = {
    iso: "ISO",
    nso: "NSO",
    rsu: "RSU",
    rsa: "RSA",
    profit_interest: "Profits Interest",
    lp_interest: "LP Interest",
  };
  return type ? (map[type] ?? type.toUpperCase()) : "—";
}

function grantColor(type?: string | null) {
  const map: Record<string, string> = {
    iso: "blue",
    nso: "orange",
    rsu: "green",
    rsa: "purple",
    profit_interest: "gray",
    lp_interest: "teal",
  };
  return type ? (map[type] ?? "gray") : "gray";
}

function parseVesting(raw?: string | null): VestEvent[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
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

// ── Page ─────────────────────────────────────────────────────────────────────

export const EquityPage = () => {
  const { currency } = useCurrency();

  function fmt(v: number) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(v);
  }
  const { selectedUserId, effectiveUserId } = useUserView();
  const navigate = useNavigate();
  const today = new Date();

  const { data: allAccounts = [], isLoading } = useQuery<EquityAccount[]>({
    queryKey: ["accounts-equity", effectiveUserId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (selectedUserId) params.user_id = effectiveUserId;
      const res = await api.get("/accounts", { params });
      return (res.data as EquityAccount[]).filter(
        (a) => a.account_type === "stock_options" || a.account_type === "private_equity",
      );
    },
    staleTime: 5 * 60 * 1000,
  });

  // Flatten all vest events across all accounts into a sorted calendar
  const vestCalendar = useMemo<VestRow[]>(() => {
    const rows: VestRow[] = [];
    for (const acc of allAccounts) {
      const events = parseVesting(acc.vesting_schedule);
      const price = acc.share_price ?? 0;
      for (const ev of events) {
        rows.push({
          accountName: acc.name,
          grantType: grantLabel(acc.grant_type),
          vestDate: ev.date,
          shares: Number(ev.quantity),
          sharePrice: price,
          estimatedValue: Number(ev.quantity) * price,
          isFuture: ev.date >= today.toISOString().slice(0, 10),
        });
      }
    }
    return rows.sort((a, b) => a.vestDate.localeCompare(b.vestDate));
  }, [allAccounts, today]);

  const futureVests = vestCalendar.filter((r) => r.isFuture);
  const pastVests = vestCalendar.filter((r) => !r.isFuture);

  // Portfolio summary stats
  const summary = useMemo(() => {
    const totalGrants = allAccounts.length;
    const totalShares = allAccounts.reduce((s, a) => s + Number(a.quantity ?? 0), 0);
    const totalValue = allAccounts.reduce((s, a) => s + Math.abs(Number(a.current_balance ?? 0)), 0);

    const isoAccounts = allAccounts.filter((a) => a.grant_type === "iso");
    const isoShares = isoAccounts.reduce((s, a) => s + Number(a.quantity ?? 0), 0);
    const isoSpread = isoAccounts.reduce(
      (s, a) =>
        s + Number(a.quantity ?? 0) * Math.max(0, Number(a.share_price ?? 0) - Number(a.strike_price ?? 0)),
      0,
    );

    const futureVestValue = futureVests.reduce((s, r) => s + r.estimatedValue, 0);
    const futureVestShares = futureVests.reduce((s, r) => s + r.shares, 0);

    return { totalGrants, totalShares, totalValue, isoShares, isoSpread, futureVestValue, futureVestShares };
  }, [allAccounts, futureVests]);

  // AMT estimate on full ISO exercise
  const amtEstimate = useMemo(() => {
    if (summary.isoSpread <= 0) return null;
    const amti = summary.isoSpread;
    const afterExemptionSingle = Math.max(0, amti - AMT_EXEMPTION_SINGLE_2026);
    const afterExemptionMFJ = Math.max(0, amti - AMT_EXEMPTION_MFJ_2026);
    const calcAmt = (afterExemption: number) => {
      if (afterExemption <= AMT_UPPER_THRESHOLD) return afterExemption * AMT_RATE_LOWER;
      return AMT_UPPER_THRESHOLD * AMT_RATE_LOWER + (afterExemption - AMT_UPPER_THRESHOLD) * AMT_RATE_UPPER;
    };
    return {
      single: calcAmt(afterExemptionSingle),
      mfj: calcAmt(afterExemptionMFJ),
      isoSpread: summary.isoSpread,
    };
  }, [summary.isoSpread]);

  const hasAccounts = allAccounts.length > 0;

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <HStack justify="space-between" w="full" align="start">
          <Box>
            <Heading size="lg">Equity Compensation</Heading>
            <Text color="text.secondary" mt={1}>
              Track your stock options (ISO/NSO), RSUs, and equity grants. Model
              vesting schedules, exercise strategies, and AMT exposure.
            </Text>
          </Box>
          <Button size="sm" variant="outline" onClick={() => navigate("/accounts")}>
            Manage Accounts
          </Button>
        </HStack>

        {/* No accounts state */}
        {!isLoading && !hasAccounts && (
          <Alert status="info" borderRadius="lg" w="full">
            <AlertIcon />
            <AlertDescription fontSize="sm">
              No stock option or equity accounts found. Add a{" "}
              <Button variant="link" size="sm" colorScheme="blue" onClick={() => navigate("/accounts")}>
                Stock Options or Private Equity account
              </Button>{" "}
              to see your vesting calendar and tax modeling here.
            </AlertDescription>
          </Alert>
        )}

        {/* Portfolio Summary */}
        {(isLoading || hasAccounts) && (
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} w="full">
            {[
              { label: "Total Grants", value: hasAccounts ? String(summary.totalGrants) : "—", help: "accounts tracked" },
              { label: "Total Shares", value: hasAccounts ? fmtShares(summary.totalShares) : "—", help: "all grant types" },
              { label: "Portfolio Value", value: hasAccounts ? fmt(summary.totalValue) : "—", help: "at current price" },
              { label: "Future Vest Value", value: hasAccounts ? fmt(summary.futureVestValue) : "—", help: `${fmtShares(summary.futureVestShares)} shares scheduled` },
            ].map(({ label, value, help }) => (
              <Card key={label} variant="outline">
                <CardBody>
                  <Stat>
                    <StatLabel fontSize="xs">{label}</StatLabel>
                    <Skeleton isLoaded={!isLoading}>
                      <StatNumber fontSize="lg">{value}</StatNumber>
                    </Skeleton>
                    <StatHelpText fontSize="xs">{help}</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            ))}
          </SimpleGrid>
        )}

        {/* Grant Summary Table */}
        {(isLoading || hasAccounts) && (
          <Box w="full">
            <Heading size="md" mb={3}>
              Your Grants
              <InfoTip label="All stock option and equity accounts. Click Manage Accounts to edit details or add vesting schedules." />
            </Heading>
            <Card variant="outline" w="full">
              <CardBody overflowX="auto">
                <Skeleton isLoaded={!isLoading}>
                  <Table size="sm">
                    <Thead>
                      <Tr>
                        <Th>Name</Th>
                        <Th>Type</Th>
                        <Th isNumeric>Shares</Th>
                        <Th isNumeric>Strike</Th>
                        <Th isNumeric>Current Price</Th>
                        <Th isNumeric>Spread / Value</Th>
                        <Th>Status</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {allAccounts.length === 0 ? (
                        <Tr>
                          <Td colSpan={7}>
                            <Text color="text.secondary" fontSize="sm" textAlign="center" py={4}>
                              No equity grants yet.
                            </Text>
                          </Td>
                        </Tr>
                      ) : (
                        allAccounts.map((acc) => {
                          const spread =
                            (acc.grant_type === "iso" || acc.grant_type === "nso") && acc.share_price && acc.strike_price
                              ? Number(acc.share_price) - Number(acc.strike_price)
                              : null;
                          const value = Math.abs(Number(acc.current_balance ?? 0));
                          return (
                            <Tr key={acc.id}>
                              <Td fontWeight="medium">{acc.name}</Td>
                              <Td>
                                <Badge colorScheme={grantColor(acc.grant_type)} fontSize="xs">
                                  {grantLabel(acc.grant_type)}
                                </Badge>
                              </Td>
                              <Td isNumeric>{acc.quantity ? fmtShares(Number(acc.quantity)) : "—"}</Td>
                              <Td isNumeric>{acc.strike_price ? fmt(Number(acc.strike_price)) : "—"}</Td>
                              <Td isNumeric>{acc.share_price ? fmt(Number(acc.share_price)) : "—"}</Td>
                              <Td isNumeric>
                                {spread !== null ? (
                                  <Text color={spread > 0 ? "green.500" : "red.500"}>
                                    {fmt(spread)}/sh
                                  </Text>
                                ) : value > 0 ? (
                                  fmt(value)
                                ) : (
                                  "—"
                                )}
                              </Td>
                              <Td>
                                <Badge colorScheme={acc.company_status === "public" ? "green" : "gray"} fontSize="xs">
                                  {acc.company_status ?? "private"}
                                </Badge>
                              </Td>
                            </Tr>
                          );
                        })
                      )}
                    </Tbody>
                  </Table>
                </Skeleton>
              </CardBody>
            </Card>
          </Box>
        )}

        <Divider />

        {/* Vesting Calendar */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Vesting Calendar
            <InfoTip label="Upcoming vest events across all your equity grants. RSU vests are ordinary income at FMV. ISO/NSO exercise decisions carry different tax implications." />
          </Heading>
          <Card variant="outline" w="full">
            <CardBody overflowX="auto">
              <Skeleton isLoaded={!isLoading}>
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Grant</Th>
                      <Th>Type</Th>
                      <Th>Vest Date</Th>
                      <Th isNumeric>Shares</Th>
                      <Th isNumeric>Price</Th>
                      <Th isNumeric>Est. Value</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {vestCalendar.length === 0 ? (
                      <Tr>
                        <Td colSpan={6}>
                          <Text color="text.secondary" fontSize="sm" textAlign="center" py={4}>
                            {hasAccounts
                              ? "No vest events added. Edit your equity accounts and add a vesting schedule."
                              : "No equity grants added yet."}
                          </Text>
                        </Td>
                      </Tr>
                    ) : (
                      <>
                        {futureVests.length > 0 && (
                          <>
                            <Tr bg="bg.muted">
                              <Td colSpan={6}>
                                <Text fontSize="xs" fontWeight="bold" color="text.heading">Upcoming</Text>
                              </Td>
                            </Tr>
                            {futureVests.map((row, i) => (
                              <Tr key={`future-${i}`} _hover={{ bg: "bg.subtle" }}>
                                <Td fontWeight="medium">{row.accountName}</Td>
                                <Td><Badge colorScheme="blue" fontSize="xs">{row.grantType}</Badge></Td>
                                <Td>{row.vestDate}</Td>
                                <Td isNumeric>{fmtShares(row.shares)}</Td>
                                <Td isNumeric>{row.sharePrice > 0 ? fmt(row.sharePrice) : "—"}</Td>
                                <Td isNumeric color="green.500" fontWeight="semibold">
                                  {row.estimatedValue > 0 ? fmt(row.estimatedValue) : "—"}
                                </Td>
                              </Tr>
                            ))}
                          </>
                        )}
                        {pastVests.length > 0 && (
                          <>
                            <Tr bg="bg.muted">
                              <Td colSpan={6}>
                                <Text fontSize="xs" fontWeight="bold" color="text.muted">Past</Text>
                              </Td>
                            </Tr>
                            {pastVests.map((row, i) => (
                              <Tr key={`past-${i}`} opacity={0.6} _hover={{ bg: "bg.subtle" }}>
                                <Td>{row.accountName}</Td>
                                <Td><Badge colorScheme="gray" fontSize="xs">{row.grantType}</Badge></Td>
                                <Td>{row.vestDate}</Td>
                                <Td isNumeric>{fmtShares(row.shares)}</Td>
                                <Td isNumeric>{row.sharePrice > 0 ? fmt(row.sharePrice) : "—"}</Td>
                                <Td isNumeric>{row.estimatedValue > 0 ? fmt(row.estimatedValue) : "—"}</Td>
                              </Tr>
                            ))}
                          </>
                        )}
                      </>
                    )}
                  </Tbody>
                </Table>
              </Skeleton>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* Exercise Modeling */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Exercise Modeling
            <InfoTip label="ISOs receive preferential tax treatment but trigger AMT on the spread. NSOs are taxed as ordinary income at exercise. Optimal timing depends on your income, AMT exposure, and company trajectory." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">ISO vs NSO Tax Impact Summary</Heading></CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    ISO Spread at Exercise
                    <InfoTip label="The difference between FMV and strike price at exercise. An AMT preference item — won't appear as regular income but increases your AMTI." />
                  </Text>
                  <HStack spacing={2}>
                    {summary.isoSpread > 0 && (
                      <Text fontWeight="semibold">{fmt(summary.isoSpread)} total</Text>
                    )}
                    <Badge colorScheme="blue">AMT Preference Item</Badge>
                  </HStack>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    NSO Spread at Exercise
                    <InfoTip label="NSO spread is reported as W-2 wages (employer) or self-employment income. Subject to income tax and FICA." />
                  </Text>
                  <Badge colorScheme="orange">Ordinary Income</Badge>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    RSU Vesting
                    <InfoTip label="RSU vests are taxed as ordinary income at FMV on vest date. Cost basis established at vest price; future appreciation taxed as capital gains." />
                  </Text>
                  <Badge colorScheme="orange">Ordinary Income at Vest</Badge>
                </HStack>
              </VStack>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* AMT Exposure */}
        <Box w="full">
          <Heading size="md" mb={3}>
            AMT Exposure
            <InfoTip label="The Alternative Minimum Tax runs a parallel calculation. ISO exercise spreads are an AMT preference item. If tentative minimum tax exceeds regular tax, you owe the difference. AMT credits may be recoverable in future lower-income years." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">Estimated AMT Add-Back (2026)</Heading></CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">AMT Exemption — Single</Text>
                  <Text fontWeight="semibold">{fmt(AMT_EXEMPTION_SINGLE_2026)}</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">AMT Exemption — Married Filing Jointly</Text>
                  <Text fontWeight="semibold">{fmt(AMT_EXEMPTION_MFJ_2026)}</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">AMT Rate on AMTI above exemption</Text>
                  <Text fontWeight="semibold">26% / 28%</Text>
                </HStack>
                {amtEstimate && (
                  <>
                    <Divider />
                    <HStack justify="space-between" w="full">
                      <Text color="text.secondary">
                        Your ISO Spread (if fully exercised)
                        <InfoTip label="Total spread across all ISO grants at current share prices. This is the AMT preference item added to your AMTI." />
                      </Text>
                      <Text fontWeight="semibold">{fmt(amtEstimate.isoSpread)}</Text>
                    </HStack>
                    <HStack justify="space-between" w="full">
                      <Text color="text.secondary">Estimated AMT — Single</Text>
                      <Text fontWeight="semibold" color={amtEstimate.single > 0 ? "orange.500" : undefined}>
                        {fmt(amtEstimate.single)}
                      </Text>
                    </HStack>
                    <HStack justify="space-between" w="full">
                      <Text color="text.secondary">Estimated AMT — MFJ</Text>
                      <Text fontWeight="semibold" color={amtEstimate.mfj > 0 ? "orange.500" : undefined}>
                        {fmt(amtEstimate.mfj)}
                      </Text>
                    </HStack>
                    <Text fontSize="xs" color="text.secondary">
                      These estimates assume exercising all ISOs in a single year with no other AMT
                      adjustments. Partial-year exercise or spreading across years can reduce AMT
                      significantly. Consult a CPA before exercising.
                    </Text>
                  </>
                )}
                {!amtEstimate && (
                  <Text fontSize="xs" color="text.secondary">
                    {hasAccounts
                      ? "No ISO grants with a spread detected. Add strike price and current share price to your ISO accounts to see AMT exposure."
                      : "Add ISO grant accounts with strike price and current share price to calculate your estimated AMT exposure."}
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

export default EquityPage;
