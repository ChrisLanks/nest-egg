/**
 * Estate & Beneficiary Planning page.
 *
 * Wires up the full estate API:
 * - Add / remove beneficiaries per account
 * - Mark estate planning documents as complete (persisted)
 * - Estate tax exposure calculator using real net worth + user-entered overrides
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
  Checkbox,
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
  Select,
  Spinner,
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
  useToast,
} from "@chakra-ui/react";
import { FiCheckCircle, FiInfo, FiPlus, FiTrash2 } from "react-icons/fi";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "../services/api";
import { useQuery as useReactQuery } from "@tanstack/react-query";
import { BeneficiaryAuditCard } from "./BeneficiaryAuditCard";

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
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

interface Beneficiary {
  id: string;
  account_id: string | null;
  name: string;
  relationship: string;
  designation_type: string;
  percentage: number;
  dob: string | null;
  notes: string | null;
}

interface EstateDoc {
  id: string;
  document_type: string;
  last_reviewed_date: string | null;
  notes: string | null;
}

interface TaxExposureResult {
  net_worth: number;
  federal_exemption: number;
  taxable_estate: number;
  estimated_federal_tax: number;
  above_exemption: boolean;
  tcja_sunset_risk: boolean;
  sunset_note: string;
}

const DOC_TYPES = [
  {
    key: "will",
    label: "Last Will & Testament",
    description: "Directs distribution of assets not covered by beneficiary designations or trusts.",
  },
  {
    key: "trust",
    label: "Revocable Living Trust",
    description: "Avoids probate, provides privacy, and allows for incapacity planning.",
  },
  {
    key: "poa",
    label: "Durable Power of Attorney",
    description: "Authorizes someone to manage financial affairs if you become incapacitated.",
  },
  {
    key: "healthcare_directive",
    label: "Healthcare Directive / Living Will",
    description: "States your wishes for medical treatment if you cannot speak for yourself.",
  },
  {
    key: "healthcare_proxy",
    label: "Healthcare Proxy / Medical POA",
    description: "Designates someone to make medical decisions on your behalf.",
  },
  {
    key: "beneficiary_form",
    label: "Beneficiary Designations Review",
    description: "Retirement accounts and life insurance pass outside the will — review annually.",
  },
];

export const EstatePage = () => {
  const toast = useToast();
  const qc = useQueryClient();
  const { isOpen, onOpen, onClose } = useDisclosure();

  // ── Estate tax calculator inputs ────────────────────────────────────────────
  const [netWorthOverride, setNetWorthOverride] = useState("");
  const [filingStatus, setFilingStatus] = useState("single");
  const [taxCalcEnabled, setTaxCalcEnabled] = useState(false);

  // ── Add beneficiary form state ──────────────────────────────────────────────
  const [benForm, setBenForm] = useState({
    name: "",
    relationship: "spouse",
    designation_type: "primary",
    percentage: "100",
    dob: "",
    notes: "",
    account_id: "",
  });

  // ── Fetch beneficiaries ─────────────────────────────────────────────────────
  const { data: beneficiaries = [], isLoading: bensLoading } = useQuery<Beneficiary[]>({
    queryKey: ["estate-beneficiaries"],
    queryFn: async () => {
      const { data } = await api.get("/estate/beneficiaries");
      return data;
    },
    staleTime: 30_000,
  });

  // ── Fetch documents ─────────────────────────────────────────────────────────
  const { data: documents = [] } = useQuery<EstateDoc[]>({
    queryKey: ["estate-documents"],
    queryFn: async () => {
      const { data } = await api.get("/estate/documents");
      return data;
    },
    staleTime: 30_000,
  });

  // ── Fetch net worth from dashboard (for default) ────────────────────────────
  const { data: dashSummary } = useQuery<{ net_worth?: number }>({
    queryKey: ["dashboard-summary"],
    queryFn: async () => {
      const { data } = await api.get("/dashboard/summary");
      return data;
    },
    staleTime: 60_000,
  });

  // ── Fetch accounts (for beneficiary account picker) ─────────────────────────
  const { data: accounts = [] } = useQuery<{ id: string; name: string; account_type: string }[]>({
    queryKey: ["accounts"],
    queryFn: async () => {
      const { data } = await api.get("/accounts/");
      return data;
    },
    staleTime: 60_000,
  });

  // ── Estate tax exposure query ────────────────────────────────────────────────
  const effectiveNetWorth = netWorthOverride
    ? Number(netWorthOverride)
    : (dashSummary?.net_worth ?? 0);

  const { data: taxResult } = useQuery<TaxExposureResult>({
    queryKey: ["estate-tax", effectiveNetWorth, filingStatus],
    queryFn: async () => {
      const { data } = await api.get("/estate/tax-exposure", {
        params: { net_worth: effectiveNetWorth, filing_status: filingStatus },
      });
      return data;
    },
    enabled: taxCalcEnabled || effectiveNetWorth > 0,
    staleTime: 30_000,
  });

  // ── Add beneficiary mutation ─────────────────────────────────────────────────
  const addBen = useMutation({
    mutationFn: async () => {
      const body = {
        name: benForm.name,
        relationship: benForm.relationship,
        designation_type: benForm.designation_type,
        percentage: Number(benForm.percentage),
        dob: benForm.dob || null,
        notes: benForm.notes || null,
        account_id: benForm.account_id || null,
      };
      const { data } = await api.post("/estate/beneficiaries", body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["estate-beneficiaries"] });
      onClose();
      setBenForm({
        name: "", relationship: "spouse", designation_type: "primary",
        percentage: "100", dob: "", notes: "", account_id: "",
      });
      toast({ title: "Beneficiary added", status: "success", duration: 2000 });
    },
    onError: () => {
      toast({ title: "Failed to add beneficiary", status: "error", duration: 3000 });
    },
  });

  // ── Delete beneficiary mutation ──────────────────────────────────────────────
  const deleteBen = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/estate/beneficiaries/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["estate-beneficiaries"] });
      toast({ title: "Beneficiary removed", status: "info", duration: 2000 });
    },
  });

  // ── Upsert document mutation ─────────────────────────────────────────────────
  const upsertDoc = useMutation({
    mutationFn: async ({
      document_type,
      checked,
    }: {
      document_type: string;
      checked: boolean;
    }) => {
      if (checked) {
        const { data } = await api.post("/estate/documents", {
          document_type,
          last_reviewed_date: new Date().toISOString().split("T")[0],
        });
        return data;
      } else {
        // Mark unchecked by posting with null reviewed date
        const { data } = await api.post("/estate/documents", {
          document_type,
          last_reviewed_date: null,
        });
        return data;
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["estate-documents"] });
    },
  });

  const docMap = new Map(documents.map((d) => [d.document_type, d]));

  const primaryBens = beneficiaries.filter((b) => b.designation_type === "primary");
  const contingentBens = beneficiaries.filter((b) => b.designation_type === "contingent");

  // Validate primary % sums
  const primaryTotal = primaryBens.reduce((s, b) => s + b.percentage, 0);
  const primaryValid = primaryBens.length === 0 || Math.abs(primaryTotal - 100) < 0.01;

  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        <BeneficiaryAuditCard />
        <Box>
          <Heading size="lg">Estate &amp; Beneficiary Planning</Heading>
          <Text color="text.secondary" mt={1}>
            Ensure your assets go where you intend. Track beneficiary
            designations, model estate tax exposure, and monitor key planning
            documents.
          </Text>
        </Box>
        <Alert status="info" borderRadius="lg" w="full">
          <AlertIcon />
          <Text fontSize="sm">
            Estate planning is most effective when revisited after major life
            events: marriage, divorce, birth of a child, or significant asset changes.
          </Text>
        </Alert>

        {/* ── Beneficiary Coverage ──────────────────────────────────────── */}
        <Box w="full">
          <HStack justify="space-between" mb={3}>
            <Heading size="md">
              Beneficiary Designations
              <InfoTip label="Beneficiary designations on retirement accounts, life insurance, and TOD/POD bank accounts supersede your will. Accounts without a named beneficiary may pass through probate." />
            </Heading>
            <Button size="sm" leftIcon={<Icon as={FiPlus} />} colorScheme="blue" onClick={onOpen}>
              Add Beneficiary
            </Button>
          </HStack>

          {!primaryValid && (
            <Alert status="warning" borderRadius="md" mb={3}>
              <AlertIcon />
              <Text fontSize="sm">
                Primary beneficiary percentages sum to {primaryTotal.toFixed(1)}% — should be 100%.
              </Text>
            </Alert>
          )}

          <Card variant="outline" w="full">
            <CardBody overflowX="auto">
              {bensLoading ? (
                <Spinner size="sm" />
              ) : (
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Name</Th>
                      <Th>Relationship</Th>
                      <Th>Type</Th>
                      <Th isNumeric>%</Th>
                      <Th>Account</Th>
                      <Th />
                    </Tr>
                  </Thead>
                  <Tbody>
                    {beneficiaries.length > 0 ? (
                      beneficiaries.map((b) => {
                        const acct = accounts.find((a) => a.id === b.account_id);
                        return (
                          <Tr key={b.id}>
                            <Td fontWeight="medium">{b.name}</Td>
                            <Td>{b.relationship}</Td>
                            <Td>
                              <Badge
                                colorScheme={b.designation_type === "primary" ? "green" : "purple"}
                                size="sm"
                              >
                                {b.designation_type}
                              </Badge>
                            </Td>
                            <Td isNumeric>{b.percentage}%</Td>
                            <Td color="text.secondary" fontSize="xs">
                              {acct ? acct.name : "All accounts"}
                            </Td>
                            <Td>
                              <Button
                                size="xs"
                                variant="ghost"
                                colorScheme="red"
                                isLoading={deleteBen.isPending}
                                onClick={() => deleteBen.mutate(b.id)}
                              >
                                <Icon as={FiTrash2} />
                              </Button>
                            </Td>
                          </Tr>
                        );
                      })
                    ) : (
                      <Tr>
                        <Td colSpan={6}>
                          <Text color="text.secondary" fontSize="sm" textAlign="center" py={4}>
                            No beneficiaries added yet. Click "Add Beneficiary" to get started.
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

        {/* ── Estate Tax Exposure ───────────────────────────────────────── */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Estate Tax Exposure
            <InfoTip label="The federal estate tax applies to estates exceeding the exemption at death. Married couples may use portability to combine exemptions." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">Net Worth vs Federal Exemption</Heading>
            </CardHeader>
            <CardBody>
              <HStack spacing={4} mb={4} flexWrap="wrap">
                <FormControl maxW="220px">
                  <FormLabel fontSize="sm">
                    Net Worth Override
                    <InfoTip label="Leave blank to use your linked account net worth." />
                  </FormLabel>
                  <InputGroup size="sm">
                    <InputLeftAddon>$</InputLeftAddon>
                    <Input
                      type="number"
                      placeholder={
                        dashSummary?.net_worth
                          ? String(Math.round(dashSummary.net_worth))
                          : "Enter net worth"
                      }
                      value={netWorthOverride}
                      onChange={(e) => {
                        setNetWorthOverride(e.target.value);
                        setTaxCalcEnabled(true);
                      }}
                    />
                  </InputGroup>
                </FormControl>
                <FormControl maxW="160px">
                  <FormLabel fontSize="sm">Filing Status</FormLabel>
                  <Select
                    size="sm"
                    value={filingStatus}
                    onChange={(e) => {
                      setFilingStatus(e.target.value);
                      setTaxCalcEnabled(true);
                    }}
                  >
                    <option value="single">Single</option>
                    <option value="married">Married</option>
                  </Select>
                </FormControl>
              </HStack>

              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Federal Exemption
                    <InfoTip label="2026 per-person exemption ~$13.99M. Married couples can combine via portability. May drop to ~$7M if TCJA sunsets." />
                  </Text>
                  <Text fontWeight="semibold">
                    {taxResult ? fmt(taxResult.federal_exemption) : "—"}
                  </Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Federal Estate Tax Rate (above exemption)</Text>
                  <Badge colorScheme="red">40%</Badge>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Your Net Worth</Text>
                  <Text fontWeight="semibold">
                    {taxResult ? fmt(taxResult.net_worth) : fmt(effectiveNetWorth)}
                  </Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Taxable Estate (above exemption)</Text>
                  <Text
                    fontWeight="semibold"
                    color={taxResult?.above_exemption ? "red.500" : "green.600"}
                  >
                    {taxResult
                      ? taxResult.above_exemption
                        ? fmt(taxResult.taxable_estate)
                        : "Below exemption threshold"
                      : "—"}
                  </Text>
                </HStack>
                {taxResult?.above_exemption && (
                  <HStack justify="space-between" w="full">
                    <Text color="text.secondary">Estimated Federal Estate Tax</Text>
                    <Text fontWeight="semibold" color="red.500">
                      {fmt(taxResult.estimated_federal_tax)}
                    </Text>
                  </HStack>
                )}
                {taxResult?.tcja_sunset_risk && (
                  <Alert status="warning" borderRadius="md" fontSize="xs">
                    <AlertIcon />
                    {taxResult.sunset_note}
                  </Alert>
                )}
                <Text fontSize="xs" color="text.secondary">
                  Consult an estate attorney for strategies including irrevocable trusts,
                  annual gifting ($18,000/year exclusion), and charitable remainder trusts.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* ── Planning Documents ────────────────────────────────────────── */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Planning Documents
            <InfoTip label="Check off documents you have in place. Your status is saved so you can track completion over time." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <HStack>
                <Icon as={FiCheckCircle} color="green.500" />
                <Heading size="sm">Document Checklist</Heading>
                <Badge colorScheme="green" ml={2}>
                  {DOC_TYPES.filter((d) => {
                    const rec = docMap.get(d.key);
                    return rec && rec.last_reviewed_date;
                  }).length}
                  /{DOC_TYPES.length} complete
                </Badge>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack align="start" spacing={3}>
                {DOC_TYPES.map((doc) => {
                  const record = docMap.get(doc.key);
                  const isChecked = !!(record && record.last_reviewed_date);
                  return (
                    <Box key={doc.key} w="full">
                      <HStack align="start">
                        <Checkbox
                          colorScheme="green"
                          size="sm"
                          isChecked={isChecked}
                          onChange={(e) =>
                            upsertDoc.mutate({
                              document_type: doc.key,
                              checked: e.target.checked,
                            })
                          }
                        >
                          <Text fontWeight="medium" fontSize="sm">
                            {doc.label}
                          </Text>
                        </Checkbox>
                        {isChecked && record?.last_reviewed_date && (
                          <Badge colorScheme="green" fontSize="xs" ml={1}>
                            reviewed {record.last_reviewed_date}
                          </Badge>
                        )}
                      </HStack>
                      <Text fontSize="xs" color="text.secondary" ml={6}>
                        {doc.description}
                      </Text>
                    </Box>
                  );
                })}
              </VStack>
            </CardBody>
          </Card>
        </Box>
      </VStack>

      {/* ── Add Beneficiary Modal ──────────────────────────────────────── */}
      <Modal isOpen={isOpen} onClose={onClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Add Beneficiary</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={3}>
              <FormControl isRequired>
                <FormLabel fontSize="sm">Full Name</FormLabel>
                <Input
                  size="sm"
                  placeholder="Jane Smith"
                  value={benForm.name}
                  onChange={(e) => setBenForm({ ...benForm, name: e.target.value })}
                />
              </FormControl>
              <HStack w="full" spacing={3}>
                <FormControl>
                  <FormLabel fontSize="sm">Relationship</FormLabel>
                  <Select
                    size="sm"
                    value={benForm.relationship}
                    onChange={(e) => setBenForm({ ...benForm, relationship: e.target.value })}
                  >
                    <option value="spouse">Spouse</option>
                    <option value="child">Child</option>
                    <option value="parent">Parent</option>
                    <option value="sibling">Sibling</option>
                    <option value="trust">Trust</option>
                    <option value="charity">Charity</option>
                    <option value="other">Other</option>
                  </Select>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">Type</FormLabel>
                  <Select
                    size="sm"
                    value={benForm.designation_type}
                    onChange={(e) =>
                      setBenForm({ ...benForm, designation_type: e.target.value })
                    }
                  >
                    <option value="primary">Primary</option>
                    <option value="contingent">Contingent</option>
                  </Select>
                </FormControl>
              </HStack>
              <HStack w="full" spacing={3}>
                <FormControl>
                  <FormLabel fontSize="sm">Percentage</FormLabel>
                  <InputGroup size="sm">
                    <Input
                      type="number"
                      placeholder="100"
                      value={benForm.percentage}
                      onChange={(e) =>
                        setBenForm({ ...benForm, percentage: e.target.value })
                      }
                    />
                  </InputGroup>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm">Date of Birth (optional)</FormLabel>
                  <Input
                    size="sm"
                    type="date"
                    value={benForm.dob}
                    onChange={(e) => setBenForm({ ...benForm, dob: e.target.value })}
                  />
                </FormControl>
              </HStack>
              <FormControl>
                <FormLabel fontSize="sm">
                  Account (optional)
                  <InfoTip label="Leave blank to apply to all accounts / estate-level designation." />
                </FormLabel>
                <Select
                  size="sm"
                  value={benForm.account_id}
                  onChange={(e) => setBenForm({ ...benForm, account_id: e.target.value })}
                >
                  <option value="">All accounts (estate-level)</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.account_type})
                    </option>
                  ))}
                </Select>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">Notes (optional)</FormLabel>
                <Input
                  size="sm"
                  placeholder="e.g. per stirpes"
                  value={benForm.notes}
                  onChange={(e) => setBenForm({ ...benForm, notes: e.target.value })}
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose} size="sm">
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              size="sm"
              isLoading={addBen.isPending}
              isDisabled={!benForm.name || !benForm.percentage}
              onClick={() => addBen.mutate()}
            >
              Add
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
};

export default EstatePage;
