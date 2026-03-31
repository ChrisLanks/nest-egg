/**
 * Withholding Check Widget — interactive inline form to estimate federal
 * withholding adequacy for the current tax year.
 */

import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Link,
  NumberInput,
  NumberInputField,
  Select,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useMutation } from "@tanstack/react-query";
import { memo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import api from "../../../services/api";

interface WithholdingCheckRequest {
  filing_status: "single" | "married";
  annual_salary: number;
  ytd_withheld: number;
  months_remaining: number;
  other_income?: number;
}

interface WithholdingCheckResponse {
  projected_tax: number;
  safe_harbour_amount: number;
  ytd_withheld: number;
  projected_year_end_withholding: number;
  underpayment_risk: boolean;
  recommended_additional_withholding_per_paycheck: number;
  w4_extra_amount: number;
  notes: string[];
  tax_year: number;
}

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

// months remaining including current month (getMonth is 0-indexed)
const defaultMonthsRemaining = () => 12 - new Date().getMonth();

const WithholdingCheckWidgetBase: React.FC = () => {
  const [filingStatus, setFilingStatus] = useState<"single" | "married">(
    "single",
  );
  const [annualSalary, setAnnualSalary] = useState("");
  const [ytdWithheld, setYtdWithheld] = useState("0");
  const [monthsRemaining, setMonthsRemaining] = useState(
    String(defaultMonthsRemaining()),
  );
  const [otherIncome, setOtherIncome] = useState("0");
  const [result, setResult] = useState<WithholdingCheckResponse | null>(null);

  const mutation = useMutation<
    WithholdingCheckResponse,
    Error,
    WithholdingCheckRequest
  >({
    mutationFn: async (body) => {
      const res = await api.post("/withholding-check", body);
      return res.data;
    },
    onSuccess: (data) => setResult(data),
  });

  const handleSubmit = () => {
    const salary = parseFloat(annualSalary);
    if (!annualSalary || isNaN(salary) || salary <= 0) return;
    mutation.mutate({
      filing_status: filingStatus,
      annual_salary: salary,
      ytd_withheld: parseFloat(ytdWithheld) || 0,
      months_remaining: parseInt(monthsRemaining) || 0,
      other_income: parseFloat(otherIncome) || 0,
    });
  };

  const handleRecalculate = () => {
    setResult(null);
    mutation.reset();
  };

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Withholding Check</Heading>
          <Link
            as={RouterLink}
            to="/tax-center"
            fontSize="sm"
            color="brand.500"
          >
            Learn more →
          </Link>
        </HStack>

        {result ? (
          <VStack align="stretch" spacing={3}>
            <Box>
              <Badge
                colorScheme={result.underpayment_risk ? "orange" : "green"}
                fontSize="sm"
                px={3}
                py={1}
                borderRadius="full"
              >
                {result.underpayment_risk
                  ? "\u26A0 Underpayment Risk"
                  : "\u2713 On Track"}
              </Badge>
            </Box>

            <SimpleGrid columns={2} spacing={3}>
              <Stat size="sm">
                <StatLabel>Projected Tax</StatLabel>
                <StatNumber fontSize="lg">
                  {fmt(result.projected_tax)}
                </StatNumber>
              </Stat>
              <Stat size="sm">
                <StatLabel>Projected Withholding</StatLabel>
                <StatNumber fontSize="lg">
                  {fmt(result.projected_year_end_withholding)}
                </StatNumber>
              </Stat>
            </SimpleGrid>

            {result.underpayment_risk && result.w4_extra_amount > 0 && (
              <Box
                p={2}
                borderRadius="md"
                bg="orange.50"
                _dark={{ bg: "orange.900" }}
              >
                <Text
                  fontSize="sm"
                  color="orange.700"
                  _dark={{ color: "orange.200" }}
                >
                  Add {fmt(result.w4_extra_amount)} extra per paycheck on your
                  W-4 to avoid underpayment.
                </Text>
              </Box>
            )}

            {result.notes.length > 0 && (
              <Text fontSize="xs" color="text.secondary">
                {result.notes[0]}
              </Text>
            )}

            <Button
              size="sm"
              variant="outline"
              onClick={handleRecalculate}
              alignSelf="flex-start"
            >
              Recalculate
            </Button>
          </VStack>
        ) : (
          <VStack align="stretch" spacing={3}>
            <FormControl>
              <FormLabel fontSize="xs">Filing status</FormLabel>
              <Select
                size="sm"
                value={filingStatus}
                onChange={(e) =>
                  setFilingStatus(e.target.value as "single" | "married")
                }
              >
                <option value="single">Single</option>
                <option value="married">Married</option>
              </Select>
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="xs">Annual salary</FormLabel>
              <NumberInput size="sm" min={0} value={annualSalary}>
                <NumberInputField
                  placeholder="Annual salary"
                  onChange={(e) => setAnnualSalary(e.target.value)}
                />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="xs">YTD federal withheld</FormLabel>
              <NumberInput
                size="sm"
                min={0}
                value={ytdWithheld}
                onChange={(val) => setYtdWithheld(val)}
              >
                <NumberInputField placeholder="YTD federal withheld" />
              </NumberInput>
            </FormControl>

            <HStack spacing={3}>
              <FormControl>
                <FormLabel fontSize="xs">Months remaining</FormLabel>
                <NumberInput
                  size="sm"
                  min={0}
                  max={12}
                  value={monthsRemaining}
                  onChange={(val) => setMonthsRemaining(val)}
                >
                  <NumberInputField placeholder="Months remaining" />
                </NumberInput>
              </FormControl>

              <FormControl>
                <FormLabel fontSize="xs">Other income</FormLabel>
                <NumberInput
                  size="sm"
                  min={0}
                  value={otherIncome}
                  onChange={(val) => setOtherIncome(val)}
                >
                  <NumberInputField placeholder="Other income (optional)" />
                </NumberInput>
              </FormControl>
            </HStack>

            {mutation.isError && (
              <Text fontSize="xs" color="red.500">
                Failed to calculate. Please try again.
              </Text>
            )}

            <Button
              size="sm"
              colorScheme="brand"
              onClick={handleSubmit}
              isLoading={mutation.isPending}
              isDisabled={!annualSalary || parseFloat(annualSalary) <= 0}
            >
              Check Withholding
            </Button>
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};

export const WithholdingCheckWidget = memo(WithholdingCheckWidgetBase);
