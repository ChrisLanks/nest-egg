/**
 * HSA Optimizer page.
 *
 * Reads the user's real HSA account(s) from the accounts API, then uses the
 * HSA backend endpoints to show contribution headroom, invest-vs-spend
 * projections, and the receipt shoebox.
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
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Progress,
  Select,
  SimpleGrid,
  Skeleton,
  Spinner,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Switch,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tooltip,
  Tr,
  useDisclosure,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { FiInfo, FiPaperclip, FiPlus } from "react-icons/fi";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useCurrency } from "../contexts/CurrencyContext";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Account {
  id: string;
  name: string;
  account_type: string;
  current_balance: string | number | null;
  institution_name: string | null;
}

interface UserProfile {
  birth_year: number | null;
  birth_month: number | null;
  birth_day: number | null;
}

interface YtdSummary {
  year: number;
  ytd_contributions: number;
  ytd_medical_expenses: number;
  hsa_accounts_found: number;
}

interface ContributionHeadroom {
  annual_limit: number;
  ytd_contributions: number;
  remaining_room: number;
  catch_up_eligible: boolean;
  catch_up_amount: number;
  can_contribute: boolean;
}

interface HsaProjection {
  years: number;
  spend_strategy_balance: number;
  invest_strategy_balance: number;
  invest_advantage: number;
  annual_oop_medical_cost: number;
  break_even_note: string;
}

interface Receipt {
  id: string;
  expense_date: string;
  amount: number;
  description: string;
  category: string | null;
  is_reimbursed: boolean;
  reimbursed_at: string | null;
  tax_year: number;
  notes: string | null;
  file_name: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(v);

/** Safely convert a Decimal-serialized string or number to a JS float. */
function toFloat(v: string | number | null | undefined): number {
  if (v === null || v === undefined) return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

/** Calculate age from birth_year, birth_month (1-based), birth_day. */
function calcAge(year: number, month: number, day: number): number {
  const today = new Date();
  let age = today.getFullYear() - year;
  const hadBirthday =
    today.getMonth() + 1 > month ||
    (today.getMonth() + 1 === month && today.getDate() >= day);
  if (!hadBirthday) age -= 1;
  return age;
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

// ── Page ──────────────────────────────────────────────────────────────────────

export const HsaPage = () => {
  const { selectedUserId, effectiveUserId, matchesMemberFilter, memberEffectiveUserId } = useUserView();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const today = new Date();
  const currentYear = today.getFullYear();

  // User inputs (may be pre-filled from profile / ytd-summary)
  const [age, setAge] = useState<string>("");
  const [isFamily, setIsFamily] = useState(false);
  const [isDomesticPartnership, setIsDomesticPartnership] = useState(false);
  const [ytdContribs, setYtdContribs] = useState<string>("");
  const [annualContrib, setAnnualContrib] = useState<string>("");
  const [annualMedical, setAnnualMedical] = useState<string>("");
  const [projYears, setProjYears] = useState<string>("20");

  // Receipt form
  const [receiptDate, setReceiptDate] = useState(today.toISOString().slice(0, 10));
  const [receiptAmount, setReceiptAmount] = useState<string>("");
  const [receiptDesc, setReceiptDesc] = useState<string>("");
  const [receiptCategory, setReceiptCategory] = useState<string>("");
  const [receiptTaxYear, setReceiptTaxYear] = useState<string>(String(currentYear));
  const [receiptFile, setReceiptFile] = useState<File | null>(null);

  // ── Data fetching ────────────────────────────────────────────────────────

  const { data: allAccounts = [], isLoading: accountsLoading } = useQuery<Account[]>({
    queryKey: ["accounts", memberEffectiveUserId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (memberEffectiveUserId) params.user_id = memberEffectiveUserId;
      const res = await api.get("/accounts/", { params });
      return res.data;
    },
  });

  // Read age from shared userProfile cache (populated by PreferencesPage / CurrencyContext)
  const { data: userProfile } = useQuery<UserProfile>({
    queryKey: ["userProfile"],
    queryFn: async () => {
      const res = await api.get("/settings/profile");
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  // Auto-fill age when profile loads (only if the user hasn't typed anything)
  useEffect(() => {
    if (!age && userProfile?.birth_year && userProfile?.birth_month && userProfile?.birth_day) {
      const computed = calcAge(userProfile.birth_year, userProfile.birth_month, userProfile.birth_day);
      if (computed >= 18 && computed < 120) {
        setAge(String(computed));
      }
    }
  }, [userProfile]); // eslint-disable-line react-hooks/exhaustive-deps

  // YTD contributions from transactions on linked HSA accounts
  const { data: ytdSummary } = useQuery<YtdSummary>({
    queryKey: ["hsa-ytd-summary", currentYear, memberEffectiveUserId],
    queryFn: async () => {
      const params: Record<string, unknown> = { year: currentYear };
      if (memberEffectiveUserId) params.user_id = memberEffectiveUserId;
      const res = await api.get("/hsa/ytd-summary", { params });
      return res.data;
    },
  });

  // Auto-fill YTD contributions when summary loads (only if user hasn't typed)
  useEffect(() => {
    if (!ytdContribs && ytdSummary && ytdSummary.hsa_accounts_found > 0 && ytdSummary.ytd_contributions > 0) {
      setYtdContribs(String(Math.round(ytdSummary.ytd_contributions)));
    }
  }, [ytdSummary]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Derived values ───────────────────────────────────────────────────────

  const hsaAccounts = allAccounts.filter(
    (a) => a.account_type === "hsa" && matchesMemberFilter(a.user_id),
  );
  // Fix NaN: current_balance comes from API as a Decimal-serialized string
  const totalHsaBalance = hsaAccounts.reduce((s, a) => s + toFloat(a.current_balance), 0);
  const hasHsaAccounts = hsaAccounts.length > 0;
  const currentBalance = totalHsaBalance;

  const ageNum = parseInt(age) || 0;
  const ytdNum = parseFloat(ytdContribs) || 0;
  const annualContribNum = parseFloat(annualContrib) || 0;
  const annualMedicalNum = parseFloat(annualMedical) || 0;
  const projYearsNum = parseInt(projYears) || 20;

  // ── Contribution headroom ────────────────────────────────────────────────

  const { data: headroom, isLoading: headroomLoading } = useQuery<ContributionHeadroom>({
    queryKey: ["hsa-headroom", ageNum, isFamily, ytdNum, currentYear],
    queryFn: async () => {
      const res = await api.get("/hsa/contribution-headroom", {
        params: {
          age: ageNum,
          is_family: isFamily,
          ytd_contributions: ytdNum,
          year: currentYear,
        },
      });
      return res.data;
    },
    enabled: ageNum >= 18,
  });

  // ── Invest vs spend projection ───────────────────────────────────────────

  const { data: projection, isLoading: projLoading } = useQuery<HsaProjection>({
    queryKey: ["hsa-projection", currentBalance, annualContribNum, annualMedicalNum, projYearsNum],
    queryFn: async () => {
      const res = await api.get("/hsa/projection", {
        params: {
          current_balance: currentBalance,
          annual_contribution: annualContribNum,
          annual_medical: annualMedicalNum,
          years: projYearsNum,
        },
      });
      return res.data;
    },
    enabled: annualContribNum > 0,
  });

  // ── Receipts ─────────────────────────────────────────────────────────────

  const { data: receipts = [], isLoading: receiptsLoading } = useQuery<Receipt[]>({
    queryKey: ["hsa-receipts"],
    queryFn: async () => {
      const res = await api.get("/hsa/receipts");
      return res.data;
    },
  });

  const unreimbursedTotal = receipts
    .filter((r) => !r.is_reimbursed)
    .reduce((s, r) => s + r.amount, 0);

  // ── Mutations ────────────────────────────────────────────────────────────

  const createReceipt = useMutation({
    mutationFn: async () => {
      const res = await api.post("/hsa/receipts", {
        expense_date: receiptDate,
        amount: parseFloat(receiptAmount),
        description: receiptDesc,
        category: receiptCategory || null,
        tax_year: parseInt(receiptTaxYear),
      });
      const newId: string = res.data.id;

      // Upload attachment if one was selected
      if (receiptFile && newId) {
        const form = new FormData();
        form.append("file", receiptFile);
        await api.post(`/hsa/receipts/${newId}/attachment`, form, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hsa-receipts"] });
      toast({ title: "Receipt saved", status: "success", duration: 2000 });
      onClose();
      setReceiptAmount("");
      setReceiptDesc("");
      setReceiptCategory("");
      setReceiptFile(null);
    },
    onError: () => {
      toast({ title: "Failed to save receipt", status: "error", duration: 3000 });
    },
  });

  const markReimbursed = useMutation({
    mutationFn: async (id: string) => {
      await api.patch(`/hsa/receipts/${id}`, {
        is_reimbursed: true,
        reimbursed_at: today.toISOString().slice(0, 10),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hsa-receipts"] });
      toast({ title: "Marked reimbursed", status: "success", duration: 2000 });
    },
  });

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">HSA Optimizer</Heading>
          <Text color="text.secondary" mt={1}>
            Maximize your Health Savings Account's triple-tax advantage —
            tax-deductible contributions, tax-free growth, and tax-free
            withdrawals for qualified medical expenses.
          </Text>
        </Box>

        {/* No HSA account warning */}
        {!accountsLoading && !hasHsaAccounts && (
          <Alert status="info" borderRadius="lg" w="full">
            <AlertIcon />
            <AlertDescription fontSize="sm">
              No HSA accounts found. Add an HSA account on the{" "}
              <Button variant="link" size="sm" colorScheme="blue" as="a" href="/accounts">
                Accounts
              </Button>{" "}
              page to track your balance automatically.
            </AlertDescription>
          </Alert>
        )}

        {/* HSA Account Summary */}
        {hasHsaAccounts && (
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} w="full">
            {hsaAccounts.map((acc) => (
              <Card key={acc.id} variant="outline">
                <CardBody py={3}>
                  <Stat>
                    <StatLabel fontSize="xs">{acc.name}</StatLabel>
                    <Skeleton isLoaded={!accountsLoading}>
                      <StatNumber fontSize="lg">
                        {fmt(toFloat(acc.current_balance))}
                      </StatNumber>
                    </Skeleton>
                    <StatHelpText fontSize="xs">
                      {acc.institution_name ?? "HSA account"}
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            ))}
            {hsaAccounts.length > 1 && (
              <Card variant="outline" borderColor="brand.200">
                <CardBody py={3}>
                  <Stat>
                    <StatLabel fontSize="xs">Total HSA Balance</StatLabel>
                    <StatNumber fontSize="lg" color="brand.500">
                      {fmt(totalHsaBalance)}
                    </StatNumber>
                    <StatHelpText fontSize="xs">across {hsaAccounts.length} accounts</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            )}
          </SimpleGrid>
        )}

        <Divider />

        {/* Contribution Headroom */}
        <Box w="full">
          <Heading size="md" mb={1}>
            Contribution Headroom
            <InfoTip label="The IRS sets annual HSA contribution limits. For 2026: $4,300 (self-only) and $8,550 (family). If you're 55+, you can contribute an extra $1,000 catch-up. Contributions via payroll avoid FICA; direct contributions are deductible." />
          </Heading>
          <Text fontSize="sm" color="text.secondary" mb={4}>
            Enter your age and coverage type to see how much more you can contribute this year.
            {ytdSummary && ytdSummary.hsa_accounts_found > 0 && (
              <> YTD contributions and age are pre-filled from your linked accounts.</>
            )}
          </Text>

          <HStack spacing={4} mb={4} flexWrap="wrap">
            <FormControl maxW="160px">
              <FormLabel fontSize="sm">Your Age</FormLabel>
              <Input
                type="number"
                placeholder="e.g. 42"
                value={age}
                onChange={(e) => setAge(e.target.value)}
              />
            </FormControl>
            <FormControl maxW="200px">
              <FormLabel fontSize="sm">
                YTD Contributions
                {ytdSummary && ytdSummary.hsa_accounts_found > 0 && (
                  <Badge ml={2} colorScheme="blue" fontSize="xs">auto</Badge>
                )}
              </FormLabel>
              <InputGroup>
                <InputLeftAddon>$</InputLeftAddon>
                <Input
                  type="number"
                  placeholder="0"
                  value={ytdContribs}
                  onChange={(e) => setYtdContribs(e.target.value)}
                />
              </InputGroup>
            </FormControl>
            <FormControl maxW="180px" pt={6}>
              <HStack>
                <Switch
                  isChecked={isFamily}
                  onChange={(e) => {
                    setIsFamily(e.target.checked);
                    if (!e.target.checked) setIsDomesticPartnership(false);
                  }}
                  colorScheme="brand"
                />
                <FormLabel mb={0} fontSize="sm">Family plan</FormLabel>
              </HStack>
            </FormControl>
            {isFamily && (
              <FormControl maxW="260px" pt={6}>
                <HStack>
                  <Switch
                    isChecked={isDomesticPartnership}
                    onChange={(e) => setIsDomesticPartnership(e.target.checked)}
                    colorScheme="orange"
                  />
                  <Tooltip
                    label="Domestic partners are generally not IRS tax dependents. This means employer-paid DP health coverage is imputed income (taxed), and pre-tax HSA contributions for your DP's expenses may not qualify — you may owe taxes on those withdrawals."
                    hasArrow
                    maxW="320px"
                  >
                    <FormLabel mb={0} fontSize="sm" cursor="help">
                      Domestic partnership
                    </FormLabel>
                  </Tooltip>
                </HStack>
              </FormControl>
            )}
          </HStack>

          {isDomesticPartnership && (
            <Alert status="warning" borderRadius="md" mb={2}>
              <AlertIcon />
              <AlertDescription fontSize="sm">
                <strong>Domestic Partnership Tax Loop:</strong> Unless your domestic partner qualifies
                as your IRS tax dependent, the employer's cost for their health coverage is added to
                your W-2 as imputed income — you pay federal, state, and FICA taxes on it. Pre-tax
                HSA contributions covering your DP's medical expenses (not yours) are also treated as
                taxable distributions. To avoid this: (1) check if your DP qualifies as your dependent,
                (2) consider having each partner maintain separate self-only HDHP coverage + HSA, or
                (3) pay DP medical expenses out-of-pocket and use your HSA only for yourself.
              </AlertDescription>
            </Alert>
          )}

          {ageNum < 18 && (
            <Alert status="info" variant="subtle" borderRadius="md">
              <AlertIcon />
              <Text fontSize="sm">Enter your age above to calculate your contribution headroom.</Text>
            </Alert>
          )}

          {ageNum >= 18 && headroomLoading && <Spinner />}

          {ageNum >= 18 && headroom && (
            <Card variant="outline" w="full">
              <CardBody>
                <VStack align="start" spacing={4} fontSize="sm">
                  <HStack justify="space-between" w="full">
                    <Text color="text.secondary">
                      {currentYear} Limit ({isFamily ? "Family" : "Self-Only"})
                      {headroom.catch_up_eligible && " + Catch-Up"}
                    </Text>
                    <Text fontWeight="semibold">{fmt(headroom.annual_limit)}</Text>
                  </HStack>
                  <HStack justify="space-between" w="full">
                    <Text color="text.secondary">YTD Contributions</Text>
                    <Text fontWeight="semibold">{fmt(headroom.ytd_contributions)}</Text>
                  </HStack>
                  <Divider />
                  <Box w="full">
                    <HStack justify="space-between" mb={1}>
                      <Text color="text.secondary">Remaining Room</Text>
                      <Text
                        fontWeight="bold"
                        color={headroom.remaining_room > 0 ? "finance.positive" : "text.muted"}
                      >
                        {fmt(headroom.remaining_room)}
                      </Text>
                    </HStack>
                    <Progress
                      value={headroom.annual_limit > 0 ? (headroom.ytd_contributions / headroom.annual_limit) * 100 : 0}
                      colorScheme={headroom.remaining_room > 0 ? "green" : "orange"}
                      borderRadius="md"
                      size="sm"
                    />
                    <Text fontSize="xs" color="text.secondary" mt={1}>
                      {headroom.remaining_room > 0
                        ? `You can still contribute ${fmt(headroom.remaining_room)} this year.`
                        : "You've reached your annual HSA contribution limit."}
                    </Text>
                  </Box>
                  {headroom.catch_up_eligible && (
                    <Alert status="success" variant="subtle" borderRadius="md" py={2}>
                      <AlertIcon />
                      <Text fontSize="xs">
                        You qualify for a $1,000 catch-up contribution (age 55+).
                      </Text>
                    </Alert>
                  )}
                </VStack>
              </CardBody>
            </Card>
          )}
        </Box>

        <Divider />

        {/* Invest vs Spend Projection */}
        <Box w="full">
          <Heading size="md" mb={1}>
            Invest vs Spend Strategy
            <InfoTip label="Pay medical bills out-of-pocket today and let your HSA grow tax-free — you can reimburse yourself later with no deadline, as long as the expense occurred after you opened the HSA. This 'invest' strategy can produce 3–5× the balance of spending HSA funds as you go." />
          </Heading>
          <Text fontSize="sm" color="text.secondary" mb={4}>
            Compare keeping your HSA invested (paying medical costs out-of-pocket) against spending it directly.
            {hasHsaAccounts && (
              <> Your current balance of <strong>{fmt(totalHsaBalance)}</strong> is used automatically.</>
            )}
          </Text>

          <HStack spacing={4} mb={4} flexWrap="wrap">
            <FormControl maxW="200px">
              <FormLabel fontSize="sm">Annual Contribution</FormLabel>
              <InputGroup>
                <InputLeftAddon>$</InputLeftAddon>
                <Input
                  type="number"
                  placeholder="e.g. 4300"
                  value={annualContrib}
                  onChange={(e) => setAnnualContrib(e.target.value)}
                />
              </InputGroup>
            </FormControl>
            <FormControl maxW="200px">
              <FormLabel fontSize="sm">
                Annual Medical Expenses
                {ytdSummary && ytdSummary.ytd_medical_expenses > 0 && (
                  <Badge ml={2} colorScheme="blue" fontSize="xs">data available</Badge>
                )}
              </FormLabel>
              <InputGroup>
                <InputLeftAddon>$</InputLeftAddon>
                <Input
                  type="number"
                  placeholder={ytdSummary?.ytd_medical_expenses ? String(Math.round(ytdSummary.ytd_medical_expenses)) : "e.g. 2000"}
                  value={annualMedical}
                  onChange={(e) => setAnnualMedical(e.target.value)}
                />
              </InputGroup>
            </FormControl>
            <FormControl maxW="140px">
              <FormLabel fontSize="sm">Years</FormLabel>
              <Select value={projYears} onChange={(e) => setProjYears(e.target.value)}>
                {[10, 15, 20, 25, 30].map((y) => (
                  <option key={y} value={y}>{y} years</option>
                ))}
              </Select>
            </FormControl>
          </HStack>

          {!annualContribNum && (
            <Alert status="info" variant="subtle" borderRadius="md">
              <AlertIcon />
              <Text fontSize="sm">Enter your annual contribution to see the invest vs spend projection.</Text>
            </Alert>
          )}

          {annualContribNum > 0 && projLoading && <Spinner />}

          {annualContribNum > 0 && projection && (
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
              <Card variant="outline">
                <CardBody py={3}>
                  <Stat>
                    <StatLabel fontSize="xs">
                      Spend-As-You-Go
                      <InfoTip label="Pay medical bills directly from your HSA each year. Slower growth because withdrawals reduce the compounding base." />
                    </StatLabel>
                    <StatNumber fontSize="lg">{fmt(projection.spend_strategy_balance)}</StatNumber>
                    <StatHelpText fontSize="xs">after {projection.years} years</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline" borderColor="brand.200">
                <CardBody py={3}>
                  <Stat>
                    <StatLabel fontSize="xs">
                      Invest & Defer
                      <InfoTip label="Pay medical costs out-of-pocket, keep HSA fully invested. Reimburse yourself later (no deadline). Historically 3–5× the spend-as-you-go balance." />
                    </StatLabel>
                    <StatNumber fontSize="lg" color="brand.500">
                      {fmt(projection.invest_strategy_balance)}
                    </StatNumber>
                    <StatHelpText fontSize="xs">after {projection.years} years</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
              <Card variant="outline" borderColor="green.200">
                <CardBody py={3}>
                  <Stat>
                    <StatLabel fontSize="xs">
                      Invest Advantage
                      <InfoTip label="The extra wealth built by investing your HSA instead of spending it. This is the tax-free compounding benefit of the HSA's triple-tax advantage." />
                    </StatLabel>
                    <StatNumber fontSize="lg" color="finance.positive">
                      +{fmt(projection.invest_advantage)}
                    </StatNumber>
                    <StatHelpText fontSize="xs">
                      paying {fmt(projection.annual_oop_medical_cost)}/yr OOP
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>
          )}
        </Box>

        <Divider />

        {/* Receipt Shoebox */}
        <Box w="full">
          <HStack justify="space-between" mb={1}>
            <Heading size="md">
              Receipt Shoebox
              <InfoTip label="There is no deadline to reimburse yourself from your HSA for qualified medical expenses — as long as the expense was incurred after you opened the HSA. Save receipts here to claim tax-free reimbursements in future low-income years." />
            </Heading>
            <HStack spacing={3}>
              {unreimbursedTotal > 0 && (
                <Badge colorScheme="green" fontSize="sm" px={2} py={1}>
                  {fmt(unreimbursedTotal)} available to reimburse
                </Badge>
              )}
              <Button size="sm" leftIcon={<Icon as={FiPlus} />} onClick={onOpen}>
                Add Receipt
              </Button>
            </HStack>
          </HStack>
          <Text fontSize="sm" color="text.secondary" mb={4}>
            Log qualified medical expenses you paid out-of-pocket. Reimburse yourself later — tax-free — from your HSA.
          </Text>

          <Card variant="outline" w="full">
            <CardBody overflowX="auto" p={0}>
              {receiptsLoading ? (
                <Box p={6} textAlign="center"><Spinner /></Box>
              ) : receipts.length === 0 ? (
                <Box p={6} textAlign="center">
                  <Text color="text.secondary" fontSize="sm">
                    No receipts stored yet. Click "Add Receipt" to start tracking qualified medical expenses for future tax-free reimbursement.
                  </Text>
                </Box>
              ) : (
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Date</Th>
                      <Th>Description</Th>
                      <Th>Category</Th>
                      <Th isNumeric>Amount</Th>
                      <Th>Tax Year</Th>
                      <Th>Status</Th>
                      <Th />
                    </Tr>
                  </Thead>
                  <Tbody>
                    {receipts.map((r) => (
                      <Tr key={r.id} opacity={r.is_reimbursed ? 0.6 : 1}>
                        <Td fontSize="sm">{r.expense_date}</Td>
                        <Td fontSize="sm">
                          {r.description}
                          {r.file_name && (
                            <Tooltip label={r.file_name} placement="top">
                              <Icon as={FiPaperclip} ml={1} boxSize={3} color="text.muted" />
                            </Tooltip>
                          )}
                        </Td>
                        <Td fontSize="sm">{r.category ?? "—"}</Td>
                        <Td isNumeric fontSize="sm" fontWeight="medium">
                          {fmt(r.amount)}
                        </Td>
                        <Td fontSize="sm">{r.tax_year}</Td>
                        <Td>
                          <Badge
                            colorScheme={r.is_reimbursed ? "gray" : "green"}
                            fontSize="xs"
                          >
                            {r.is_reimbursed ? "Reimbursed" : "Pending"}
                          </Badge>
                        </Td>
                        <Td>
                          {!r.is_reimbursed && (
                            <Button
                              size="xs"
                              variant="ghost"
                              colorScheme="green"
                              isLoading={markReimbursed.isPending}
                              onClick={() => markReimbursed.mutate(r.id)}
                            >
                              Mark Reimbursed
                            </Button>
                          )}
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              )}
            </CardBody>
          </Card>
        </Box>

        {/* Add Receipt Modal */}
        <Modal isOpen={isOpen} onClose={onClose}>
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Add Medical Receipt</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <VStack spacing={4}>
                <FormControl isRequired>
                  <FormLabel fontSize="sm">Date</FormLabel>
                  <Input
                    type="date"
                    value={receiptDate}
                    onChange={(e) => setReceiptDate(e.target.value)}
                  />
                </FormControl>
                <FormControl isRequired>
                  <FormLabel fontSize="sm">Description</FormLabel>
                  <Input
                    placeholder="e.g. Dental cleaning"
                    value={receiptDesc}
                    onChange={(e) => setReceiptDesc(e.target.value)}
                  />
                </FormControl>
                <FormControl isRequired>
                  <FormLabel fontSize="sm">Amount</FormLabel>
                  <InputGroup>
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder="0.00"
                      value={receiptAmount}
                      onChange={(e) => setReceiptAmount(e.target.value)}
                    />
                  </InputGroup>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">Category</FormLabel>
                  <Select
                    placeholder="Select category"
                    value={receiptCategory}
                    onChange={(e) => setReceiptCategory(e.target.value)}
                  >
                    <option value="dental">Dental</option>
                    <option value="vision">Vision</option>
                    <option value="prescription">Prescription</option>
                    <option value="mental_health">Mental Health</option>
                    <option value="medical_device">Medical Device</option>
                    <option value="physician">Physician / Hospital</option>
                    <option value="other">Other</option>
                  </Select>
                </FormControl>
                <FormControl isRequired>
                  <FormLabel fontSize="sm">Tax Year</FormLabel>
                  <Select
                    value={receiptTaxYear}
                    onChange={(e) => setReceiptTaxYear(e.target.value)}
                  >
                    {[currentYear, currentYear - 1, currentYear - 2, currentYear - 3].map((y) => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </Select>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">
                    Attach Receipt
                    <Text as="span" fontSize="xs" color="text.muted" ml={2}>
                      (PDF, JPG, PNG — max 20 MB)
                    </Text>
                  </FormLabel>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/gif,image/webp,application/pdf"
                    style={{ display: "none" }}
                    onChange={(e) => setReceiptFile(e.target.files?.[0] ?? null)}
                  />
                  <HStack>
                    <Button
                      size="sm"
                      variant="outline"
                      leftIcon={<Icon as={FiPaperclip} />}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {receiptFile ? receiptFile.name : "Choose file"}
                    </Button>
                    {receiptFile && (
                      <Button size="xs" variant="ghost" onClick={() => setReceiptFile(null)}>
                        Remove
                      </Button>
                    )}
                  </HStack>
                </FormControl>
              </VStack>
            </ModalBody>
            <ModalFooter>
              <Button variant="ghost" mr={3} onClick={onClose}>
                Cancel
              </Button>
              <Button
                colorScheme="brand"
                isLoading={createReceipt.isPending}
                isDisabled={!receiptDesc || !receiptAmount || !receiptDate}
                onClick={() => createReceipt.mutate()}
              >
                Save Receipt
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </VStack>
    </Container>
  );
};

export default HsaPage;
