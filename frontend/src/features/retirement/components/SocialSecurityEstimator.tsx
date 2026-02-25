/**
 * Social Security benefit estimator card.
 * Shows monthly benefit at different claiming ages with a slider.
 */

import {
  Box,
  FormControl,
  FormLabel,
  HStack,
  NumberInput,
  NumberInputField,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Spinner,
  Stat,
  StatGroup,
  StatLabel,
  StatNumber,
  Switch,
  Text,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useState } from 'react';
import { useSocialSecurityEstimate } from '../hooks/useRetirementScenarios';

interface SocialSecurityEstimatorProps {
  currentIncome?: number | null;
  claimingAge: number;
  manualOverride?: number | null;
  onClaimingAgeChange?: (age: number) => void;
  onManualOverrideChange?: (amount: number | null) => void;
  readOnly?: boolean;
}

export function SocialSecurityEstimator({
  currentIncome,
  claimingAge,
  manualOverride,
  onClaimingAgeChange,
  onManualOverrideChange,
  readOnly,
}: SocialSecurityEstimatorProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const labelColor = useColorModeValue('gray.500', 'gray.400');
  const [localClaimingAge, setLocalClaimingAge] = useState(claimingAge);
  const [useManual, setUseManual] = useState(!!manualOverride);
  const [manualAmount, setManualAmount] = useState(manualOverride ?? 2000);

  const { data: estimate, isLoading } = useSocialSecurityEstimate(
    localClaimingAge,
    currentIncome ?? undefined
  );

  const handleClaimingAgeEnd = useCallback(
    (val: number) => {
      setLocalClaimingAge(val);
      onClaimingAgeChange?.(val);
    },
    [onClaimingAgeChange]
  );

  const handleManualToggle = useCallback(
    (checked: boolean) => {
      setUseManual(checked);
      if (checked) {
        onManualOverrideChange?.(manualAmount);
      } else {
        onManualOverrideChange?.(null);
      }
    },
    [manualAmount, onManualOverrideChange]
  );

  const handleManualAmountChange = useCallback(
    (_: string, val: number) => {
      if (!isNaN(val)) {
        setManualAmount(val);
        onManualOverrideChange?.(val);
      }
    },
    [onManualOverrideChange]
  );

  const formatMoney = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);

  return (
    <Box bg={bgColor} p={5} borderRadius="xl" shadow="sm">
      <VStack spacing={4} align="stretch">
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="semibold">
            Social Security
          </Text>
          {isLoading && <Spinner size="sm" />}
        </HStack>

        {/* Claiming age slider */}
        <FormControl>
          <HStack justify="space-between">
            <FormLabel fontSize="sm" mb={0} color={labelColor}>
              Claiming Age
            </FormLabel>
            <Text fontSize="sm" fontWeight="bold">
              {localClaimingAge}
            </Text>
          </HStack>
          <Slider
            value={localClaimingAge}
            min={62}
            max={70}
            step={1}
            onChange={setLocalClaimingAge}
            onChangeEnd={handleClaimingAgeEnd}
            isDisabled={readOnly}
          >
            <SliderTrack>
              <SliderFilledTrack bg="purple.400" />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </FormControl>

        {/* Manual override toggle */}
        <FormControl display="flex" alignItems="center">
          <FormLabel fontSize="xs" mb={0} color={labelColor}>
            Manual Override
          </FormLabel>
          <Switch
            size="sm"
            isChecked={useManual}
            onChange={(e) => handleManualToggle(e.target.checked)}
            isDisabled={readOnly}
          />
        </FormControl>

        {/* Manual override input */}
        {useManual && (
          <FormControl>
            <FormLabel fontSize="xs" color={labelColor}>
              Monthly SS Benefit ($)
            </FormLabel>
            <NumberInput
              value={manualAmount}
              min={0}
              max={10000}
              step={100}
              onChange={handleManualAmountChange}
              size="sm"
            >
              <NumberInputField />
            </NumberInput>
            <Text fontSize="xs" color={labelColor} mt={1}>
              {formatMoney(manualAmount * 12)}/year
            </Text>
          </FormControl>
        )}

        {/* Benefit estimates (only when not in manual mode) */}
        {!useManual && estimate && (
          <>
            <StatGroup>
              <Stat size="sm">
                <StatLabel fontSize="xs" color={labelColor}>
                  At 62
                </StatLabel>
                <StatNumber fontSize="sm">{formatMoney(estimate.monthly_at_62)}/mo</StatNumber>
              </Stat>
              <Stat size="sm">
                <StatLabel fontSize="xs" color={labelColor}>
                  At FRA ({estimate.fra_age})
                </StatLabel>
                <StatNumber fontSize="sm">{formatMoney(estimate.monthly_at_fra)}/mo</StatNumber>
              </Stat>
              <Stat size="sm">
                <StatLabel fontSize="xs" color={labelColor}>
                  At 70
                </StatLabel>
                <StatNumber fontSize="sm">{formatMoney(estimate.monthly_at_70)}/mo</StatNumber>
              </Stat>
            </StatGroup>

            <Box
              bg={useColorModeValue('blue.50', 'blue.900')}
              p={3}
              borderRadius="md"
            >
              <HStack justify="space-between">
                <Text fontSize="sm" color={labelColor}>
                  Your Benefit at {localClaimingAge}
                </Text>
                <Text fontSize="md" fontWeight="bold" color="blue.500">
                  {formatMoney(estimate.monthly_benefit)}/mo
                </Text>
              </HStack>
              <Text fontSize="xs" color={labelColor}>
                ({formatMoney(estimate.monthly_benefit * 12)}/year)
              </Text>
            </Box>

            <Text fontSize="xs" color={labelColor}>
              PIA (Primary Insurance Amount): {formatMoney(estimate.estimated_pia)}/mo
            </Text>
          </>
        )}

        {/* Manual mode summary */}
        {useManual && (
          <Box
            bg={useColorModeValue('purple.50', 'purple.900')}
            p={3}
            borderRadius="md"
          >
            <HStack justify="space-between">
              <Text fontSize="sm" color={labelColor}>
                Manual Benefit at {localClaimingAge}
              </Text>
              <Text fontSize="md" fontWeight="bold" color="purple.500">
                {formatMoney(manualAmount)}/mo
              </Text>
            </HStack>
            <Text fontSize="xs" color={labelColor}>
              ({formatMoney(manualAmount * 12)}/year)
            </Text>
          </Box>
        )}
      </VStack>
    </Box>
  );
}
