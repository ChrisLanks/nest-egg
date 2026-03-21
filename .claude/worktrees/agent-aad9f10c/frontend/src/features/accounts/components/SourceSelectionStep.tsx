/**
 * Source selection step for adding accounts
 */

import { useState } from "react";
import {
  VStack,
  HStack,
  Text,
  SimpleGrid,
  Box,
  Icon,
  Badge,
  Spinner,
  Tooltip,
  Switch,
  FormControl,
  FormLabel,
  Button,
  Heading,
} from "@chakra-ui/react";
import { FiLink, FiEdit3, FiDollarSign, FiAlertCircle } from "react-icons/fi";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../services/api";

export type AccountSource = "plaid" | "teller" | "mx" | "manual";

interface ProviderAvailability {
  plaid: boolean;
  teller: boolean;
  mx: boolean;
}

interface SourceSelectionStepProps {
  onSelectSource: (source: AccountSource) => void;
  /** @deprecated No longer used — auto-select is now controlled by the in-UI toggle */
  skipAutoSelect?: boolean;
}

const AUTO_PROVIDER_KEY = "nest-egg-auto-provider";

function readAutoMode(): boolean {
  try {
    const stored = localStorage.getItem(AUTO_PROVIDER_KEY);
    if (stored === null) return true; // default ON
    return stored === "true";
  } catch {
    return true;
  }
}

function writeAutoMode(value: boolean): void {
  try {
    localStorage.setItem(AUTO_PROVIDER_KEY, String(value));
  } catch {
    // ignore storage errors
  }
}

function getBestProvider(
  availability: ProviderAvailability,
): AccountSource | null {
  if (availability.plaid) return "plaid";
  if (availability.teller) return "teller";
  if (availability.mx) return "mx";
  return null;
}

const PROVIDER_INFO: Record<
  string,
  { label: string; reason: string; color: string; icon: React.ElementType }
> = {
  plaid: {
    label: "Plaid",
    reason: "Best coverage — 11,000+ institutions",
    color: "brand.500",
    icon: FiLink,
  },
  teller: {
    label: "Teller",
    reason: "100 free accounts/month — simple & affordable",
    color: "green.500",
    icon: FiDollarSign,
  },
  mx: {
    label: "MX",
    reason: "Enterprise aggregation — 16,000+ institutions",
    color: "purple.500",
    icon: FiLink,
  },
};

export const SourceSelectionStep = ({
  onSelectSource,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  skipAutoSelect: _skipAutoSelect,
}: SourceSelectionStepProps) => {
  const [autoMode, setAutoMode] = useState<boolean>(readAutoMode);

  const { data: availability, isLoading } = useQuery<ProviderAvailability>({
    queryKey: ["provider-availability"],
    queryFn: async () => {
      const response = await api.get("/accounts/providers/availability");
      return response.data;
    },
  });

  const handleToggleAutoMode = (value: boolean) => {
    setAutoMode(value);
    writeAutoMode(value);
  };

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

  const autoProvider = availability ? getBestProvider(availability) : null;

  return (
    <VStack spacing={6} align="stretch">
      {/* Auto-select toggle */}
      <FormControl display="flex" alignItems="center">
        <HStack justify="space-between" align="center" w="full">
          <VStack align="start" spacing={0}>
            <FormLabel
              htmlFor="auto-provider-toggle"
              mb={0}
              fontWeight="medium"
            >
              Auto-select provider
            </FormLabel>
            <Text fontSize="xs" color="text.secondary">
              Let Nest Egg choose the best available connection
            </Text>
          </VStack>
          <Switch
            id="auto-provider-toggle"
            isChecked={autoMode}
            onChange={(e) => handleToggleAutoMode(e.target.checked)}
            colorScheme="brand"
          />
        </HStack>
      </FormControl>

      {autoMode ? (
        autoProvider ? (
          /* Auto mode — provider found */
          <Box
            p={6}
            borderWidth={2}
            borderColor="brand.500"
            borderRadius="lg"
            bg="brand.subtle"
          >
            <VStack spacing={3} align="center">
              <Badge colorScheme="green" fontSize="sm" px={3} py={1}>
                Auto-selected
              </Badge>
              <Icon
                as={PROVIDER_INFO[autoProvider].icon}
                boxSize={10}
                color={PROVIDER_INFO[autoProvider].color}
              />
              <Heading size="md">{PROVIDER_INFO[autoProvider].label}</Heading>
              <Text color="text.secondary" textAlign="center">
                {PROVIDER_INFO[autoProvider].reason}
              </Text>
              <Button
                colorScheme="brand"
                onClick={() => onSelectSource(autoProvider)}
                mt={1}
              >
                Connect with {PROVIDER_INFO[autoProvider].label}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleToggleAutoMode(false)}
              >
                Choose a different provider
              </Button>
            </VStack>
          </Box>
        ) : (
          /* Auto mode — no providers configured */
          <Box p={6} borderRadius="lg" bg="bg.subtle" textAlign="center">
            <Text color="text.secondary" mb={3}>
              No bank providers are configured.
            </Text>
            <Button
              colorScheme="brand"
              onClick={() => onSelectSource("manual")}
            >
              Add account manually
            </Button>
          </Box>
        )
      ) : (
        /* Manual mode — existing 4-card grid */
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
          {/* Plaid */}
          <Tooltip
            label={!plaidEnabled ? "Plaid credentials not configured" : ""}
            placement="top"
            hasArrow
          >
            <Box
              as="button"
              onClick={plaidEnabled ? () => onSelectSource("plaid") : undefined}
              p={6}
              borderWidth={2}
              borderRadius="lg"
              borderColor="border.default"
              _hover={
                plaidEnabled
                  ? {
                      borderColor: "brand.500",
                      bg: "brand.subtle",
                      transform: "translateY(-2px)",
                      shadow: "md",
                    }
                  : {}
              }
              transition="all 0.2s"
              cursor={plaidEnabled ? "pointer" : "not-allowed"}
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
              onClick={
                tellerEnabled ? () => onSelectSource("teller") : undefined
              }
              p={6}
              borderWidth={2}
              borderRadius="lg"
              borderColor="border.default"
              _hover={
                tellerEnabled
                  ? {
                      borderColor: "green.500",
                      bg: "bg.success",
                      transform: "translateY(-2px)",
                      shadow: "md",
                    }
                  : {}
              }
              transition="all 0.2s"
              cursor={tellerEnabled ? "pointer" : "not-allowed"}
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
            label={!mxEnabled ? "MX credentials not configured" : ""}
            placement="top"
            hasArrow
          >
            <Box
              as="button"
              onClick={mxEnabled ? () => onSelectSource("mx") : undefined}
              p={6}
              borderWidth={2}
              borderRadius="lg"
              borderColor="border.default"
              _hover={
                mxEnabled
                  ? {
                      borderColor: "purple.500",
                      bg: "purple.50",
                      transform: "translateY(-2px)",
                      shadow: "md",
                    }
                  : {}
              }
              transition="all 0.2s"
              cursor={mxEnabled ? "pointer" : "not-allowed"}
              opacity={mxEnabled ? 1 : 0.5}
              position="relative"
            >
              {!mxEnabled && (
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
                <Icon as={FiLink} boxSize={8} color="purple.500" />
                <Text fontWeight="bold">MX</Text>
                <Text fontSize="sm" color="text.secondary" textAlign="center">
                  Enterprise aggregation. 16,000+ institutions.
                </Text>
                {!mxEnabled && (
                  <Badge colorScheme="orange" fontSize="xs">
                    Not Configured
                  </Badge>
                )}
              </VStack>
            </Box>
          </Tooltip>

          {/* Manual */}
          <Box
            as="button"
            onClick={() => onSelectSource("manual")}
            p={6}
            borderWidth={2}
            borderRadius="lg"
            borderColor="border.default"
            _hover={{
              borderColor: "brand.500",
              bg: "brand.subtle",
              transform: "translateY(-2px)",
              shadow: "md",
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
      )}
    </VStack>
  );
};
