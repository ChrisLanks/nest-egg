/**
 * Loan Modeler page.
 *
 * Models any loan before the user takes it. Calculates affordability,
 * full amortization, and compares buying vs leasing for major purchases.
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

export const LoanModelerPage = () => {
  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        <Box>
          <Heading size="lg">Loan Modeler</Heading>
          <Text color="text.secondary" mt={1}>
            Model any loan before you take it. Calculate affordability, full
            amortization, and compare buying vs leasing for major purchases.
          </Text>
        </Box>
        <Alert status="info" borderRadius="lg" w="full">
          <AlertIcon />
          <Text fontSize="sm">
            Enter loan parameters to generate an affordability analysis and
            full amortization schedule.
          </Text>
        </Alert>
        {/* Affordability Check */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Affordability Check
            <InfoTip label="Lenders use two DTI thresholds: front-end (housing costs only, target below 28%) and back-end (all debts, target below 36%). FHA allows up to 43% back-end DTI with compensating factors." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">Monthly Payment + DTI Impact</Heading></CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
                <Stat>
                  <StatLabel>
                    Estimated Monthly Payment
                    <InfoTip label="Principal + interest. Does not include taxes, insurance, or PMI for mortgages." />
                  </StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>enter loan details</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>
                    Front-End DTI
                    <InfoTip label="Housing payment as a percentage of gross monthly income. Conventional lenders prefer below 28%." />
                  </StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>target: below 28%</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>
                    Back-End DTI
                    <InfoTip label="All monthly debt obligations as a percentage of gross monthly income. Target: below 36%." />
                  </StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>target: below 36%</StatHelpText>
                </Stat>
              </SimpleGrid>
              <Text fontSize="xs" color="text.secondary">
                Enter loan amount, interest rate, term, and your gross monthly
                income to calculate affordability metrics.
              </Text>
            </CardBody>
          </Card>
        </Box>
        <Divider />
        {/* Amortization Schedule */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Amortization Schedule
            <InfoTip label="Shows how each payment splits between principal and interest over the life of the loan. Early payments are mostly interest; later payments shift toward principal. Extra payments reduce total interest significantly." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">Total Interest Over Life of Loan</Heading></CardHeader>
            <CardBody overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>Year</Th>
                    <Th isNumeric>Principal Paid</Th>
                    <Th isNumeric>Interest Paid</Th>
                    <Th isNumeric>Cumulative Interest</Th>
                    <Th isNumeric>Remaining Balance</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  <Tr>
                    <Td colSpan={5}>
                      <Text color="text.secondary" fontSize="sm" textAlign="center" py={4}>
                        Enter loan parameters above to generate the full amortization table.
                      </Text>
                    </Td>
                  </Tr>
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        </Box>
        <Divider />
        {/* Buy vs Lease */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Buy vs Lease
            <InfoTip label="Buying builds equity and avoids mileage penalties but has higher monthly payments. Leasing offers lower monthly payments and easy vehicle turnover but you have nothing at end of term. The break-even depends on miles driven, vehicle depreciation, and how long you keep the car." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">Total Cost Comparison (Vehicles)</Heading></CardHeader>
            <CardBody>
              <HStack spacing={8} flexWrap="wrap" mb={4}>
                <Stat>
                  <StatLabel>
                    Buy — Total Cost
                    <InfoTip label="Loan payments + estimated maintenance + insurance minus residual value at end of ownership period." />
                  </StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>over ownership period</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>
                    Lease — Total Cost
                    <InfoTip label="Total lease payments + acquisition fees + disposition fee." />
                  </StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>over lease period</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>Better Option</StatLabel>
                  <StatNumber fontSize="lg">
                    <Badge colorScheme="gray">—</Badge>
                  </StatNumber>
                  <StatHelpText>based on inputs</StatHelpText>
                </Stat>
              </HStack>
              <Text fontSize="xs" color="text.secondary">
                Enter vehicle price, financing rate, lease terms, and expected
                ownership duration to compare total-cost-of-ownership scenarios.
              </Text>
            </CardBody>
          </Card>
        </Box>
      </VStack>
    </Container>
  );
};

export default LoanModelerPage;
