/**
 * Scenario configuration panel with sliders and inputs.
 */

import {
  Box,
  Button,
  CloseButton,
  FormControl,
  FormLabel,
  HStack,
  NumberInput,
  NumberInputField,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Switch,
  Text,
  Tooltip,
  VStack,
  useColorModeValue,
} from "@chakra-ui/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { RetirementScenario, SpendingPhase } from "../types/retirement";

interface ScenarioPanelProps {
  scenario: RetirementScenario | null;
  onUpdate: (updates: Partial<RetirementScenario>) => void;
  readOnly?: boolean;
}

export function ScenarioPanel({
  scenario,
  onUpdate,
  readOnly,
}: ScenarioPanelProps) {
  const bgColor = useColorModeValue("white", "gray.800");
  const labelColor = useColorModeValue("gray.600", "gray.400");

  // Local state for sliders (debounced updates)
  const [retirementAge, setRetirementAge] = useState(
    scenario?.retirement_age ?? 67,
  );
  const [annualSpending, setAnnualSpending] = useState(
    scenario?.annual_spending_retirement ?? 60000,
  );
  const [preReturn, setPreReturn] = useState(
    scenario?.pre_retirement_return ?? 7,
  );
  const [postReturn, setPostReturn] = useState(
    scenario?.post_retirement_return ?? 5,
  );
  const [volatility, setVolatility] = useState(scenario?.volatility ?? 15);
  const [inflationRate, setInflationRate] = useState(
    scenario?.inflation_rate ?? 3,
  );
  const [lifeExpectancy, setLifeExpectancy] = useState(
    scenario?.life_expectancy ?? 95,
  );

  // Spending phases state
  const [usePhasedSpending, setUsePhasedSpending] = useState(false);
  const [phases, setPhases] = useState<SpendingPhase[]>([]);

  // Sync local state when scenario changes
  /* eslint-disable react-hooks/set-state-in-effect -- intentional sync from prop to local state */
  useEffect(() => {
    if (scenario) {
      setRetirementAge(scenario.retirement_age);
      setAnnualSpending(scenario.annual_spending_retirement);
      setPreReturn(scenario.pre_retirement_return);
      setPostReturn(scenario.post_retirement_return);
      setVolatility(scenario.volatility);
      setInflationRate(scenario.inflation_rate);
      setLifeExpectancy(scenario.life_expectancy);

      // Sync spending phases
      if (scenario.spending_phases && scenario.spending_phases.length > 0) {
        setUsePhasedSpending(true);
        setPhases(scenario.spending_phases);
      } else {
        setUsePhasedSpending(false);
        setPhases([]);
      }
    }
  }, [scenario?.id]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleSliderChange = useCallback(
    (field: string, value: number) => {
      onUpdate({ [field]: value });
    },
    [onUpdate],
  );

  // --- Spending phases handlers ---

  // Commit phases to server (used by discrete actions and on blur)
  const commitPhases = useCallback(
    (newPhases: SpendingPhase[] | null) => {
      onUpdate({ spending_phases: newPhases } as Partial<RetirementScenario>);
    },
    [onUpdate],
  );

  const handleTogglePhases = useCallback(
    (enabled: boolean) => {
      setUsePhasedSpending(enabled);
      if (enabled) {
        const initial: SpendingPhase[] = [
          {
            start_age: retirementAge,
            end_age: null,
            annual_amount: annualSpending,
          },
        ];
        setPhases(initial);
        commitPhases(initial);
      } else {
        setPhases([]);
        commitPhases(null);
      }
    },
    [retirementAge, annualSpending, commitPhases],
  );

  // Local-only change (no server call) — committed on blur
  const handlePhaseChange = useCallback(
    (index: number, field: keyof SpendingPhase, value: number | null) => {
      setPhases((prev) =>
        prev.map((p, i) => (i === index ? { ...p, [field]: value } : p)),
      );
    },
    [],
  );

  // Called on blur from phase inputs to commit to server
  const handlePhaseBlur = useCallback(() => {
    commitPhases(phases);
  }, [phases, commitPhases]);

  const handleAddPhase = useCallback(() => {
    setPhases((prev) => {
      const lastPhase = prev[prev.length - 1];
      const newStart =
        lastPhase?.end_age ?? lastPhase?.start_age ?? retirementAge;
      const updated = prev.map((p, i) =>
        i === prev.length - 1 && p.end_age === null
          ? { ...p, end_age: newStart + 5 }
          : p,
      );
      const newPhase: SpendingPhase = {
        start_age: updated[updated.length - 1]?.end_age ?? newStart,
        end_age: null,
        annual_amount: lastPhase?.annual_amount ?? annualSpending,
      };
      const result = [...updated, newPhase];
      commitPhases(result);
      return result;
    });
  }, [retirementAge, annualSpending, commitPhases]);

  const handleRemovePhase = useCallback(
    (index: number) => {
      setPhases((prev) => {
        const updated = prev.filter((_, i) => i !== index);
        if (updated.length > 0) {
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            end_age: null,
          };
        }
        if (updated.length === 0) {
          setUsePhasedSpending(false);
          commitPhases(null);
        } else {
          commitPhases(updated);
        }
        return updated;
      });
    },
    [commitPhases],
  );

  // Validation warnings
  const phaseWarnings = useMemo(() => {
    if (!usePhasedSpending || phases.length === 0) return [];
    const warnings: string[] = [];
    if (phases[0]?.start_age !== retirementAge) {
      warnings.push(
        `First phase starts at ${phases[0]?.start_age}, not retirement age ${retirementAge}`,
      );
    }
    for (let i = 0; i < phases.length - 1; i++) {
      if (phases[i].end_age !== phases[i + 1].start_age) {
        warnings.push(`Gap or overlap between phases ${i + 1} and ${i + 2}`);
      }
    }
    return warnings;
  }, [phases, retirementAge, usePhasedSpending]);

  if (!scenario) {
    return (
      <Box bg={bgColor} p={6} borderRadius="xl" shadow="sm">
        <Text color={labelColor}>
          Select or create a scenario to configure.
        </Text>
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
            <Tooltip label="The age you plan to stop working and begin withdrawing from your portfolio">
              <FormLabel fontSize="sm" mb={0} color={labelColor} cursor="help">
                Retirement Age
              </FormLabel>
            </Tooltip>
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
            onChangeEnd={(v) => handleSliderChange("retirement_age", v)}
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
            <Tooltip label="How long to model your finances — plan conservatively to avoid outliving your money">
              <FormLabel fontSize="sm" mb={0} color={labelColor} cursor="help">
                Plan Through Age
              </FormLabel>
            </Tooltip>
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
            onChangeEnd={(v) => handleSliderChange("life_expectancy", v)}
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
          <HStack justify="space-between">
            <Tooltip label="How much you expect to spend per year after retiring, before taxes">
              <FormLabel fontSize="sm" color={labelColor} mb={0} cursor="help">
                Annual Spending in Retirement
              </FormLabel>
            </Tooltip>
            <HStack spacing={2}>
              <Tooltip label="Model different spending levels at different ages (e.g., travel more early, spend less later)">
                <Text fontSize="xs" color={labelColor} cursor="help">
                  Use phases
                </Text>
              </Tooltip>
              <Switch
                size="sm"
                isChecked={usePhasedSpending}
                onChange={(e) => handleTogglePhases(e.target.checked)}
                isDisabled={readOnly}
              />
            </HStack>
          </HStack>

          {!usePhasedSpending && (
            <NumberInput
              value={annualSpending}
              min={10000}
              max={500000}
              step={1000}
              onChange={(_, val) => {
                if (!isNaN(val)) {
                  setAnnualSpending(val);
                  handleSliderChange("annual_spending_retirement", val);
                }
              }}
              size="sm"
              isDisabled={readOnly}
              mt={1}
            >
              <NumberInputField />
            </NumberInput>
          )}

          {usePhasedSpending && (
            <VStack spacing={2} align="stretch" mt={2}>
              {phases.map((phase, idx) => (
                <HStack key={idx} spacing={2} align="end">
                  <FormControl size="sm" flex={1}>
                    {idx === 0 && (
                      <FormLabel fontSize="xs" color={labelColor}>
                        From
                      </FormLabel>
                    )}
                    <NumberInput
                      value={phase.start_age}
                      min={15}
                      max={120}
                      size="xs"
                      onChange={(_, val) => {
                        if (!isNaN(val))
                          handlePhaseChange(idx, "start_age", val);
                      }}
                      isDisabled={readOnly}
                    >
                      <NumberInputField px={2} onBlur={handlePhaseBlur} />
                    </NumberInput>
                  </FormControl>
                  <FormControl size="sm" flex={1}>
                    {idx === 0 && (
                      <FormLabel fontSize="xs" color={labelColor}>
                        To
                      </FormLabel>
                    )}
                    {phase.end_age !== null ? (
                      <NumberInput
                        value={phase.end_age}
                        min={phase.start_age + 1}
                        max={120}
                        size="xs"
                        onChange={(_, val) => {
                          if (!isNaN(val))
                            handlePhaseChange(idx, "end_age", val);
                        }}
                        isDisabled={readOnly}
                      >
                        <NumberInputField px={2} onBlur={handlePhaseBlur} />
                      </NumberInput>
                    ) : (
                      <Text fontSize="xs" color={labelColor} py={1}>
                        End
                      </Text>
                    )}
                  </FormControl>
                  <FormControl size="sm" flex={2}>
                    {idx === 0 && (
                      <FormLabel fontSize="xs" color={labelColor}>
                        $/year
                      </FormLabel>
                    )}
                    <NumberInput
                      value={phase.annual_amount}
                      min={1000}
                      max={1000000}
                      step={1000}
                      size="xs"
                      onChange={(_, val) => {
                        if (!isNaN(val))
                          handlePhaseChange(idx, "annual_amount", val);
                      }}
                      isDisabled={readOnly}
                    >
                      <NumberInputField px={2} onBlur={handlePhaseBlur} />
                    </NumberInput>
                  </FormControl>
                  {phases.length > 1 && !readOnly && (
                    <CloseButton
                      size="sm"
                      onClick={() => handleRemovePhase(idx)}
                    />
                  )}
                </HStack>
              ))}
              {!readOnly && (
                <Button size="xs" variant="ghost" onClick={handleAddPhase}>
                  + Add Phase
                </Button>
              )}
              {phaseWarnings.map((w, i) => (
                <Text key={i} fontSize="xs" color="orange.500">
                  {w}
                </Text>
              ))}
            </VStack>
          )}
        </FormControl>

        {/* Return Assumptions */}
        <Text fontSize="sm" fontWeight="semibold" color={labelColor} pt={2}>
          Return Assumptions
        </Text>

        <FormControl>
          <HStack justify="space-between">
            <Tooltip label="Expected average annual return on investments before you retire (S&P 500 averages ~10%)">
              <FormLabel fontSize="sm" mb={0} color={labelColor} cursor="help">
                Pre-Retirement Return
              </FormLabel>
            </Tooltip>
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
            onChangeEnd={(v) => handleSliderChange("pre_retirement_return", v)}
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
            <Tooltip label="Expected average annual return after retiring — typically lower due to more conservative investments">
              <FormLabel fontSize="sm" mb={0} color={labelColor} cursor="help">
                Post-Retirement Return
              </FormLabel>
            </Tooltip>
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
            onChangeEnd={(v) => handleSliderChange("post_retirement_return", v)}
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
            <Tooltip label="How much returns swing year to year — higher means more uncertainty in outcomes">
              <FormLabel fontSize="sm" mb={0} color={labelColor} cursor="help">
                Volatility
              </FormLabel>
            </Tooltip>
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
            onChangeEnd={(v) => handleSliderChange("volatility", v)}
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
            <Tooltip label="How fast prices rise each year — your spending needs grow by this rate over time">
              <FormLabel fontSize="sm" mb={0} color={labelColor} cursor="help">
                Inflation Rate
              </FormLabel>
            </Tooltip>
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
            onChangeEnd={(v) => handleSliderChange("inflation_rate", v)}
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
