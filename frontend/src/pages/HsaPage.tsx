/**
 * HSA Optimizer page.
 *
 * Helps users maximize their Health Savings Account's triple-tax advantage:
 * tax-deductible contributions, tax-free growth, and tax-free withdrawals
 * for qualified medical expenses.
 */

import {
  Alert,
  AlertIcon,
  Box,
  Card,
  CardBody,
  CardHeader,
  Container,
  Divider,
  Heading,
  HStack,
  Icon,
  Progress,
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

export const HsaPage = () => {
  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">HSA Optimizer</Heading>
          <Text color="text.secondary" mt={1}>
            Maximize your Health Savings Account's triple-tax advantage —
            tax-deductible contributions, tax-free growth, and tax-free
            withdrawals for medical expenses.
          </Text>
        </Box>

        <Alert status="info" borderRadius="lg" w="full">
          <AlertIcon />
          <Text fontSize="sm">
            Add your HSA account to enable contribution tracking and long-term
            investment projections.
          </Text>
        </Alert>

        {/* Contribution Headroom */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Contribution Headroom
            <InfoTip label="The IRS sets annual HSA contribution limits based on your coverage type. For 2026: $4,300 (self-only) and $8,550 (family). Catch-up contributions of $1,000 allowed for age 55+. Contributions made directly are deductible; payroll contributions avoid FICA too." />
          </Heading>
          <Card variant="outline" w="full">
            <CardBody>
              <VStack align="start" spacing={4} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    2026 Limit — Self-Only Coverage
                    <InfoTip label="HDHP self-only coverage contribution limit for 2026." />
                  </Text>
                  <Text fontWeight="semibold">$4,300</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    2026 Limit — Family Coverage
                    <InfoTip label="HDHP family coverage contribution limit for 2026." />
                  </Text>
                  <Text fontWeight="semibold">$8,550</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    Catch-Up (Age 55+)
                    <InfoTip label="Additional $1,000 catch-up contribution allowed per year once you turn 55." />
                  </Text>
                  <Text fontWeight="semibold">+$1,000</Text>
                </HStack>
                <Divider />
                <Box w="full">
                  <HStack justify="space-between" mb={1}>
                    <Text color="text.secondary">YTD Contributions</Text>
                    <Text>$0 / $4,300</Text>
                  </HStack>
                  <Progress value={0} colorScheme="green" borderRadius="md" size="sm" />
                  <Text fontSize="xs" color="text.secondary" mt={1}>
                    Connect your HSA account to track YTD contributions automatically.
                  </Text>
                </Box>
              </VStack>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* Invest vs Spend Strategy */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Invest vs Spend Strategy
            <InfoTip label="Paying medical bills out-of-pocket today and letting your HSA grow tax-free can dramatically increase long-term value. You can reimburse yourself years later — with no deadline for claims — as long as you have receipts." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">Projected Long-Term Value</Heading>
            </CardHeader>
            <CardBody>
              <HStack spacing={6} flexWrap="wrap">
                <Stat>
                  <StatLabel>
                    Reimburse as You Go
                    <InfoTip label="Pay medical bills with HSA funds as incurred. Balance grows more slowly since withdrawals offset contributions." />
                  </StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>est. balance at age 65</StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>
                    Invest + Defer
                    <InfoTip label="Pay medical costs out of pocket now, invest HSA contributions in equities, and reimburse yourself later. Historically produces 3-5x the balance of spend-as-you-go strategy." />
                  </StatLabel>
                  <StatNumber fontSize="lg">—</StatNumber>
                  <StatHelpText>est. balance at age 65</StatHelpText>
                </Stat>
              </HStack>
              <Text fontSize="xs" color="text.secondary" mt={3}>
                Add your HSA balance and annual contribution to model the long-term
                difference between investing vs spending your HSA funds.
              </Text>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* Receipt Shoebox */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Receipt Shoebox
            <InfoTip label="There is no deadline to reimburse yourself from your HSA for qualified medical expenses — as long as the expense was incurred after you opened the HSA. Store receipts here to claim tax-free reimbursements in future years." />
          </Heading>
          <Card variant="outline" w="full">
            <CardBody overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>Date</Th>
                    <Th>Description</Th>
                    <Th>Provider</Th>
                    <Th isNumeric>Amount</Th>
                    <Th>Status</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  <Tr>
                    <Td colSpan={5}>
                      <Text color="text.secondary" fontSize="sm" textAlign="center" py={4}>
                        No receipts stored yet. Add qualified medical expense receipts
                        to track future reimbursement opportunities.
                      </Text>
                    </Td>
                  </Tr>
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        </Box>
      </VStack>
    </Container>
  );
};

export default HsaPage;
