/**
 * Equity Compensation page.
 *
 * Helps users track stock options (ISO/NSO), RSUs, and equity grants.
 * Models vesting schedules, exercise strategies, and AMT exposure.
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

export const EquityPage = () => {
  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
        {/* Header */}
        <Box>
          <Heading size="lg">Equity Compensation</Heading>
          <Text color="text.secondary" mt={1}>
            Track your stock options (ISO/NSO), RSUs, and equity grants. Model
            vesting schedules, exercise strategies, and AMT exposure.
          </Text>
        </Box>

        <Alert status="info" borderRadius="lg" w="full">
          <AlertIcon />
          <Text fontSize="sm">
            Connect your equity accounts or manually add grants to unlock full
            vesting calendar and tax modeling.
          </Text>
        </Alert>

        {/* Vesting Calendar */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Vesting Calendar
            <InfoTip label="Upcoming vest events across all your equity grants, sorted by vest date. RSU vests are ordinary income; ISO/NSO exercise decisions have different AMT implications." />
          </Heading>
          <Card variant="outline" w="full">
            <CardBody overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>Grant</Th>
                    <Th>Type</Th>
                    <Th>Vest Date</Th>
                    <Th isNumeric>Shares</Th>
                    <Th isNumeric>Est. Value</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  <Tr>
                    <Td colSpan={5}>
                      <Text color="text.secondary" fontSize="sm" textAlign="center" py={4}>
                        No equity grants added yet. Add grants to see upcoming vest events.
                      </Text>
                    </Td>
                  </Tr>
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* Exercise Modeling */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Exercise Modeling
            <InfoTip label="ISOs (Incentive Stock Options) receive preferential tax treatment but trigger AMT on the spread. NSOs (Non-Qualified Stock Options) are taxed as ordinary income at exercise. Optimal exercise timing depends on your income, AMT exposure, and the company trajectory." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">ISO vs NSO Tax Impact Summary</Heading>
            </CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    ISO Spread at Exercise
                    <InfoTip label="The difference between fair market value and strike price at exercise. This spread is an AMT preference item — it won't appear as regular income but increases your AMTI." />
                  </Text>
                  <Badge colorScheme="blue">AMT Preference Item</Badge>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    NSO Spread at Exercise
                    <InfoTip label="The spread on NSO exercise is reported as W-2 wages (if from an employer) or self-employment income. Subject to income tax and FICA." />
                  </Text>
                  <Badge colorScheme="orange">Ordinary Income</Badge>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">
                    RSU Vesting
                    <InfoTip label="RSU shares vesting are taxed as ordinary income based on the FMV at vest. Cost basis is established at vest price. Future appreciation is taxed as capital gains." />
                  </Text>
                  <Badge colorScheme="orange">Ordinary Income at Vest</Badge>
                </HStack>
                <Divider />
                <Text color="text.secondary" fontSize="xs">
                  Add grants and income data above to model your specific exercise
                  strategy and optimal timing for early exercise elections (83(b)).
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </Box>

        <Divider />

        {/* AMT Exposure */}
        <Box w="full">
          <Heading size="md" mb={3}>
            AMT Exposure
            <InfoTip label="The Alternative Minimum Tax runs a parallel tax calculation. ISO exercise spreads are an AMT preference item. If your tentative minimum tax exceeds your regular tax, you owe the difference as AMT. AMT credits may be recoverable in future lower-income years." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <Heading size="sm">Estimated AMT Add-Back</Heading>
            </CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">AMT Exemption (2026 — Single)</Text>
                  <Text fontWeight="semibold">$89,075</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">AMT Exemption (2026 — MFJ)</Text>
                  <Text fontWeight="semibold">$126,500</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">AMT Rate on AMTI above exemption</Text>
                  <Text fontWeight="semibold">26% / 28%</Text>
                </HStack>
                <Divider />
                <Text color="text.secondary" fontSize="xs">
                  Enter your ISO grants and projected exercise details to calculate
                  your estimated AMT exposure and the optimal safe harbor exercise amount.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </Box>
      </VStack>
    </Container>
  );
};

export default EquityPage;
