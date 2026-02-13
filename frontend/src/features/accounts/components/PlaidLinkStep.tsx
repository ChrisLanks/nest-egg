/**
 * Plaid Link integration step
 */

import { useState, useEffect } from 'react';
import {
  VStack,
  Button,
  HStack,
  Text,
  Spinner,
  Center,
  Box,
  SimpleGrid,
  Icon,
  useToast,
} from '@chakra-ui/react';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { FiCheck } from 'react-icons/fi';
import { usePlaidLink } from 'react-plaid-link';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../../../services/api';

interface PlaidLinkStepProps {
  onSuccess: () => void;
  onBack: () => void;
}

// Dummy institutions for test mode
const TEST_INSTITUTIONS = [
  { id: 'chase', name: 'Chase Bank', logo: '🏦' },
  { id: 'bofa', name: 'Bank of America', logo: '🏦' },
  { id: 'wells', name: 'Wells Fargo', logo: '🏦' },
  { id: 'citi', name: 'Citibank', logo: '🏦' },
  { id: 'usbank', name: 'US Bank', logo: '🏦' },
  { id: 'pnc', name: 'PNC Bank', logo: '🏦' },
];

export const PlaidLinkStep = ({ onSuccess, onBack }: PlaidLinkStepProps) => {
  const [isTestMode, setIsTestMode] = useState(false);
  const [selectedInstitution, setSelectedInstitution] = useState<string | null>(null);
  const toast = useToast();

  // Fetch link token
  const { data: linkTokenData, isLoading: isLoadingToken } = useQuery({
    queryKey: ['plaid-link-token'],
    queryFn: async () => {
      const response = await api.post('/plaid/link-token', {});
      return response.data;
    },
  });

  // Check if we're in test mode (dummy token)
  useEffect(() => {
    if (linkTokenData?.link_token?.startsWith('link-sandbox-')) {
      setIsTestMode(true);
    }
  }, [linkTokenData]);

  // Exchange public token mutation
  const exchangeTokenMutation = useMutation({
    mutationFn: async (data: {
      public_token: string;
      institution_id?: string;
      institution_name?: string;
    }) => {
      const response = await api.post('/plaid/exchange-token', data);
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Accounts connected',
        description: 'Your bank accounts have been successfully linked.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onSuccess();
    },
    onError: (error: any) => {
      toast({
        title: 'Connection failed',
        description: error.response?.data?.detail || 'Failed to connect accounts.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Plaid Link callbacks
  const onPlaidSuccess = async (public_token: string, metadata: any) => {
    exchangeTokenMutation.mutate({
      public_token,
      institution_id: metadata.institution?.institution_id,
      institution_name: metadata.institution?.name,
    });
  };

  const onPlaidExit = (error: any, _metadata: any) => {
    if (error) {
      console.error('Plaid Link error:', error);
      toast({
        title: 'Connection cancelled',
        description: error.error_message || 'Failed to connect bank account.',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  // Initialize Plaid Link
  const { open, ready } = usePlaidLink({
    token: linkTokenData?.link_token || '',
    onSuccess: onPlaidSuccess,
    onExit: onPlaidExit,
  });

  // Handle test institution selection
  const handleTestInstitutionSelect = (institutionId: string, institutionName: string) => {
    setSelectedInstitution(institutionId);

    // Simulate token exchange with dummy data
    exchangeTokenMutation.mutate({
      public_token: `public-sandbox-${institutionId}-${Date.now()}`,
      institution_id: institutionId,
      institution_name: institutionName,
    });
  };

  if (isLoadingToken) {
    return (
      <VStack spacing={6} align="stretch">
        <HStack>
          <Button
            variant="ghost"
            leftIcon={<ArrowBackIcon />}
            onClick={onBack}
            size="sm"
          >
            Back
          </Button>
        </HStack>

        <Center py={12}>
          <VStack spacing={4}>
            <Spinner size="xl" color="brand.500" />
            <Text color="gray.600">Preparing connection...</Text>
          </VStack>
        </Center>
      </VStack>
    );
  }

  // Test mode UI - show bank selection
  if (isTestMode) {
    return (
      <VStack spacing={6} align="stretch">
        <HStack>
          <Button
            variant="ghost"
            leftIcon={<ArrowBackIcon />}
            onClick={onBack}
            size="sm"
            isDisabled={exchangeTokenMutation.isPending}
          >
            Back
          </Button>
        </HStack>

        <Box>
          <Text fontSize="md" color="gray.600" mb={4}>
            Select your bank to connect (Test Mode)
          </Text>
          <Text fontSize="sm" color="orange.600" mb={4}>
            🧪 Test mode: Using dummy data for test@test.com
          </Text>
        </Box>

        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
          {TEST_INSTITUTIONS.map((institution) => (
            <Box
              key={institution.id}
              as="button"
              onClick={() => !exchangeTokenMutation.isPending && handleTestInstitutionSelect(institution.id, institution.name)}
              p={4}
              borderWidth={2}
              borderRadius="md"
              borderColor={selectedInstitution === institution.id ? 'brand.500' : 'gray.200'}
              bg={selectedInstitution === institution.id ? 'brand.50' : 'white'}
              _hover={{
                borderColor: 'brand.500',
                bg: 'brand.50',
                transform: 'translateY(-2px)',
                shadow: 'sm',
              }}
              transition="all 0.2s"
              cursor={exchangeTokenMutation.isPending ? 'not-allowed' : 'pointer'}
              opacity={exchangeTokenMutation.isPending ? 0.6 : 1}
              position="relative"
            >
              <HStack spacing={3}>
                <Text fontSize="2xl">{institution.logo}</Text>
                <Text fontWeight="medium">{institution.name}</Text>
                {selectedInstitution === institution.id && exchangeTokenMutation.isPending && (
                  <Spinner size="sm" color="brand.500" ml="auto" />
                )}
                {selectedInstitution === institution.id && !exchangeTokenMutation.isPending && (
                  <Icon as={FiCheck} color="brand.500" ml="auto" />
                )}
              </HStack>
            </Box>
          ))}
        </SimpleGrid>

        <Text fontSize="xs" color="gray.500" textAlign="center">
          In production, this will open the secure Plaid Link interface
        </Text>
      </VStack>
    );
  }

  // Production mode - use real Plaid Link
  return (
    <VStack spacing={6} align="stretch">
      <HStack>
        <Button
          variant="ghost"
          leftIcon={<ArrowBackIcon />}
          onClick={onBack}
          size="sm"
        >
          Back
        </Button>
      </HStack>

      <Center py={12}>
        <VStack spacing={6}>
          <Text fontSize="lg" fontWeight="medium">
            Connect Your Bank Account
          </Text>
          <Text fontSize="sm" color="gray.600" textAlign="center" maxW="md">
            Click below to securely connect your bank account through Plaid.
            Your credentials are never stored by us.
          </Text>
          <Button
            colorScheme="brand"
            size="lg"
            onClick={() => open()}
            isDisabled={!ready || exchangeTokenMutation.isPending}
            isLoading={exchangeTokenMutation.isPending}
          >
            Continue to Bank Login
          </Button>
        </VStack>
      </Center>
    </VStack>
  );
};
