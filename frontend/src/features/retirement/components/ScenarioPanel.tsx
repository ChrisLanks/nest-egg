/**
 * Scenario configuration panel with sliders and inputs.
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
  Text,
  VStack,
  useColorModeValue,
} from '@chakra-ui/react';
import { useCallback, useEffect, useState } from 'react';
import type { RetirementScenario } from '../types/retirement';

interface ScenarioPanelProps {
  scenario: RetirementScenario | null;
  onUpdate: (updates: Partial<RetirementScenario>) => void;
  readOnly?: boolean;
}

export function ScenarioPanel({ scenario, onUpdate, readOnly }: ScenarioPanelProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const labelColor = useColorModeValue('gray.600', 'gray.400');

  // Local state for sliders (debounced updates)
  const [retirementAge, setRetirementAge] = useState(scenario?.retirement_age ?? 67);
  const [annualSpending, setAnnualSpending] = useState(scenario?.annual_spending_retirement ?? 60000);
  const [preReturn, setPreReturn] = useState(scenario?.pre_retirement_return ?? 7);
  const [postReturn, setPostReturn] = useState(scenario?.post_retirement_return ?? 5);
  const [volatility, setVolatility] = useState(scenario?.volatility ?? 15);
  const [inflationRate, setInflationRate] = useState(scenario?.inflation_rate ?? 3);
  const [lifeExpectancy, setLifeExpectancy] = useState(scenario?.life_expectancy ?? 95);

  // Sync local state when scenario changes
  useEffect(() => {
    if (scenario) {
      setRetirementAge(scenario.retirement_age);
      setAnnualSpending(scenario.annual_spending_retirement);
      setPreReturn(scenario.pre_retirement_return);
      setPostReturn(scenario.post_retirement_return);
      setVolatility(scenario.volatility);
      setInflationRate(scenario.inflation_rate);
      setLifeExpectancy(scenario.life_expectancy);
    }
  }, [scenario?.id]);

  const handleSliderChange = useCallback(
    (field: string, value: number) => {
      onUpdate({ [field]: value });
    },
    [onUpdate]
  );

  if (!scenario) {
    return (
      <Box bg={bgColor} p={6} borderRadius="xl" shadow="sm">
        <Text color={labelColor}>Select or create a scenario to configure.</Text>
      </Box>
    );
  }

  return (
    <Box bg={bgColor} p={5} borderRadius="xl" shadow="sm">
      <VStack spacing={4} align="stretch">
        <Text fontSize="lg" fontWeight="semibold">
          Scenario Settings
        </Text>

        {/* Retirement Age */}
        <FormControl>
          <HStack justify="space-between">
            <FormLabel fontSize="sm" mb={0} color={labelColor}>
              Retirement Age
            </FormLabel>
            <Text fontSize="sm" fontWeight="bold">
              {retirementAge}
            </Text>
          </HStack>
          <Slider
            value={retirementAge}
            min={15}
            max={95}
            step={1}
            onChange={setRetirementAge}
            onChangeEnd={(v) => handleSliderChange('retirement_age', v)}
            isDisabled={readOnly}
          >
            <SliderTrack>
              <SliderFilledTrack bg="blue.400" />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </FormControl>

        {/* Life Expectancy */}
        <FormControl>
          <HStack justify="space-between">
            <FormLabel fontSize="sm" mb={0} color={labelColor}>
              Plan Through Age
            </FormLabel>
            <Text fontSize="sm" fontWeight="bold">
              {lifeExpectancy}
            </Text>
          </HStack>
          <Slider
            value={lifeExpectancy}
            min={15}
            max={110}
            step={1}
            onChange={setLifeExpectancy}
            onChangeEnd={(v) => handleSliderChange('life_expectancy', v)}
            isDisabled={readOnly}
          >
            <SliderTrack>
              <SliderFilledTrack bg="blue.400" />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </FormControl>

        {/* Annual Spending */}
        <FormControl>
          <FormLabel fontSize="sm" color={labelColor}>
            Annual Spending in Retirement
          </FormLabel>
          <NumberInput
            value={annualSpending}
            min={10000}
            max={500000}
            step={1000}
            onChange={(_, val) => {
              if (!isNaN(val)) {
                setAnnualSpending(val);
                handleSliderChange('annual_spending_retirement', val);
              }
            }}
            size="sm"
            isDisabled={readOnly}
          >
            <NumberInputField />
          </NumberInput>
        </FormControl>

        {/* Return Assumptions */}
        <Text fontSize="sm" fontWeight="semibold" color={labelColor} pt={2}>
          Return Assumptions
        </Text>

        <FormControl>
          <HStack justify="space-between">
            <FormLabel fontSize="sm" mb={0} color={labelColor}>
              Pre-Retirement Return
            </FormLabel>
            <Text fontSize="sm" fontWeight="bold">
              {preReturn}%
            </Text>
          </HStack>
          <Slider
            value={preReturn}
            min={0}
            max={15}
            step={0.5}
            onChange={setPreReturn}
            onChangeEnd={(v) => handleSliderChange('pre_retirement_return', v)}
            isDisabled={readOnly}
          >
            <SliderTrack>
              <SliderFilledTrack bg="green.400" />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </FormControl>

        <FormControl>
          <HStack justify="space-between">
            <FormLabel fontSize="sm" mb={0} color={labelColor}>
              Post-Retirement Return
            </FormLabel>
            <Text fontSize="sm" fontWeight="bold">
              {postReturn}%
            </Text>
          </HStack>
          <Slider
            value={postReturn}
            min={0}
            max={12}
            step={0.5}
            onChange={setPostReturn}
            onChangeEnd={(v) => handleSliderChange('post_retirement_return', v)}
            isDisabled={readOnly}
          >
            <SliderTrack>
              <SliderFilledTrack bg="green.400" />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </FormControl>

        <FormControl>
          <HStack justify="space-between">
            <FormLabel fontSize="sm" mb={0} color={labelColor}>
              Volatility
            </FormLabel>
            <Text fontSize="sm" fontWeight="bold">
              {volatility}%
            </Text>
          </HStack>
          <Slider
            value={volatility}
            min={0}
            max={40}
            step={1}
            onChange={setVolatility}
            onChangeEnd={(v) => handleSliderChange('volatility', v)}
            isDisabled={readOnly}
          >
            <SliderTrack>
              <SliderFilledTrack bg="orange.400" />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </FormControl>

        <FormControl>
          <HStack justify="space-between">
            <FormLabel fontSize="sm" mb={0} color={labelColor}>
              Inflation Rate
            </FormLabel>
            <Text fontSize="sm" fontWeight="bold">
              {inflationRate}%
            </Text>
          </HStack>
          <Slider
            value={inflationRate}
            min={0}
            max={10}
            step={0.5}
            onChange={setInflationRate}
            onChangeEnd={(v) => handleSliderChange('inflation_rate', v)}
            isDisabled={readOnly}
          >
            <SliderTrack>
              <SliderFilledTrack bg="red.400" />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </FormControl>

      </VStack>
    </Box>
  );
}
