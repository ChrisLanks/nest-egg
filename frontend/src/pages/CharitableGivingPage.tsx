/**
 * Charitable Giving page.
 *
 * Helps users optimize their charitable strategy with tax-smart giving:
 * DAF contributions, gift bunching, qualified charitable distributions,
 * and appreciated securities.
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

export const CharitableGivingPage = () => {
  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        <Box>
          <Heading size="lg">Charitable Giving</Heading>
          <Text color="text.secondary" mt={1}>
            Optimize your charitable strategy with tax-smart giving — DAF
            contributions, gift bunching, qualified charitable distributions,
            and appreciated securities.
          </Text>
        </Box>
        <Alert status="info" borderRadius="lg" w="full">
          <AlertIcon />
          <Text fontSize="sm">
            Connect charitable transactions to track YTD giving and unlock
            bunching and QCD analysis.
          </Text>
        </Alert>
        {/* Donation History */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Donation History
            <InfoTip label="Cash donations to public charities are deductible up to 60% of AGI. Appreciated securities donated directly avoid capital gains and provide a deduction at FMV. DAF contributions get an immediate deduction; grants can be distributed over time." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <HStack justify="space-between">
                <Heading size="sm">YTD Giving vs Prior Years</Heading>
                <Stat textAlign="right" minW="100px">
                  <StatLabel>YTD Total</StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>2026</StatHelpText>
                </Stat>
              </HStack>
            </CardHeader>
            <CardBody overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>Date</Th>
                    <Th>Organization</Th>
                    <Th>Method</Th>
                    <Th isNumeric>Amount</Th>
                    <Th>Deductible</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  <Tr>
                    <Td colSpan={5}>
                      <Text color="text.secondary" fontSize="sm" textAlign="center" py={4}>
                        No donations recorded yet. Add charitable transactions to
                        track your deductible giving history.
                      </Text>
                    </Td>
                  </Tr>
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        </Box>
        <Divider />
        {/* Bunching Analysis */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Bunching Analysis
            <InfoTip label="Bunching concentrates two or more years of charitable giving into a single tax year to exceed the standard deduction threshold, then takes the standard deduction in the off year. A DAF makes bunching easy: contribute a lump sum to get the deduction, then grant to charities over multiple years." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">Annual vs Bunched Strategy Tax Savings</Heading></CardHeader>
            <CardBody>
              <HStack spacing={8} flexWrap="wrap" mb={4}>
                <Stat>
                  <StatLabel>
                    2026 Standard Deduction (Single)
                    <InfoTip label="Taxpayers must exceed the standard deduction for charitable deductions to provide tax benefit. Bunching helps clear this threshold." />
                  </StatLabel>
                  <StatNumber fontSize="lg">$15,000</StatNumber>
                  <StatHelpText>est. 2026 single filer</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>
                    2026 Standard Deduction (MFJ)
                    <InfoTip label="Married filing jointly standard deduction for 2026." />
                  </StatLabel>
                  <StatNumber fontSize="lg">$30,000</StatNumber>
                  <StatHelpText>est. 2026 married</StatHelpText>
                </Stat>
              </HStack>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Annual Giving Strategy — Est. Tax Savings</Text>
                  <Text fontWeight="semibold">—</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Bunched Strategy (2-year) — Est. Tax Savings
                    <InfoTip label="Giving two years of donations in one year creates an itemized deduction exceeding the standard deduction. The alternate year uses the standard deduction." />
                  </Text>
                  <Text fontWeight="semibold" color="green.600">—</Text>
                </HStack>
                <Text fontSize="xs" color="text.secondary">
                  Enter your annual giving amount and marginal tax rate to compare
                  the net tax benefit of bunching vs annual giving.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </Box>
        <Divider />
        {/* QCD Opportunity */}
        <Box w="full">
          <Heading size="md" mb={3}>
            QCD Opportunity
            <InfoTip label="Qualified Charitable Distributions allow IRA owners age 70.5+ to donate up to $105,000 per year (2026) directly from an IRA to a qualified charity. The distribution is excluded from gross income and satisfies RMDs." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">IRA Qualified Charitable Distributions (Age 70.5+)</Heading></CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    2026 QCD Annual Limit (per taxpayer)
                    <InfoTip label="The annual QCD limit is indexed to inflation. Estimated at $105,000 for 2026. A married couple can each do $105,000 from their own IRAs." />
                  </Text>
                  <Text fontWeight="semibold">$105,000</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Eligible Accounts
                    <InfoTip label="QCDs can only be made from Traditional IRAs. They cannot be made from 401(k) or 403(b) accounts directly." />
                  </Text>
                  <Badge colorScheme="blue">Traditional IRA only</Badge>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    RMD Satisfaction
                    <InfoTip label="A QCD counts toward your RMD for the year. One of the only ways to satisfy an RMD without recognizing the income." />
                  </Text>
                  <Badge colorScheme="green">Satisfies RMD</Badge>
                </HStack>
                <Divider />
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Your IRA Balance (Traditional)</Text>
                  <Text fontWeight="semibold">—</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Eligibility</Text>
                  <Text color="text.secondary" fontSize="xs">
                    Connect your IRA and verify birthdate to check eligibility
                  </Text>
                </HStack>
              </VStack>
            </CardBody>
          </Card>
        </Box>
      </VStack>
    </Container>
  );
};

export default CharitableGivingPage;
