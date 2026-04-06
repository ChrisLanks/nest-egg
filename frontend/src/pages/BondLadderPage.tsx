/**
 * Bond Ladder page — form to build a ladder + results display.
 */

import { useState } from "react";
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Heading,
  Input,
  Select,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Table,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
  VStack,
  Alert,
  AlertIcon,
  Text,
  Badge,
  Icon,
  Tooltip,
} from "@chakra-ui/react";
import { FiInfo } from "react-icons/fi";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "../services/api";
import { useCurrency } from "../contexts/CurrencyContext";

function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip label={label} placement="top" hasArrow maxW="280px">
      <span style={{ display: "inline-flex", alignItems: "center", marginLeft: "4px", cursor: "default" }}>
        <Icon as={FiInfo} boxSize={3} color="gray.400" />
      </span>
    </Tooltip>
  );
}

interface RatesResponse {
  treasury_rates: Record<string, number>;
  estimated_cd_rates: Record<string, number>;
  source: string;
}

interface LadderRung {
  rung: number;
  years_to_maturity: number;
  maturity_year: number;
  investment_amount: number;
  annual_rate: number;
  annual_rate_pct: number;
  maturity_value: number;
  interest_earned: number;
  instrument_type: string;
}

interface LadderResult {
  rungs: LadderRung[];
  num_rungs: number;
  ladder_type: string;
  total_invested: number;
  per_rung_investment: number;
  total_interest: number;
  total_maturity_values: number;
  annual_income_actual: number;
  annual_income_needed: number;
  income_gap: number;
  meets_income_target: boolean;
  reinvestment_note: string;
}

export default function BondLadderPage() {
  const { currency } = useCurrency();

  const fmt = (n: number) =>
    n.toLocaleString("en-US", { style: "currency", currency, maximumFractionDigits: 0 });
  const [totalInvestment, setTotalInvestment] = useState("500000");
  const [numRungs, setNumRungs] = useState("10");
  const [incomeNeeded, setIncomeNeeded] = useState("50000");
  const [startYear, setStartYear] = useState(String(new Date().getFullYear() + 1));
  const [ladderType, setLadderType] = useState("treasury");

  const { data: ratesData } = useQuery<RatesResponse>({
    queryKey: ["bond-ladder-rates"],
    queryFn: async () => {
      const res = await api.get("/bond-ladder/rates");
      return res.data;
    },
    staleTime: 15 * 60 * 1000,
  });

  const mutation = useMutation<LadderResult, Error>({
    mutationFn: async () => {
      const res = await api.post("/bond-ladder/plan", {
        total_investment: parseFloat(totalInvestment),
        num_rungs: parseInt(numRungs),
        annual_income_needed: parseFloat(incomeNeeded),
        start_year: parseInt(startYear),
        ladder_type: ladderType,
      });
      return res.data;
    },
  });

  return (
    <Box p={6}>
      <Heading size="lg" mb={4}>
        Bond Ladder Builder
      </Heading>

      <Alert status="info" mb={6} fontSize="sm">
        <AlertIcon />
        Rates sourced from {ratesData ? ratesData.source : "U.S. Treasury / FRED"}.
        {ratesData && (
          <Text as="span" ml={2}>
            10-yr Treasury: {((ratesData.treasury_rates["10_year"] ?? 0) * 100).toFixed(2)}%
            {ratesData.treasury_rates["1_year"] !== undefined && (
              <>, 1-yr: {(ratesData.treasury_rates["1_year"] * 100).toFixed(2)}%</>
            )}
          </Text>
        )}
      </Alert>

      <VStack spacing={4} align="stretch" maxW="500px" mb={6}>
        <SimpleGrid columns={2} spacing={4}>
          <FormControl>
            <FormLabel>
              Total Investment
              <InfoTip label="The total amount you want to invest across all rungs of the ladder." />
            </FormLabel>
            <Input
              type="number"
              value={totalInvestment}
              onChange={(e) => setTotalInvestment(e.target.value)}
            />
          </FormControl>
          <FormControl>
            <FormLabel>
              Number of Rungs
              <InfoTip label="Each rung is a bond or CD maturing in a different year. More rungs means more predictable, staggered income." />
            </FormLabel>
            <Input
              type="number"
              min={1}
              max={30}
              value={numRungs}
              onChange={(e) => setNumRungs(e.target.value)}
            />
          </FormControl>
        </SimpleGrid>
        <SimpleGrid columns={2} spacing={4}>
          <FormControl>
            <FormLabel>
              Annual Income Needed
              <InfoTip label="Your target annual income from this ladder. We'll flag if the ladder falls short of this target." />
            </FormLabel>
            <Input
              type="number"
              value={incomeNeeded}
              onChange={(e) => setIncomeNeeded(e.target.value)}
            />
          </FormControl>
          <FormControl>
            <FormLabel>
              Start Year
              <InfoTip label="The year the first rung matures." />
            </FormLabel>
            <Input
              type="number"
              value={startYear}
              onChange={(e) => setStartYear(e.target.value)}
            />
          </FormControl>
        </SimpleGrid>
        <FormControl>
          <FormLabel>
            Ladder Type
            <InfoTip label="Choose the type of fixed-income instrument for each rung. Treasury bonds are backed by the U.S. government. CDs are FDIC-insured bank deposits. TIPS adjust principal with inflation." />
          </FormLabel>
          <Select value={ladderType} onChange={(e) => setLadderType(e.target.value)}>
            <option value="treasury">Treasury</option>
            <option value="cd">CD</option>
            <option value="tips">TIPS</option>
          </Select>
        </FormControl>
        {ladderType === "tips" && (
          <Alert status="info" fontSize="sm" borderRadius="md">
            <AlertIcon />
            <Text>
              <strong>TIPS (Treasury Inflation-Protected Securities):</strong> U.S. government bonds whose principal adjusts with inflation (CPI). Yields may be lower than nominal Treasuries, but your purchasing power is protected. Interest is federally taxable but exempt from state and local tax.
            </Text>
          </Alert>
        )}
        <Button
          colorScheme="blue"
          onClick={() => mutation.mutate()}
          isLoading={mutation.isPending}
        >
          Build Ladder
        </Button>
      </VStack>

      {mutation.isError && (
        <Alert status="error" mb={4}>
          <AlertIcon />
          Failed to build bond ladder. Check your inputs and try again.
        </Alert>
      )}

      {mutation.data && (
        <Box>
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} mb={4}>
            <Stat>
              <StatLabel>Total Invested</StatLabel>
              <StatNumber>{fmt(mutation.data.total_invested)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>
                Total Interest
                <InfoTip label="The total interest (or inflation-adjusted gain for TIPS) earned across all rungs by their respective maturity dates." />
              </StatLabel>
              <StatNumber>{fmt(mutation.data.total_interest)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>
                Annual Income
                <InfoTip label="Estimated annual income generated by this ladder — the average interest paid out per year across all rungs." />
              </StatLabel>
              <StatNumber>{fmt(mutation.data.annual_income_actual)}</StatNumber>
              <StatHelpText>
                {mutation.data.meets_income_target ? (
                  <Badge colorScheme="green">Meets target</Badge>
                ) : (
                  <Badge colorScheme="orange">
                    Gap: {fmt(Math.abs(mutation.data.income_gap))}
                  </Badge>
                )}
              </StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>Type</StatLabel>
              <StatNumber>{mutation.data.ladder_type.toUpperCase()}</StatNumber>
              <StatHelpText>{mutation.data.num_rungs} rungs</StatHelpText>
            </Stat>
          </SimpleGrid>

          <Table size="sm" variant="simple" mb={4}>
            <Thead>
              <Tr>
                <Th>Rung</Th>
                <Th>Maturity Year</Th>
                <Th isNumeric>Invested</Th>
                <Th isNumeric>Rate</Th>
                <Th isNumeric>
                  Maturity Value
                  <InfoTip label="The total amount returned when this rung matures — your original investment plus interest earned." />
                </Th>
                <Th isNumeric>Interest</Th>
              </Tr>
            </Thead>
            <Tbody>
              {mutation.data.rungs.map((rung) => (
                <Tr key={rung.rung}>
                  <Td>{rung.rung}</Td>
                  <Td>{rung.maturity_year}</Td>
                  <Td isNumeric>{fmt(rung.investment_amount)}</Td>
                  <Td isNumeric>{rung.annual_rate_pct.toFixed(2)}%</Td>
                  <Td isNumeric>{fmt(rung.maturity_value)}</Td>
                  <Td isNumeric>{fmt(rung.interest_earned)}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>

          <Text fontSize="sm" color="gray.500">{mutation.data.reinvestment_note}</Text>
        </Box>
      )}

      {!mutation.data && !mutation.isPending && !mutation.isError && (
        <Text color="gray.500">
          Configure your ladder parameters above and click "Build Ladder" to see results.
        </Text>
      )}
    </Box>
  );
}
