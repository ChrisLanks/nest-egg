/**
 * Provider-agnostic bank linking step
 * Supports Plaid, Teller, and other providers
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

export type BankProvider = 'plaid' | 'teller';

interface BankLinkStepProps {
  provider: BankProvider;
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

export const BankLinkStep = ({ provider, onSuccess, onBack }: BankLinkStepProps) => {
  const [isTestMode, setIsTestMode] = useState(false);
  const [selectedInstitution, setSelectedInstitution] = useState<string | null>(null);
  const toast = useToast();

  // Fetch link token from unified endpoint
  const { data: linkTokenData, isLoading: isLoadingToken } = useQuery({
    queryKey: ['bank-link-token', provider],
    queryFn: async () => {
      const response = await api.post('/bank-linking/link-token', { provider });
      return response.data;
    },
  });

  // Check if we're in test mode (dummy token)
  useEffect(() => {
    if (linkTokenData?.link_token?.startsWith('link-sandbox-') ||
        linkTokenData?.link_token?.startsWith('https://teller.io/connect/')) {
      setIsTestMode(true);
    }
  }, [linkTokenData]);

  // Exchange public token mutation (unified endpoint)
  const exchangeTokenMutation = useMutation({
    mutationFn: async (data: {
      provider: BankProvider;
      public_token: string;
      institution_id: string;
      institution_name: string;
      accounts?: any[];
    }) => {
      const response = await api.post('/bank-linking/exchange-token', data);
      return response.data;
    },
    onSuccess: () => {
      const providerName = provider === 'plaid' ? 'Plaid' : 'Teller';
      toast({
        title: 'Accounts connected',
        description: `Your bank accounts have been successfully linked via ${providerName}.`,
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

  // Plaid Link callbacks (only used when provider === 'plaid')
  const onPlaidSuccess = async (public_token: string, metadata: any) => {
    exchangeTokenMutation.mutate({
      provider: 'plaid',
      public_token,
      institution_id: metadata.institution?.institution_id,
      institution_name: metadata.institution?.name,
      accounts: metadata.accounts,
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

  // Initialize Plaid Link (only when provider === 'plaid')
  const { open: openPlaid, ready: plaidReady } = usePlaidLink({
    token: provider === 'plaid' ? linkTokenData?.link_token || '' : '',
    onSuccess: onPlaidSuccess,
    onExit: onPlaidExit,
  });

  // Handle Teller connection (opens Teller Connect URL)
  const handleTellerConnect = () => {
    if (!linkTokenData?.link_token) return;

    // Open Teller Connect URL in a new window
    const tellerWindow = window.open(
      linkTokenData.link_token,
      'TellerConnect',
      'width=600,height=800'
    );

    // Listen for message from Teller window
    const handleMessage = (event: MessageEvent) => {
      // Verify origin for security
      if (!event.origin.includes('teller.io')) return;

      if (event.data.type === 'teller-connect-success') {
        const { enrollment_id, institution } = event.data;

        exchangeTokenMutation.mutate({
          provider: 'teller',
          public_token: enrollment_id,
          institution_id: institution.id,
          institution_name: institution.name,
          accounts: [],
        });

        tellerWindow?.close();
      }
    };

    window.addEventListener('message', handleMessage);

    // Cleanup listener when component unmounts
    return () => window.removeEventListener('message', handleMessage);
  };

  // Handle test institution selection
  const handleTestInstitutionSelect = (institutionId: string, institutionName: string) => {
    setSelectedInstitution(institutionId);

    // Simulate token exchange with dummy data
    exchangeTokenMutation.mutate({
      provider,
      public_token: `public-sandbox-${provider}-${institutionId}-${Date.now()}`,
      institution_id: institutionId,
      institution_name: institutionName,
      accounts: [],
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
    const providerName = provider === 'plaid' ? 'Plaid' : 'Teller';

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
            Select your bank to connect via {providerName} (Test Mode)
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
          In production, this will open the secure {providerName} interface
        </Text>
      </VStack>
    );
  }

  // Production mode - use real provider link
  const providerConfig = {
    plaid: {
      name: 'Plaid',
      description: 'Click below to securely connect your bank account through Plaid. Your credentials are never stored by us.',
      onOpen: () => openPlaid(),
      isReady: plaidReady,
    },
    teller: {
      name: 'Teller',
      description: 'Click below to securely connect your bank account through Teller. Your credentials are never stored by us.',
      onOpen: handleTellerConnect,
      isReady: true,
    },
  };

  const config = providerConfig[provider];

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
            Connect Your Bank Account via {config.name}
          </Text>
          <Text fontSize="sm" color="gray.600" textAlign="center" maxW="md">
            {config.description}
          </Text>
          <Button
            colorScheme="brand"
            size="lg"
            onClick={config.onOpen}
            isDisabled={!config.isReady || exchangeTokenMutation.isPending}
            isLoading={exchangeTokenMutation.isPending}
          >
            Continue to Bank Login
          </Button>
        </VStack>
      </Center>
    </VStack>
  );
};
