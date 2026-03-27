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
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
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
} from "@chakra-ui/react";
import { useMutation } from "@tanstack/react-query";
import api from "../services/api";

interface LadderRung {
  year: number;
  amount: number;
  yield_pct: number;
  maturity_date: string;
}

interface LadderResult {
  rungs: LadderRung[];
  total_cost: number;
  average_yield: number;
  ladder_type: string;
}

const fmt = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function BondLadderPage() {
  const [incomeNeeded, setIncomeNeeded] = useState("50000");
  const [startYear, setStartYear] = useState("2027");
  const [endYear, setEndYear] = useState("2036");
  const [ladderType, setLadderType] = useState("treasury");

  const mutation = useMutation<LadderResult, Error>({
    mutationFn: async () => {
      const res = await api.post("/bond-ladder/build", {
        annual_income_needed: parseFloat(incomeNeeded),
        start_year: parseInt(startYear),
        end_year: parseInt(endYear),
        ladder_type: ladderType,
      });
      return res.data;
    },
  });

  return (
    <Box p={6}>
      <Heading size="lg" mb={6}>
        Bond Ladder Builder
      </Heading>

      <VStack spacing={4} align="stretch" maxW="500px" mb={6}>
        <FormControl>
          <FormLabel>Annual Income Needed</FormLabel>
          <Input
            type="number"
            value={incomeNeeded}
            onChange={(e) => setIncomeNeeded(e.target.value)}
          />
        </FormControl>
        <SimpleGrid columns={2} spacing={4}>
          <FormControl>
            <FormLabel>Start Year</FormLabel>
            <Input
              type="number"
              value={startYear}
              onChange={(e) => setStartYear(e.target.value)}
            />
          </FormControl>
          <FormControl>
            <FormLabel>End Year</FormLabel>
            <Input
              type="number"
              value={endYear}
              onChange={(e) => setEndYear(e.target.value)}
            />
          </FormControl>
        </SimpleGrid>
        <FormControl>
          <FormLabel>Ladder Type</FormLabel>
          <Select value={ladderType} onChange={(e) => setLadderType(e.target.value)}>
            <option value="treasury">Treasury</option>
            <option value="cd">CD</option>
            <option value="tips">TIPS</option>
          </Select>
        </FormControl>
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
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={6}>
            <Stat>
              <StatLabel>Total Cost</StatLabel>
              <StatNumber>{fmt(mutation.data.total_cost)}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Average Yield</StatLabel>
              <StatNumber>{(mutation.data.average_yield * 100).toFixed(2)}%</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Ladder Type</StatLabel>
              <StatNumber>{mutation.data.ladder_type.toUpperCase()}</StatNumber>
            </Stat>
          </SimpleGrid>

          <Table size="sm" variant="simple">
            <Thead>
              <Tr>
                <Th>Year</Th>
                <Th isNumeric>Amount</Th>
                <Th isNumeric>Yield</Th>
                <Th>Maturity</Th>
              </Tr>
            </Thead>
            <Tbody>
              {mutation.data.rungs.map((rung) => (
                <Tr key={rung.year}>
                  <Td>{rung.year}</Td>
                  <Td isNumeric>{fmt(rung.amount)}</Td>
                  <Td isNumeric>{(rung.yield_pct * 100).toFixed(2)}%</Td>
                  <Td>{rung.maturity_date}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      {!mutation.data && !mutation.isPending && (
        <Text color="gray.500">
          Configure your ladder parameters above and click "Build Ladder" to see results.
        </Text>
      )}
    </Box>
  );
}
