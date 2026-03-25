/**
 * Variable Income Planner page.
 *
 * Helps freelancers and self-employed users smooth out income volatility,
 * set a minimum monthly floor, and stay on top of quarterly estimated taxes.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  CardHeader,
  Container,
  Divider,
  Heading,
  HStack,
  Icon,
  SimpleGrid,
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

function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip label={label} placement="top" hasArrow maxW="260px">
      <Box as="span" display="inline-flex" ml={1} verticalAlign="middle" cursor="help">
        <Icon as={FiInfo} boxSize={3} color="text.muted" />
      </Box>
    </Tooltip>
  );
}

const quarterlySchedule = [
  { quarter: "Q1 2026", period: "Jan 1 – Mar 31", dueDate: "Apr 15, 2026", status: "upcoming" },
  { quarter: "Q2 2026", period: "Apr 1 – May 31", dueDate: "Jun 16, 2026", status: "upcoming" },
  { quarter: "Q3 2026", period: "Jun 1 – Aug 31", dueDate: "Sep 15, 2026", status: "upcoming" },
  { quarter: "Q4 2026", period: "Sep 1 – Dec 31", dueDate: "Jan 15, 2027", status: "upcoming" },
];

export const VariableIncomePage = () => {
  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        <Box>
          <Heading size="lg">Variable Income Planner</Heading>
          <Text color="text.secondary" mt={1}>
            Smooth out income volatility with rolling averages, set a minimum
            monthly floor, and stay on top of quarterly estimated tax payments.
          </Text>
        </Box>
        <Alert status="info" borderRadius="lg" w="full">
          <AlertIcon />
          <Text fontSize="sm">
            Connect income transactions to enable automatic rolling average
            calculations and safe-harbor payment estimates.
          </Text>
        </Alert>
        {/* Income Smoothing */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Income Smoothing
            <InfoTip label="The 12-month rolling average normalizes volatile income for consistent budgeting. The IRS safe harbor for avoiding underpayment penalties is paying 100% of prior-year tax (110% if AGI exceeded $150k) or 90% of current-year tax." />
          </Heading>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} w="full">
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel>This Month<InfoTip label="Gross income recognized in the current calendar month." /></StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>current month gross</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel>12-Month Rolling Avg<InfoTip label="Average monthly gross income over the trailing 12 months. Use this as your budgeting baseline." /></StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>per month avg</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
            <Card variant="outline">
              <CardBody>
                <Stat>
                  <StatLabel>Variance vs Average<InfoTip label="How much this month deviates from your 12-month average. Large positive swings are a good time to fund estimated taxes and savings goals." /></StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>this month vs avg</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>
        </Box>
        <Divider />
        {/* Quarterly Tax Estimates */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Quarterly Tax Estimates
            <InfoTip label="Self-employed individuals must pay estimated taxes quarterly to avoid underpayment penalties. The safe harbor is the lesser of 90% of current-year tax or 100%/110% of prior-year tax." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">Q1–Q4 Payment Schedule</Heading></CardHeader>
            <CardBody overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>Quarter</Th>
                    <Th>Income Period</Th>
                    <Th>Due Date</Th>
                    <Th isNumeric>Est. Payment</Th>
                    <Th>Status</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {quarterlySchedule.map((q) => (
                    <Tr key={q.quarter}>
                      <Td fontWeight="medium">{q.quarter}</Td>
                      <Td color="text.secondary">{q.period}</Td>
                      <Td>{q.dueDate}</Td>
                      <Td isNumeric>—</Td>
                      <Td><Badge colorScheme="blue">{q.status}</Badge></Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
              <Text fontSize="xs" color="text.secondary" mt={3}>
                Payment estimates populate once your income and prior-year tax data
                are connected. Self-employment tax (15.3%) is included.
              </Text>
            </CardBody>
          </Card>
        </Box>
        <Divider />
        {/* Minimum Budget Floor */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Minimum Budget Floor
            <InfoTip label="Your safe spending floor is based on the lowest-income month in the trailing 12 months. Keeping monthly spending at or below this floor ensures you can cover expenses even in a dry month." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">Safe Spending Floor</Heading></CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Lowest Monthly Income (trailing 12 mo)
                    <InfoTip label="The minimum monthly income in the past year. Used as the conservative baseline for setting your spending floor." />
                  </Text>
                  <Text fontWeight="semibold">—</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Recommended Monthly Spending Cap
                    <InfoTip label="80% of your lowest monthly income, leaving a 20% buffer for taxes and savings even in your worst month." />
                  </Text>
                  <Text fontWeight="semibold" color="green.600">—</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Your Average Monthly Spend</Text>
                  <Text fontWeight="semibold">—</Text>
                </HStack>
                <Divider />
                <Text fontSize="xs" color="text.secondary">
                  Connect transactions to calculate your actual spending baseline
                  and compare it against your safe floor.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </Box>
      </VStack>
    </Container>
  );
};

export default VariableIncomePage;
