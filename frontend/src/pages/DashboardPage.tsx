/**
 * Dashboard page (placeholder)
 */

import {
  Box,
  Container,
  Heading,
  Text,
  Button,
  VStack,
  HStack,
  Card,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
} from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useLogout } from '../features/auth/hooks/useAuth';

export const DashboardPage = () => {
  const { user } = useAuthStore();
  const logoutMutation = useLogout();
  const navigate = useNavigate();

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="lg">
              Welcome back, {user?.first_name || 'User'}!
            </Heading>
            <Text color="gray.600">
              {user?.email} • Organization: {user?.organization_id}
            </Text>
          </VStack>
          <Button colorScheme="red" variant="outline" onClick={handleLogout}>
            Logout
          </Button>
        </HStack>

        {/* Summary Cards */}
        <HStack spacing={6} align="stretch">
          <Card flex={1}>
            <CardBody>
              <Stat>
                <StatLabel>Net Worth</StatLabel>
                <StatNumber>$0.00</StatNumber>
                <StatHelpText>No data yet</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card flex={1}>
            <CardBody>
              <Stat>
                <StatLabel>Total Assets</StatLabel>
                <StatNumber>$0.00</StatNumber>
                <StatHelpText>No data yet</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card flex={1}>
            <CardBody>
              <Stat>
                <StatLabel>Total Debts</StatLabel>
                <StatNumber>$0.00</StatNumber>
                <StatHelpText>No data yet</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </HStack>

        {/* Placeholder Content */}
        <Box bg="white" p={8} borderRadius="lg" boxShadow="sm">
          <VStack spacing={4} align="start">
            <Heading size="md">🎉 Authentication Successful!</Heading>
            <Text color="gray.600">
              You've successfully logged in to Nest Egg. The dashboard is currently a placeholder.
            </Text>
            <Text color="gray.600">
              Next steps:
            </Text>
            <VStack align="start" pl={4} spacing={2}>
              <Text>• Set up Plaid integration to connect bank accounts ✅</Text>
              <Text>• Add transaction tracking and labeling ✅ (mock data)</Text>
              <Text>• Build investment tracking features</Text>
              <Text>• Create custom reports and predictions</Text>
            </VStack>
            <Button
              colorScheme="brand"
              size="lg"
              onClick={() => navigate('/transactions')}
              mt={4}
            >
              View Mock Transactions (30 txns)
            </Button>
          </VStack>
        </Box>
      </VStack>
    </Container>
  );
};
