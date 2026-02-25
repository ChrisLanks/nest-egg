/**
 * Healthcare cost estimator card.
 * Shows cost phases: pre-65 insurance, Medicare at 65, IRMAA, LTC at 85+.
 * Pencil icon to toggle edit mode for medical inflation rate, retirement income,
 * and individual cost line overrides.
 */

import {
  Box,
  FormControl,
  FormLabel,
  HStack,
  IconButton,
  NumberInput,
  NumberInputField,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Spinner,
  Text,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FiCheck, FiEdit2 } from 'react-icons/fi';
import { useHealthcareEstimate } from '../hooks/useRetirementScenarios';

interface HealthcareEstimatorProps {
  retirementIncome?: number;
  medicalInflationRate?: number;
  onMedicalInflationChange?: (rate: number) => void;
  onRetirementIncomeChange?: (income: number) => void;
  /** Current override values from scenario (null = use estimate) */
  pre65Override?: number | null;
  medicareOverride?: number | null;
  ltcOverride?: number | null;
  /** Callback to persist overrides */
  onHealthcareOverridesChange?: (overrides: {
    healthcare_pre65_override?: number | null;
    healthcare_medicare_override?: number | null;
    healthcare_ltc_override?: number | null;
  }) => void;
}

export function HealthcareEstimator({
  retirementIncome = 50000,
  medicalInflationRate = 6.0,
  onMedicalInflationChange,
  onRetirementIncomeChange,
  pre65Override,
  medicareOverride,
  ltcOverride,
  onHealthcareOverridesChange,
}: HealthcareEstimatorProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const labelColor = useColorModeValue('gray.500', 'gray.400');
  const editBg = useColorModeValue('gray.50', 'gray.700');
  const [isEditing, setIsEditing] = useState(false);
  const [localInflation, setLocalInflation] = useState(medicalInflationRate);
  const [localIncome, setLocalIncome] = useState(retirementIncome);
  const [localPre65, setLocalPre65] = useState<number | null>(pre65Override ?? null);
  const [localMedicare, setLocalMedicare] = useState<number | null>(medicareOverride ?? null);
  const [localLtc, setLocalLtc] = useState<number | null>(ltcOverride ?? null);

  // Optimistic display: retain saved values until props catch up from the PATCH response
  const [savedOverrides, setSavedOverrides] = useState<{
    pre65: number | null;
    medicare: number | null;
    ltc: number | null;
  } | null>(null);

  // Clear optimistic state when override props actually change (PATCH response arrived)
  const prevOverrideProps = useRef({ pre65: pre65Override, medicare: medicareOverride, ltc: ltcOverride });
  useEffect(() => {
    const prev = prevOverrideProps.current;
    if (prev.pre65 !== pre65Override || prev.medicare !== medicareOverride || prev.ltc !== ltcOverride) {
      setSavedOverrides(null);
    }
    prevOverrideProps.current = { pre65: pre65Override, medicare: medicareOverride, ltc: ltcOverride };
  }, [pre65Override, medicareOverride, ltcOverride]);

  const { data: estimate, isLoading } = useHealthcareEstimate(
    retirementIncome,
    medicalInflationRate
  );

  const handleToggleEdit = useCallback(() => {
    if (isEditing) {
      // Save changes
      if (localInflation !== medicalInflationRate) {
        onMedicalInflationChange?.(localInflation);
      }
      if (localIncome !== retirementIncome) {
        onRetirementIncomeChange?.(localIncome);
      }
      // Save cost overrides
      const overrides: {
        healthcare_pre65_override?: number | null;
        healthcare_medicare_override?: number | null;
        healthcare_ltc_override?: number | null;
      } = {};
      if (localPre65 !== (pre65Override ?? null)) overrides.healthcare_pre65_override = localPre65;
      if (localMedicare !== (medicareOverride ?? null)) overrides.healthcare_medicare_override = localMedicare;
      if (localLtc !== (ltcOverride ?? null)) overrides.healthcare_ltc_override = localLtc;
      if (Object.keys(overrides).length > 0) onHealthcareOverridesChange?.(overrides);
      // Show saved values immediately without waiting for PATCH response
      setSavedOverrides({ pre65: localPre65, medicare: localMedicare, ltc: localLtc });
    } else {
      // Enter edit mode — sync local state
      setLocalInflation(medicalInflationRate);
      setLocalIncome(retirementIncome);
      setLocalPre65(pre65Override ?? (estimate?.pre_65_annual ?? null));
      setLocalMedicare(medicareOverride ?? (estimate?.medicare_annual ?? null));
      setLocalLtc(ltcOverride ?? (estimate?.ltc_annual ?? null));
    }
    setIsEditing(!isEditing);
  }, [
    isEditing, localInflation, localIncome, localPre65, localMedicare, localLtc,
    medicalInflationRate, retirementIncome, pre65Override, medicareOverride, ltcOverride,
    estimate, onMedicalInflationChange, onRetirementIncomeChange, onHealthcareOverridesChange,
  ]);

  const formatMoney = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);

  const phaseColor = (phase: string) => {
    switch (phase) {
      case 'pre65':
        return 'blue.400';
      case 'medicare':
        return 'green.400';
      case 'ltc':
        return 'red.400';
      default:
        return 'gray.400';
    }
  };

  // Effective overrides: prefer optimistic saved values > props (with Number() for Decimal string safety)
  const effectivePre65 = savedOverrides !== null ? savedOverrides.pre65 : (pre65Override != null ? Number(pre65Override) : null);
  const effectiveMedicare = savedOverrides !== null ? savedOverrides.medicare : (medicareOverride != null ? Number(medicareOverride) : null);
  const effectiveLtc = savedOverrides !== null ? savedOverrides.ltc : (ltcOverride != null ? Number(ltcOverride) : null);

  const displayPre65 = effectivePre65 ?? estimate?.pre_65_annual ?? 0;
  const displayMedicare = effectiveMedicare ?? estimate?.medicare_annual ?? 0;
  const displayLtc = effectiveLtc ?? estimate?.ltc_annual ?? 0;

  // Adjust sample ages when overrides are set
  const adjustedSampleAges = useMemo(() => {
    if (!estimate?.sample_ages?.length) return [];
    const hasAnyOverride = effectivePre65 != null || effectiveMedicare != null || effectiveLtc != null;
    if (!hasAnyOverride) return estimate.sample_ages;

    const pre65Scale =
      effectivePre65 != null && estimate.pre_65_annual > 0
        ? effectivePre65 / estimate.pre_65_annual
        : 1;
    const medicareScale =
      effectiveMedicare != null && estimate.medicare_annual > 0
        ? effectiveMedicare / estimate.medicare_annual
        : 1;
    const ltcScale =
      effectiveLtc != null && estimate.ltc_annual > 0
        ? effectiveLtc / estimate.ltc_annual
        : 1;

    return estimate.sample_ages.map((sample) => {
      let adjustedTotal = sample.total;
      if (sample.age < 65) {
        adjustedTotal = sample.total * pre65Scale;
      } else if (sample.age < 85) {
        adjustedTotal = sample.total * medicareScale;
      } else {
        // 85+: scale medicare and LTC portions separately
        const ltcPortion = sample.long_term_care || 0;
        const medicarePortion = sample.total - ltcPortion;
        adjustedTotal = medicarePortion * medicareScale + ltcPortion * ltcScale;
      }
      return { ...sample, total: adjustedTotal };
    });
  }, [estimate, effectivePre65, effectiveMedicare, effectiveLtc]);

  return (
    <Box bg={bgColor} p={5} borderRadius="xl" shadow="sm">
      <VStack spacing={4} align="stretch">
        <HStack justify="space-between">
          <Text fontSize="lg" fontWeight="semibold">
            Healthcare Costs
          </Text>
          <HStack spacing={2}>
            {isLoading && <Spinner size="sm" />}
            <IconButton
              aria-label={isEditing ? 'Save healthcare settings' : 'Edit healthcare settings'}
              icon={isEditing ? <FiCheck /> : <FiEdit2 />}
              size="xs"
              variant="ghost"
              onClick={handleToggleEdit}
            />
          </HStack>
        </HStack>

        {/* Edit mode: inflation slider + income input */}
        {isEditing && (
          <VStack spacing={3} align="stretch" p={3} bg={editBg} borderRadius="md">
            <FormControl>
              <HStack justify="space-between">
                <FormLabel fontSize="xs" mb={0} color={labelColor}>
                  Medical Inflation Rate
                </FormLabel>
                <Text fontSize="xs" fontWeight="bold">
                  {localInflation}%
                </Text>
              </HStack>
              <Slider
                value={localInflation}
                min={0}
                max={15}
                step={0.5}
                onChange={setLocalInflation}
              >
                <SliderTrack>
                  <SliderFilledTrack bg="red.400" />
                </SliderTrack>
                <SliderThumb />
              </Slider>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="xs" color={labelColor}>
                Retirement Income (for IRMAA)
              </FormLabel>
              <NumberInput
                value={localIncome}
                min={0}
                max={1000000}
                step={5000}
                onChange={(_, val) => { if (!isNaN(val)) setLocalIncome(val); }}
                size="sm"
              >
                <NumberInputField />
              </NumberInput>
            </FormControl>
          </VStack>
        )}

        {(estimate || isEditing) && (
          <>
            {/* Cost phases — editable when in edit mode */}
            <VStack spacing={2} align="stretch">
              {(displayPre65 > 0 || isEditing) && (
                <HStack justify="space-between">
                  <HStack spacing={2}>
                    <Box w={2} h={2} borderRadius="full" bg={phaseColor('pre65')} />
                    <Text fontSize="sm" color={labelColor}>
                      Pre-65 Insurance
                    </Text>
                  </HStack>
                  {isEditing ? (
                    <NumberInput
                      value={localPre65 ?? 0}
                      min={0}
                      max={100000}
                      step={100}
                      size="xs"
                      w="100px"
                      onChange={(_, val) => { if (!isNaN(val)) setLocalPre65(val || null); }}
                    >
                      <NumberInputField textAlign="right" />
                    </NumberInput>
                  ) : (
                    <Text fontSize="sm" fontWeight="medium">
                      {formatMoney(displayPre65)}/yr
                    </Text>
                  )}
                </HStack>
              )}

              <HStack justify="space-between">
                <HStack spacing={2}>
                  <Box w={2} h={2} borderRadius="full" bg={phaseColor('medicare')} />
                  <Text fontSize="sm" color={labelColor}>
                    Medicare (65+)
                  </Text>
                </HStack>
                {isEditing ? (
                  <NumberInput
                    value={localMedicare ?? 0}
                    min={0}
                    max={100000}
                    step={100}
                    size="xs"
                    w="100px"
                    onChange={(_, val) => { if (!isNaN(val)) setLocalMedicare(val || null); }}
                  >
                    <NumberInputField textAlign="right" />
                  </NumberInput>
                ) : (
                  <Text fontSize="sm" fontWeight="medium">
                    {formatMoney(displayMedicare)}/yr
                  </Text>
                )}
              </HStack>

              {(displayLtc > 0 || isEditing) && (
                <HStack justify="space-between">
                  <HStack spacing={2}>
                    <Box w={2} h={2} borderRadius="full" bg={phaseColor('ltc')} />
                    <Text fontSize="sm" color={labelColor}>
                      Long-Term Care (85+)
                    </Text>
                  </HStack>
                  {isEditing ? (
                    <NumberInput
                      value={localLtc ?? 0}
                      min={0}
                      max={200000}
                      step={100}
                      size="xs"
                      w="100px"
                      onChange={(_, val) => { if (!isNaN(val)) setLocalLtc(val || null); }}
                    >
                      <NumberInputField textAlign="right" />
                    </NumberInput>
                  ) : (
                    <Text fontSize="sm" fontWeight="medium">
                      {formatMoney(displayLtc)}/yr
                    </Text>
                  )}
                </HStack>
              )}
            </VStack>

            {/* Sample age breakdown (read-only), adjusted for overrides */}
            {!isEditing && adjustedSampleAges.length > 0 && (
              <Box>
                <Text fontSize="xs" fontWeight="semibold" color={labelColor} mb={2}>
                  Annual Cost by Age
                </Text>
                <VStack spacing={1} align="stretch">
                  {adjustedSampleAges
                    .filter((s) => s.total > 0)
                    .slice(0, 5)
                    .map((sample) => (
                      <HStack key={sample.age} justify="space-between" fontSize="xs">
                        <Text color={labelColor}>Age {sample.age}</Text>
                        <Text fontWeight="medium">{formatMoney(sample.total)}</Text>
                      </HStack>
                    ))}
                </VStack>
              </Box>
            )}

            <Text fontSize="xs" color={labelColor} pt={1}>
              Assumes {medicalInflationRate}% medical inflation.
              {(effectivePre65 != null || effectiveMedicare != null || effectiveLtc != null) &&
                ' Includes manual overrides.'}
              {' '}Costs are in today's dollars.
            </Text>
          </>
        )}
      </VStack>
    </Box>
  );
}
