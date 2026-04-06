/**
 * Backdoor Roth & Mega Backdoor Wizard tab.
 */

import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  FormControl,
  FormLabel,
  HStack,
  List,
  ListIcon,
  ListItem,
  NumberInput,
  NumberInputField,
  Select,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { FiCheckCircle, FiAlertTriangle, FiArrowRight } from "react-icons/fi";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import { useCurrency } from "../contexts/CurrencyContext";

interface IraAccountDetail {
  account_id: string;
  name: string;
  balance: number;
  form_8606_basis: number;
  pre_tax_portion: number;
  pro_rata_ratio: number;
}

interface BackdoorRothDetail {
  eligible: boolean;
  pro_rata_warning: boolean;
  total_ira_balance: number;
  total_form_8606_basis: number;
  accounts: IraAccountDetail[];
  steps: string[];
}

interface K401AccountDetail {
  account_id: string;
  name: string;
  after_tax_balance: number;
  mega_backdoor_eligible: boolean;
}

interface MegaBackdoorDetail {
  eligible: boolean;
  available_amount: number;
  accounts: K401AccountDetail[];
  steps: string[];
}

interface BackdoorRothResponse {
  backdoor_roth: BackdoorRothDetail;
  mega_backdoor: MegaBackdoorDetail;
  ira_contribution_headroom: number;
  direct_roth_eligible: boolean | null;
  user_magi_estimate: number | null;
  tax_year: number;
  phaseout_lower: number;
  phaseout_upper: number;
}

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);

export const BackdoorRothTab = () => {
  const { selectedUserId, effectiveUserId } = useUserView();
  const [filingStatus, setFilingStatus] = useState("single");
  const [magi, setMagi] = useState<number | undefined>(undefined);

  const params = new URLSearchParams({ filing_status: filingStatus });
  if (magi !== undefined) params.set("estimated_magi", String(magi));
  if (effectiveUserId) params.set("user_id", effectiveUserId);

  const { data, isLoading, error } = useQuery<BackdoorRothResponse>({
    queryKey: ["backdoor-roth", filingStatus, magi, effectiveUserId],
    queryFn: () => api.get(`/tax/backdoor-roth-analysis?${params}`).then((r) => r.data),
  });

  return (
    <VStack spacing={6} align="stretch">
      <Text fontSize="sm" color="text.secondary">
        Backdoor Roth and Mega Backdoor Roth strategies allow high earners to contribute to a Roth
        IRA regardless of income limits.
      </Text>

      {/* Optional MAGI input for direct Roth eligibility check */}
      <Card>
        <CardBody>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <FormControl>
              <FormLabel fontSize="sm">Filing Status</FormLabel>
              <Select
                size="sm"
                value={filingStatus}
                onChange={(e) => setFilingStatus(e.target.value)}
              >
                <option value="single">Single</option>
                <option value="married">Married Filing Jointly</option>
              </Select>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Estimated MAGI (optional)</FormLabel>
              <NumberInput
                value={magi ?? ""}
                min={0}
                step={5000}
                onChange={(_, v) => setMagi(isNaN(v) ? undefined : v)}
                size="sm"
              >
                <NumberInputField placeholder="Enter to check direct Roth eligibility" />
              </NumberInput>
            </FormControl>
          </SimpleGrid>
        </CardBody>
      </Card>

      {isLoading && <Text color="text.secondary">Analyzing accounts…</Text>}
      {error && (
        <Alert status="error">
          <AlertIcon />
          Failed to load analysis.
        </Alert>
      )}

      {data && (
        <>
          {/* Summary cards */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <Tooltip label="How much more you can contribute to an IRA this year before hitting the IRS limit ($7,000 for 2026; $8,000 if age 50+). Unused room cannot be carried forward to next year." hasArrow placement="top">
                <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">IRA Contribution Headroom</StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg">{fmt(data.ira_contribution_headroom)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Roth Phase-Out Range</StatLabel>
              <StatNumber fontSize="md">{fmt(data.phaseout_lower)}–{fmt(data.phaseout_upper)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel fontSize="xs">Total IRA Pre-Tax Balance</StatLabel>
              <StatNumber fontSize="lg">{fmt(data.backdoor_roth.total_ira_balance)}</StatNumber>
            </Stat>
            <Stat>
              <Tooltip label="After-tax 401(k) contributions that can be converted to Roth beyond the standard $23,500 limit — requires your plan to allow after-tax contributions and in-service rollovers." hasArrow placement="top">
                <StatLabel fontSize="xs" cursor="help" textDecoration="underline dotted" display="inline-block">Mega Backdoor Available</StatLabel>
              </Tooltip>
              <StatNumber fontSize="lg">{fmt(data.mega_backdoor.available_amount)}</StatNumber>
            </Stat>
          </SimpleGrid>

          {/* Direct Roth eligibility */}
          {data.direct_roth_eligible !== null ? (
            <Alert status={data.direct_roth_eligible ? "success" : "info"}>
              <AlertIcon />
              <AlertDescription fontSize="sm">
                {data.direct_roth_eligible
                  ? `Your income is below the ${fmt(data.phaseout_lower)} phase-out threshold — you can contribute directly to a Roth IRA.`
                  : `Your income exceeds the ${fmt(data.phaseout_upper)} phase-out limit. Use the backdoor strategy below.`}
              </AlertDescription>
            </Alert>
          ) : (
            <Alert status="info" variant="subtle">
              <AlertIcon />
              <AlertDescription fontSize="sm">
                Direct Roth IRA contributions phase out between {fmt(data.phaseout_lower)} and {fmt(data.phaseout_upper)} for {filingStatus === "married" ? "married filing jointly" : "single"} filers. Enter your MAGI above to check eligibility.
              </AlertDescription>
            </Alert>
          )}

          <Accordion allowMultiple defaultIndex={[0, 1]}>
            {/* Backdoor Roth */}
            <AccordionItem border="1px solid" borderColor="border.default" borderRadius="md" mb={3}>
              <AccordionButton>
                <HStack flex={1}>
                  <Text fontWeight="bold" fontSize="sm">Backdoor Roth IRA</Text>
                  {data.backdoor_roth.pro_rata_warning ? (
                    <Badge colorScheme="orange">Pro-Rata Warning</Badge>
                  ) : (
                    <Badge colorScheme="green">Clean</Badge>
                  )}
                </HStack>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                <VStack align="stretch" spacing={3}>
                  {data.backdoor_roth.pro_rata_warning && (
                    <Alert status="warning" variant="subtle">
                      <AlertIcon />
                      <AlertDescription fontSize="xs">
                        You have pre-tax IRA funds (${fmt(data.backdoor_roth.total_ira_balance - data.backdoor_roth.total_form_8606_basis)} pre-tax portion).
                        The pro-rata rule will tax a portion of your backdoor conversion. Consider rolling IRA funds into your 401(k) first.
                      </AlertDescription>
                    </Alert>
                  )}

                  {data.backdoor_roth.accounts.length > 0 && (
                    <Box overflowX="auto">
                      <Text fontSize="xs" fontWeight="bold" mb={1}>IRA Accounts</Text>
                      {data.backdoor_roth.accounts.map((a) => (
                        <HStack key={a.account_id} justify="space-between" py={1} fontSize="sm">
                          <Text>{a.name}</Text>
                          <HStack spacing={4}>
                            <Text color="text.secondary">Balance: {fmt(a.balance)}</Text>
                            <Text color="text.secondary">Basis: {fmt(a.form_8606_basis)}</Text>
                            <Badge colorScheme={a.pro_rata_ratio > 0.1 ? "orange" : "green"}>
                              {Math.round(a.pro_rata_ratio * 100)}% pre-tax
                            </Badge>
                          </HStack>
                        </HStack>
                      ))}
                    </Box>
                  )}

                  <Text fontSize="xs" fontWeight="bold">Steps to Execute</Text>
                  <List spacing={2}>
                    {data.backdoor_roth.steps.map((step, i) => (
                      <ListItem key={i} fontSize="sm" display="flex" alignItems="flex-start">
                        <ListIcon as={step.startsWith("⚠️") ? FiAlertTriangle : FiArrowRight} color={step.startsWith("⚠️") ? "orange.400" : "brand.500"} mt="2px" />
                        {step.replace("⚠️ ", "")}
                      </ListItem>
                    ))}
                  </List>
                </VStack>
              </AccordionPanel>
            </AccordionItem>

            {/* Mega Backdoor */}
            <AccordionItem border="1px solid" borderColor="border.default" borderRadius="md">
              <AccordionButton>
                <HStack flex={1}>
                  <Text fontWeight="bold" fontSize="sm">Mega Backdoor Roth (401k)</Text>
                  <Badge colorScheme={data.mega_backdoor.eligible ? "green" : "gray"}>
                    {data.mega_backdoor.eligible ? "Eligible" : "Not Available"}
                  </Badge>
                </HStack>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                <VStack align="stretch" spacing={3}>
                  {data.mega_backdoor.eligible && data.mega_backdoor.available_amount > 0 && (
                    <Alert status="success" variant="subtle">
                      <AlertIcon />
                      <AlertDescription fontSize="sm">
                        You have {fmt(data.mega_backdoor.available_amount)} in after-tax 401(k) funds available for conversion.
                      </AlertDescription>
                    </Alert>
                  )}

                  <Text fontSize="xs" fontWeight="bold">Steps to Execute</Text>
                  <List spacing={2}>
                    {data.mega_backdoor.steps.map((step, i) => (
                      <ListItem key={i} fontSize="sm" display="flex" alignItems="flex-start">
                        <ListIcon as={FiArrowRight} color="brand.500" mt="2px" />
                        {step}
                      </ListItem>
                    ))}
                  </List>
                </VStack>
              </AccordionPanel>
            </AccordionItem>
          </Accordion>
        </>
      )}
    </VStack>
  );
};
