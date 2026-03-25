/**
 * Estate & Beneficiary Planning page.
 *
 * Ensures assets go where the user intends. Tracks beneficiary designations,
 * models estate tax exposure, and monitors key planning documents.
 */

import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  CardHeader,
  Checkbox,
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
import { FiCheckCircle, FiInfo } from "react-icons/fi";

function InfoTip({ label }: { label: string }) {
  return (
    <Tooltip label={label} placement="top" hasArrow maxW="260px">
      <Box as="span" display="inline-flex" ml={1} verticalAlign="middle" cursor="help">
        <Icon as={FiInfo} boxSize={3} color="text.muted" />
      </Box>
    </Tooltip>
  );
}

const planningDocuments = [
  { name: "Last Will & Testament", description: "Directs distribution of assets not covered by beneficiary designations or trusts." },
  { name: "Revocable Living Trust", description: "Avoids probate, provides privacy, and allows for incapacity planning." },
  { name: "Durable Power of Attorney", description: "Authorizes someone to manage financial affairs if you become incapacitated." },
  { name: "Healthcare Directive / Living Will", description: "States your wishes for medical treatment if you cannot speak for yourself." },
  { name: "Healthcare Proxy / Medical POA", description: "Designates someone to make medical decisions on your behalf." },
  { name: "Beneficiary Designations Review", description: "Retirement accounts and life insurance pass outside the will — review annually." },
];

export const EstatePage = () => {
  return (
    <Container maxW="5xl" py={6}>
      <VStack align="start" spacing={6}>
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
        {/* Beneficiary Coverage */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Beneficiary Coverage
            <InfoTip label="Beneficiary designations on retirement accounts (401k, IRA), life insurance, and TOD/POD bank accounts supersede your will. Accounts without a named beneficiary may pass through probate." />
          </Heading>
          <Card variant="outline" w="full">
            <CardBody overflowX="auto">
              <Table size="sm">
                <Thead><Tr><Th>Account</Th><Th>Type</Th><Th>Primary Beneficiary</Th><Th>Contingent Beneficiary</Th><Th>Status</Th></Tr></Thead>
                <Tbody>
                  <Tr><Td colSpan={5}>
                    <Text color="text.secondary" fontSize="sm" textAlign="center" py={4}>
                      Connect accounts to audit beneficiary designations. Missing designations are flagged automatically.
                    </Text>
                  </Td></Tr>
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        </Box>
        <Divider />
        {/* Estate Tax Exposure */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Estate Tax Exposure
            <InfoTip label="The federal estate tax applies to estates exceeding the exemption at death. The 2026 per-person exemption is $13.99M. Married couples may use portability to combine exemptions." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}><Heading size="sm">Net Worth vs Federal Exemption</Heading></CardHeader>
            <CardBody>
              <VStack align="start" spacing={3} fontSize="sm">
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">2026 Federal Exemption (per person)<InfoTip label="The TCJA exemption sunset reduces the per-person exemption from ~$13.99M in 2025 to approximately $7M in 2026 unless Congress acts." /></Text>
                  <Text fontWeight="semibold">$13,990,000</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Married Couple Combined Exemption<InfoTip label="Portability allows a surviving spouse to use the deceased spouse unused exemption (DSUE), effectively doubling the shield for married couples." /></Text>
                  <Text fontWeight="semibold">$27,980,000</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Federal Estate Tax Rate (above exemption)</Text>
                  <Badge colorScheme="red">40%</Badge>
                </HStack>
                <Divider />
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Your Estimated Net Worth</Text>
                  <Text fontWeight="semibold">—</Text>
                </HStack>
                <HStack justify="space-between" w="full">
                  <Text color="text.secondary">Estimated Estate Tax Exposure<InfoTip label="Amount by which your taxable estate exceeds the applicable exemption, multiplied by the 40% top rate." /></Text>
                  <Text fontWeight="semibold" color="green.600">Below exemption threshold</Text>
                </HStack>
                <Text fontSize="xs" color="text.secondary">
                  Consult an estate attorney for strategies including irrevocable trusts,
                  annual gifting ($18,000/year exclusion), and charitable remainder trusts.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </Box>
        <Divider />
        {/* Planning Documents */}
        <Box w="full">
          <Heading size="md" mb={3}>
            Planning Documents
            <InfoTip label="A comprehensive estate plan typically includes these six documents. Check off the ones you have in place and review each after major life events." />
          </Heading>
          <Card variant="outline" w="full">
            <CardHeader pb={0}>
              <HStack><Icon as={FiCheckCircle} color="green.500" /><Heading size="sm">Document Checklist</Heading></HStack>
            </CardHeader>
            <CardBody>
              <VStack align="start" spacing={3}>
                {planningDocuments.map((doc) => (
                  <Box key={doc.name} w="full">
                    <Checkbox colorScheme="green" size="sm">
                      <Text fontWeight="medium" fontSize="sm">{doc.name}</Text>
                    </Checkbox>
                    <Text fontSize="xs" color="text.secondary" ml={6}>{doc.description}</Text>
                  </Box>
                ))}
              </VStack>
            </CardBody>
          </Card>
        </Box>
      </VStack>
    </Container>
  );
};

export default EstatePage;
