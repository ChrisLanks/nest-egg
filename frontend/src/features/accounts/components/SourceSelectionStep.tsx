/**
 * Source selection step for adding accounts
 */

import {
  VStack,
  Text,
  SimpleGrid,
  Box,
  Icon,
  Badge,
  Spinner,
  Tooltip,
} from '@chakra-ui/react';
import { FiLink, FiEdit3, FiDollarSign, FiAlertCircle } from 'react-icons/fi';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../../services/api';

export type AccountSource = 'plaid' | 'teller' | 'mx' | 'manual';

interface ProviderAvailability {
  plaid: boolean;
  teller: boolean;
  mx: boolean;
}

interface SourceSelectionStepProps {
  onSelectSource: (source: AccountSource) => void;
}

export const SourceSelectionStep = ({ onSelectSource }: SourceSelectionStepProps) => {
  const { data: availability, isLoading } = useQuery<ProviderAvailability>({
    queryKey: ['provider-availability'],
    queryFn: async () => {
      const response = await api.get('/accounts/providers/availability');
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <VStack spacing={6} align="center" py={8}>
        <Spinner size="lg" color="brand.500" />
        <Text color="text.secondary">Loading account providers...</Text>
      </VStack>
    );
  }

  const plaidEnabled = availability?.plaid ?? false;
  const tellerEnabled = availability?.teller ?? false;
  const mxEnabled = availability?.mx ?? false;

  return (
    <VStack spacing={6} align="stretch">
      <Text fontSize="md" color="text.secondary">
        Choose how you'd like to add your account
      </Text>

      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
        {/* Plaid */}
        <Tooltip
          label={!plaidEnabled ? "Plaid credentials not configured" : ""}
          placement="top"
          hasArrow
        >
          <Box
            as="button"
            onClick={plaidEnabled ? () => onSelectSource('plaid') : undefined}
            p={6}
            borderWidth={2}
            borderRadius="lg"
            borderColor="border.default"
            _hover={plaidEnabled ? {
              borderColor: 'brand.500',
              bg: 'brand.subtle',
              transform: 'translateY(-2px)',
              shadow: 'md',
            } : {}}
            transition="all 0.2s"
            cursor={plaidEnabled ? 'pointer' : 'not-allowed'}
            opacity={plaidEnabled ? 1 : 0.5}
            position="relative"
          >
            {!plaidEnabled && (
              <Icon
                as={FiAlertCircle}
                position="absolute"
                top={2}
                right={2}
                color="orange.500"
                boxSize={5}
              />
            )}
            <VStack spacing={3}>
              <Icon as={FiLink} boxSize={8} color="brand.500" />
              <Text fontWeight="bold">Plaid</Text>
              <Text fontSize="sm" color="text.secondary" textAlign="center">
                11,000+ institutions. Comprehensive support.
              </Text>
              {!plaidEnabled && (
                <Badge colorScheme="orange" fontSize="xs">
                  Not Configured
                </Badge>
              )}
            </VStack>
          </Box>
        </Tooltip>

        {/* Teller */}
        <Tooltip
          label={!tellerEnabled ? "Teller credentials not configured" : ""}
          placement="top"
          hasArrow
        >
          <Box
            as="button"
            onClick={tellerEnabled ? () => onSelectSource('teller') : undefined}
            p={6}
            borderWidth={2}
            borderRadius="lg"
            borderColor="border.default"
            _hover={tellerEnabled ? {
              borderColor: 'green.500',
              bg: 'bg.success',
              transform: 'translateY(-2px)',
              shadow: 'md',
            } : {}}
            transition="all 0.2s"
            cursor={tellerEnabled ? 'pointer' : 'not-allowed'}
            opacity={tellerEnabled ? 1 : 0.5}
            position="relative"
          >
            {tellerEnabled ? (
              <Badge
                position="absolute"
                top={2}
                right={2}
                colorScheme="green"
                fontSize="xs"
              >
                100 FREE
              </Badge>
            ) : (
              <Icon
                as={FiAlertCircle}
                position="absolute"
                top={2}
                right={2}
                color="orange.500"
                boxSize={5}
              />
            )}
            <VStack spacing={3}>
              <Icon as={FiDollarSign} boxSize={8} color="green.500" />
              <Text fontWeight="bold">Teller</Text>
              <Text fontSize="sm" color="text.secondary" textAlign="center">
                100 free accounts/month. Simple & affordable.
              </Text>
              {!tellerEnabled && (
                <Badge colorScheme="orange" fontSize="xs">
                  Not Configured
                </Badge>
              )}
            </VStack>
          </Box>
        </Tooltip>

        {/* MX */}
        <Tooltip
          label={!mxEnabled ? "MX integration coming soon" : ""}
          placement="top"
          hasArrow
        >
          <Box
            as="button"
            onClick={mxEnabled ? () => onSelectSource('mx') : undefined}
            p={6}
            borderWidth={2}
            borderRadius="lg"
            borderColor="border.default"
            transition="all 0.2s"
            cursor="not-allowed"
            opacity={0.5}
            position="relative"
          >
            <Icon
              as={FiAlertCircle}
              position="absolute"
              top={2}
              right={2}
              color="text.muted"
              boxSize={5}
            />
            <VStack spacing={3}>
              <Icon as={FiLink} boxSize={8} color="brand.500" />
              <Text fontWeight="bold">MX</Text>
              <Text fontSize="sm" color="text.secondary" textAlign="center">
                Alternative provider
              </Text>
              <Badge colorScheme="gray" fontSize="xs">
                Coming Soon
              </Badge>
            </VStack>
          </Box>
        </Tooltip>

        {/* Manual */}
        <Box
          as="button"
          onClick={() => onSelectSource('manual')}
          p={6}
          borderWidth={2}
          borderRadius="lg"
          borderColor="border.default"
          _hover={{
            borderColor: 'brand.500',
            bg: 'brand.subtle',
            transform: 'translateY(-2px)',
            shadow: 'md',
          }}
          transition="all 0.2s"
          cursor="pointer"
        >
          <VStack spacing={3}>
            <Icon as={FiEdit3} boxSize={8} color="brand.500" />
            <Text fontWeight="bold">Manual</Text>
            <Text fontSize="sm" color="text.secondary" textAlign="center">
              Enter account details yourself
            </Text>
          </VStack>
        </Box>
      </SimpleGrid>
    </VStack>
  );
};
