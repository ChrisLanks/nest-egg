/**
 * RMD Alert Component
 *
 * Displays Required Minimum Distribution information for users age 73+
 */

import {
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Card,
  CardBody,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import api from '../../../services/api';

interface AccountRMD {
  account_id: string;
  account_name: string;
  account_type: string;
  account_balance: number;
  required_distribution: number;
  distribution_taken: number;
  remaining_required: number;
}

interface RMDSummary {
  user_age: number;
  requires_rmd: boolean;
  rmd_deadline: string | null;
  total_required_distribution: number;
  total_distribution_taken: number;
  total_remaining_required: number;
  accounts: AccountRMD[];
  penalty_if_missed: number | null;
}

interface RMDAlertProps {
  /** Optional user ID filter (null = combined household view) */
  userId?: string | null;
}

export const RMDAlert: React.FC<RMDAlertProps> = ({ userId = null }) => {
  const { isOpen, onOpen, onClose } = useDisclosure();

  const { data: rmdData, isLoading, error } = useQuery<RMDSummary>({
    queryKey: ['rmd-summary', userId],
    queryFn: async () => {
      const params = userId ? { user_id: userId } : {};
      const response = await api.get('/holdings/rmd-summary', { params });
      return response.data;
    },
    retry: false,
    // Don't show error if user doesn't have birthdate set
    useErrorBoundary: false,
  });

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Format date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Don't show anything if loading or error (user may not have birthdate)
  if (isLoading || error || !rmdData) return null;

  // Don't show if RMD not required
  if (!rmdData.requires_rmd) return null;

  const percentageTaken = rmdData.total_required_distribution > 0
    ? (rmdData.total_distribution_taken / rmdData.total_required_distribution) * 100
    : 0;

  return (
    <>
      <Alert
        status={rmdData.total_remaining_required > 0 ? 'warning' : 'success'}
        variant="left-accent"
        borderRadius="md"
      >
        <AlertIcon />
        <Box flex="1">
          <AlertTitle fontSize="md">
            {rmdData.total_remaining_required > 0
              ? 'Required Minimum Distribution Due'
              : 'RMD Requirement Met'}
          </AlertTitle>
          <AlertDescription fontSize="sm">
            <VStack align="start" spacing={2} mt={2}>
              <Text>
                <strong>{formatCurrency(rmdData.total_remaining_required)}</strong> remaining
                required withdrawal by <strong>{formatDate(rmdData.rmd_deadline)}</strong>
              </Text>
              {rmdData.penalty_if_missed && rmdData.penalty_if_missed > 0 && (
                <HStack>
                  <Badge colorScheme="red">Penalty Risk</Badge>
                  <Text fontSize="xs" color="text.secondary">
                    {formatCurrency(rmdData.penalty_if_missed)} penalty if missed (25%)
                  </Text>
                </HStack>
              )}
              <Button size="sm" colorScheme="blue" variant="link" onClick={onOpen}>
                View Details →
              </Button>
            </VStack>
          </AlertDescription>
        </Box>
      </Alert>

      {/* RMD Details Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Required Minimum Distribution Details</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={6} align="stretch">
              {/* Summary Stats */}
              <SimpleGrid columns={3} spacing={4}>
                <Card>
                  <CardBody>
                    <Stat size="sm">
                      <StatLabel>Your Age</StatLabel>
                      <StatNumber>{rmdData.user_age}</StatNumber>
                    </Stat>
                  </CardBody>
                </Card>
                <Card>
                  <CardBody>
                    <Stat size="sm">
                      <StatLabel>Total Required</StatLabel>
                      <StatNumber fontSize="lg">
                        {formatCurrency(rmdData.total_required_distribution)}
                      </StatNumber>
                      <StatHelpText>By {formatDate(rmdData.rmd_deadline)}</StatHelpText>
                    </Stat>
                  </CardBody>
                </Card>
                <Card>
                  <CardBody>
                    <Stat size="sm">
                      <StatLabel>Remaining</StatLabel>
                      <StatNumber fontSize="lg" color="orange.600">
                        {formatCurrency(rmdData.total_remaining_required)}
                      </StatNumber>
                      <StatHelpText>
                        {percentageTaken.toFixed(0)}% taken
                      </StatHelpText>
                    </Stat>
                  </CardBody>
                </Card>
              </SimpleGrid>

              {/* RMD Info */}
              <Alert status="info" borderRadius="md">
                <AlertIcon />
                <Box fontSize="sm">
                  <Text fontWeight="bold" mb={1}>
                    What is an RMD?
                  </Text>
                  <Text>
                    Required Minimum Distributions (RMDs) are mandatory withdrawals from
                    traditional retirement accounts starting at age 73. Failure to take RMDs
                    results in a 25% penalty on the amount not withdrawn.
                  </Text>
                </Box>
              </Alert>

              {/* Account Breakdown */}
              <Box>
                <Text fontWeight="bold" mb={3}>
                  RMD by Account
                </Text>
                <Table size="sm" variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Account</Th>
                      <Th isNumeric>Balance</Th>
                      <Th isNumeric>Required</Th>
                      <Th isNumeric>Remaining</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {rmdData.accounts.map((account) => (
                      <Tr key={account.account_id}>
                        <Td>
                          <VStack align="start" spacing={0}>
                            <Text fontWeight="medium">{account.account_name}</Text>
                            <Text fontSize="xs" color="text.muted">
                              {account.account_type.replace('_', ' ')}
                            </Text>
                          </VStack>
                        </Td>
                        <Td isNumeric>{formatCurrency(account.account_balance)}</Td>
                        <Td isNumeric>{formatCurrency(account.required_distribution)}</Td>
                        <Td isNumeric>
                          <Text
                            fontWeight="semibold"
                            color={
                              account.remaining_required > 0 ? 'orange.600' : 'finance.positive'
                            }
                          >
                            {formatCurrency(account.remaining_required)}
                          </Text>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button colorScheme="blue" onClick={onClose}>
              Close
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};
