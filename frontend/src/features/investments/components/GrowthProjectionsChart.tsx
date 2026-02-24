/**
 * Growth Projections Chart Component
 *
 * Uses Monte Carlo simulation to project portfolio growth with:
 * - Configurable return rate, volatility, and inflation
 * - Percentile bands showing range of outcomes
 * - Inflation-adjusted projections
 * - Retirement/withdrawal phase with success probability
 * - Scenario comparison (up to 3 overlaid scenarios)
 * - Stress-test presets (2008 Crisis, High Inflation, Lost Decade)
 */

import {
  Box,
  VStack,
  HStack,
  Text,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  FormControl,
  FormLabel,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Button,
  Switch,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Card,
  CardBody,
  Badge,
  IconButton,
  RadioGroup,
  Radio,
  Stack,
  Divider,
  Wrap,
  WrapItem,
  useColorModeValue,
} from '@chakra-ui/react';
import { CloseIcon, AddIcon } from '@chakra-ui/icons';
import { useState, useMemo, useCallback, useEffect } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import {
  runMonteCarloSimulation,
  STRESS_SCENARIOS,
  type SimulationParams,
  type SimulationSummary,
  type StressScenario,
} from '../../../utils/monteCarloSimulation';
import { ScenarioComparisonChart, type ScenarioData } from './ScenarioComparisonChart';

interface GrowthProjectionsChartProps {
  currentValue: number;
  monthlyContribution?: number;
}

interface ScenarioConfig {
  id: string;
  name: string;
  color: string;
  annualReturn: number;
  volatility: number;
  inflationRate: number;
  years: number;
  retirementYear?: number;
  annualWithdrawal?: number;
  withdrawalRate?: number;
  withdrawalStrategy: 'fixed' | 'percent';
  enableRetirement: boolean;
  stressOverrides?: StressScenario;
}

const SCENARIO_COLORS = ['#4299E1', '#ED8936', '#48BB78'];
let scenarioCounter = 0;

const makeDefaultScenario = (overrides?: Partial<ScenarioConfig>): ScenarioConfig => ({
  id: `scenario-${++scenarioCounter}`,
  name: 'Base Case',
  color: SCENARIO_COLORS[0],
  annualReturn: 7,
  volatility: 15,
  inflationRate: 3,
  years: 10,
  withdrawalStrategy: 'percent',
  enableRetirement: false,
  ...overrides,
});

export const GrowthProjectionsChart = ({ currentValue, monthlyContribution = 0 }: GrowthProjectionsChartProps) => {
  // Scenario management
  const [scenarios, setScenarios] = useState<ScenarioConfig[]>([makeDefaultScenario()]);
  const [activeScenarioIndex, setActiveScenarioIndex] = useState(0);
  const [showInflationAdjusted, setShowInflationAdjusted] = useState(true);
  // Local slider state so dragging doesn't recompute simulations per pixel
  const [sliderYears, setSliderYears] = useState(10);

  const activeScenario = scenarios[activeScenarioIndex] || scenarios[0];

  // Keep slider in sync when active scenario changes
  useEffect(() => {
    setSliderYears(activeScenario.years);
  }, [activeScenario.years]);

  // Dark mode colors
  const successBg = useColorModeValue('green.50', 'green.900');
  const successColor = useColorModeValue('green.700', 'green.200');
  const warningBg = useColorModeValue('orange.50', 'orange.900');
  const warningColor = useColorModeValue('orange.700', 'orange.200');
  const dangerBg = useColorModeValue('red.50', 'red.900');
  const dangerColor = useColorModeValue('red.700', 'red.200');
  const gridColor = useColorModeValue('#e0e0e0', '#4A5568');
  const scenarioCardBg = useColorModeValue('gray.50', 'gray.700');
  const stressBtnVariant = useColorModeValue('outline', 'solid');

  // Run all simulations
  const simulationResults: SimulationSummary[] = useMemo(() => {
    return scenarios.map((sc) => {
      const params: SimulationParams = {
        currentValue,
        years: sc.years,
        simulations: 1000,
        annualReturn: sc.annualReturn,
        volatility: sc.volatility,
        inflationRate: sc.inflationRate,
        monthlyContribution,
        stressOverrides: sc.stressOverrides,
      };
      if (sc.enableRetirement && sc.retirementYear != null) {
        params.retirementYear = sc.retirementYear;
        params.inflationAdjustWithdrawals = true;
        if (sc.withdrawalStrategy === 'fixed') {
          params.annualWithdrawal = sc.annualWithdrawal || 0;
        } else {
          params.withdrawalRate = sc.withdrawalRate || 4;
        }
      }
      return runMonteCarloSimulation(params);
    });
  }, [scenarios, currentValue, monthlyContribution]);

  const activeSummary = simulationResults[activeScenarioIndex] || simulationResults[0];
  const activeProjections = activeSummary.projections;

  // Summary stats for active scenario
  const summaryStats = useMemo(() => {
    const finalYear = activeProjections[activeProjections.length - 1];
    return {
      medianValue: finalYear.median,
      medianGain: finalYear.median - currentValue,
      medianGainPercent: ((finalYear.median - currentValue) / currentValue) * 100,
      pessimistic: finalYear.percentile10,
      optimistic: finalYear.percentile90,
      inflationAdjustedMedian: finalYear.medianInflationAdjusted,
      successRate: activeSummary.successRate,
      medianDepletionYear: activeSummary.medianDepletionYear,
    };
  }, [activeProjections, currentValue, activeSummary]);

  // Update active scenario field
  const updateField = useCallback(
    <K extends keyof ScenarioConfig>(field: K, value: ScenarioConfig[K]) => {
      setScenarios((prev) =>
        prev.map((s, i) => (i === activeScenarioIndex ? { ...s, [field]: value } : s))
      );
    },
    [activeScenarioIndex]
  );

  // Add scenario
  const addScenario = useCallback(
    (overrides?: Partial<ScenarioConfig>) => {
      if (scenarios.length >= 3) return;
      const idx = scenarios.length;
      const newSc = makeDefaultScenario({
        name: `Scenario ${idx + 1}`,
        color: SCENARIO_COLORS[idx],
        years: activeScenario.years,
        ...overrides,
      });
      setScenarios((prev) => [...prev, newSc]);
      setActiveScenarioIndex(idx);
    },
    [scenarios.length, activeScenario.years]
  );

  // Remove scenario
  const removeScenario = useCallback(
    (idx: number) => {
      if (scenarios.length <= 1) return;
      setScenarios((prev) => prev.filter((_, i) => i !== idx));
      setActiveScenarioIndex((prev) => (prev >= idx ? Math.max(0, prev - 1) : prev));
    },
    [scenarios.length]
  );

  // Apply stress preset as new scenario
  const applyStressPreset = useCallback(
    (key: string) => {
      const preset = STRESS_SCENARIOS[key];
      if (!preset) return;
      if (scenarios.length >= 3) {
        // Replace active scenario's stress overrides
        updateField('stressOverrides', preset);
        updateField('name', preset.name);
      } else {
        addScenario({
          name: preset.name,
          stressOverrides: preset,
        });
      }
    },
    [scenarios.length, addScenario, updateField]
  );

  // Reset active to defaults
  const handleReset = () => {
    const defaults = makeDefaultScenario({
      id: activeScenario.id,
      name: activeScenario.name,
      color: activeScenario.color,
    });
    setScenarios((prev) => prev.map((s, i) => (i === activeScenarioIndex ? defaults : s)));
  };

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);

  // Custom tooltip for single-scenario view
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <Card size="sm">
          <CardBody>
            <Text fontWeight="bold" mb={2}>
              Year {label}
            </Text>
            {payload.map((entry: any, index: number) => (
              <Text key={index} fontSize="sm" color={entry.color}>
                {entry.name}: {formatCurrency(entry.value)}
              </Text>
            ))}
          </CardBody>
        </Card>
      );
    }
    return null;
  };

  // Success rate badge color
  const getSuccessRateProps = (rate: number) => {
    if (rate >= 80) return { bg: successBg, color: successColor, label: 'High' };
    if (rate >= 50) return { bg: warningBg, color: warningColor, label: 'Moderate' };
    return { bg: dangerBg, color: dangerColor, label: 'Low' };
  };

  const showMultiScenario = scenarios.length > 1;

  // Build scenario data for comparison chart
  const scenarioChartData: ScenarioData[] = scenarios.map((sc, i) => ({
    name: sc.name,
    color: sc.color,
    summary: simulationResults[i],
  }));

  return (
    <VStack spacing={6} align="stretch">
      {/* Summary Statistics */}
      <SimpleGrid columns={{ base: 1, md: activeScenario.enableRetirement ? 4 : 3 }} spacing={4}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Median Projection</StatLabel>
              <StatNumber color="brand.accent">
                {formatCurrency(summaryStats.medianValue)}
              </StatNumber>
              <StatHelpText>
                {summaryStats.medianGainPercent >= 0 ? '+' : ''}
                {summaryStats.medianGainPercent.toFixed(1)}% ({formatCurrency(summaryStats.medianGain)})
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Pessimistic (10th %ile)</StatLabel>
              <StatNumber color="finance.negative">
                {formatCurrency(summaryStats.pessimistic)}
              </StatNumber>
              <StatHelpText>Downside scenario</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Optimistic (90th %ile)</StatLabel>
              <StatNumber color="finance.positive">
                {formatCurrency(summaryStats.optimistic)}
              </StatNumber>
              <StatHelpText>Upside scenario</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        {activeScenario.enableRetirement && (
          <Card bg={getSuccessRateProps(summaryStats.successRate).bg}>
            <CardBody>
              <Stat>
                <StatLabel>Probability of Success</StatLabel>
                <StatNumber color={getSuccessRateProps(summaryStats.successRate).color}>
                  {summaryStats.successRate.toFixed(0)}%
                </StatNumber>
                <StatHelpText>
                  {summaryStats.medianDepletionYear != null
                    ? `Median depletion: Year ${summaryStats.medianDepletionYear}`
                    : 'Portfolio survives in most scenarios'}
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        )}
      </SimpleGrid>

      {/* Scenario selector tabs */}
      {scenarios.length > 0 && (
        <HStack spacing={2} flexWrap="wrap">
          {scenarios.map((sc, i) => (
            <Card
              key={sc.id}
              size="sm"
              cursor="pointer"
              onClick={() => setActiveScenarioIndex(i)}
              borderWidth={2}
              borderColor={i === activeScenarioIndex ? sc.color : 'border.default'}
              bg={i === activeScenarioIndex ? scenarioCardBg : undefined}
            >
              <CardBody py={2} px={3}>
                <HStack spacing={2}>
                  <Box w={3} h={3} borderRadius="full" bg={sc.color} />
                  <Text fontSize="sm" fontWeight={i === activeScenarioIndex ? 'bold' : 'normal'}>
                    {sc.name}
                  </Text>
                  {sc.stressOverrides && (
                    <Badge size="sm" colorScheme="red" fontSize="2xs">
                      Stress
                    </Badge>
                  )}
                  {scenarios.length > 1 && (
                    <IconButton
                      aria-label="Remove scenario"
                      icon={<CloseIcon />}
                      size="xs"
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeScenario(i);
                      }}
                    />
                  )}
                </HStack>
              </CardBody>
            </Card>
          ))}
          {scenarios.length < 3 && (
            <Button
              size="sm"
              leftIcon={<AddIcon />}
              variant="outline"
              onClick={() => addScenario()}
            >
              Add Scenario
            </Button>
          )}
        </HStack>
      )}

      {/* Chart — single or multi-scenario */}
      {showMultiScenario ? (
        <ScenarioComparisonChart
          scenarios={scenarioChartData}
          activeIndex={activeScenarioIndex}
          showInflationAdjusted={showInflationAdjusted}
          retirementYear={activeScenario.enableRetirement ? activeScenario.retirementYear : undefined}
        />
      ) : (
        <Box>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={activeProjections}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis
                dataKey="year"
                label={{ value: 'Years', position: 'insideBottom', offset: -5 }}
              />
              <YAxis
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                label={{ value: 'Portfolio Value', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />

              {activeScenario.enableRetirement && activeScenario.retirementYear != null && (
                <ReferenceLine
                  x={activeScenario.retirementYear}
                  stroke="#A0AEC0"
                  strokeDasharray="6 4"
                  label={{ value: 'Retirement', position: 'top', fill: '#A0AEC0' }}
                />
              )}

              {/* Percentile bands */}
              <Area type="monotone" dataKey="percentile90" stroke="transparent" fill="#48BB78" fillOpacity={0.1} name="" legendType="none" />
              <Area type="monotone" dataKey="percentile75" stroke="transparent" fill="#4299E1" fillOpacity={0.15} name="" legendType="none" />
              <Area type="monotone" dataKey="percentile25" stroke="transparent" fill="#ED8936" fillOpacity={0.15} name="" legendType="none" />
              <Area type="monotone" dataKey="percentile10" stroke="transparent" fill="#F56565" fillOpacity={0.1} name="" legendType="none" />

              {!showInflationAdjusted && (
                <>
                  <Line type="monotone" dataKey="percentile90" stroke="#48BB78" strokeWidth={2} strokeDasharray="3 3" name="Optimistic (90th percentile)" dot={false} />
                  <Line type="monotone" dataKey="median" stroke="#4299E1" strokeWidth={3} name="Average (50th percentile)" dot={false} />
                  <Line type="monotone" dataKey="percentile10" stroke="#F56565" strokeWidth={2} strokeDasharray="3 3" name="Conservative (10th percentile)" dot={false} />
                </>
              )}

              {showInflationAdjusted && (
                <>
                  <Line type="monotone" dataKey="percentile90InflationAdjusted" stroke="#48BB78" strokeWidth={2} strokeDasharray="5 5" name="Optimistic (90th, Inflation Adjusted)" dot={false} />
                  <Line type="monotone" dataKey="medianInflationAdjusted" stroke="#ED8936" strokeWidth={3} strokeDasharray="5 5" name="Average (50th, Inflation Adjusted)" dot={false} />
                  <Line type="monotone" dataKey="percentile10InflationAdjusted" stroke="#F56565" strokeWidth={2} strokeDasharray="5 5" name="Conservative (10th, Inflation Adjusted)" dot={false} />
                </>
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </Box>
      )}

      {/* Controls */}
      <Card>
        <CardBody>
          <VStack spacing={6} align="stretch">
            <Text fontWeight="bold" fontSize="lg">
              Simulation Parameters
              {scenarios.length > 1 && (
                <Badge ml={2} colorScheme="blue">{activeScenario.name}</Badge>
              )}
            </Text>

            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
              {/* Annual Return */}
              <FormControl>
                <FormLabel>Annual Return (%)</FormLabel>
                <HStack spacing={4}>
                  <NumberInput
                    value={activeScenario.annualReturn}
                    onChange={(_, val) => !isNaN(val) && updateField('annualReturn', val)}
                    min={-20}
                    max={30}
                    step={0.5}
                    w="120px"
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                  <Text fontSize="sm" color="text.secondary">
                    Historical S&P 500: ~10%
                  </Text>
                </HStack>
              </FormControl>

              {/* Volatility */}
              <FormControl>
                <FormLabel>Volatility (%)</FormLabel>
                <HStack spacing={4}>
                  <NumberInput
                    value={activeScenario.volatility}
                    onChange={(_, val) => !isNaN(val) && updateField('volatility', val)}
                    min={0}
                    max={50}
                    step={1}
                    w="120px"
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                  <Text fontSize="sm" color="text.secondary">
                    S&P 500: ~15%
                  </Text>
                </HStack>
              </FormControl>

              {/* Inflation Rate */}
              <FormControl>
                <FormLabel>Inflation Rate (%)</FormLabel>
                <HStack spacing={4}>
                  <NumberInput
                    value={activeScenario.inflationRate}
                    onChange={(_, val) => !isNaN(val) && updateField('inflationRate', val)}
                    min={0}
                    max={10}
                    step={0.5}
                    w="120px"
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                  <Text fontSize="sm" color="text.secondary">
                    Historical: ~3%
                  </Text>
                </HStack>
              </FormControl>

              {/* Years */}
              <FormControl>
                <FormLabel>
                  Years: <strong>{sliderYears}</strong>
                </FormLabel>
                <Slider
                  value={sliderYears}
                  onChange={(val) => setSliderYears(val)}
                  onChangeEnd={(val) => updateField('years', val)}
                  min={1}
                  max={100}
                  step={1}
                >
                  <SliderTrack>
                    <SliderFilledTrack />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
              </FormControl>
            </SimpleGrid>

            {/* Retirement Phase */}
            <Divider />
            <VStack spacing={4} align="stretch">
              <FormControl display="flex" alignItems="center" w="auto">
                <FormLabel mb="0" mr={2} fontWeight="bold">
                  Enable Retirement Phase
                </FormLabel>
                <Switch
                  isChecked={activeScenario.enableRetirement}
                  onChange={(e) => updateField('enableRetirement', e.target.checked)}
                  colorScheme="brand"
                />
              </FormControl>

              {activeScenario.enableRetirement && (
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                  <FormControl>
                    <FormLabel>Retirement Year</FormLabel>
                    <NumberInput
                      value={activeScenario.retirementYear ?? Math.round(activeScenario.years / 2)}
                      onChange={(_, val) => !isNaN(val) && updateField('retirementYear', val)}
                      min={1}
                      max={activeScenario.years}
                      step={1}
                      w="120px"
                    >
                      <NumberInputField />
                      <NumberInputStepper>
                        <NumberIncrementStepper />
                        <NumberDecrementStepper />
                      </NumberInputStepper>
                    </NumberInput>
                  </FormControl>

                  <FormControl>
                    <FormLabel>Withdrawal Strategy</FormLabel>
                    <RadioGroup
                      value={activeScenario.withdrawalStrategy}
                      onChange={(val) => updateField('withdrawalStrategy', val as 'fixed' | 'percent')}
                    >
                      <Stack direction="row" spacing={4}>
                        <Radio value="percent">% of Portfolio (4% Rule)</Radio>
                        <Radio value="fixed">Fixed Amount</Radio>
                      </Stack>
                    </RadioGroup>
                  </FormControl>

                  {activeScenario.withdrawalStrategy === 'fixed' ? (
                    <FormControl>
                      <FormLabel>Annual Withdrawal ($)</FormLabel>
                      <NumberInput
                        value={activeScenario.annualWithdrawal ?? 40000}
                        onChange={(_, val) => !isNaN(val) && updateField('annualWithdrawal', val)}
                        min={0}
                        max={1000000}
                        step={1000}
                        w="160px"
                      >
                        <NumberInputField />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    </FormControl>
                  ) : (
                    <FormControl>
                      <FormLabel>Withdrawal Rate (%)</FormLabel>
                      <NumberInput
                        value={activeScenario.withdrawalRate ?? 4}
                        onChange={(_, val) => !isNaN(val) && updateField('withdrawalRate', val)}
                        min={0}
                        max={20}
                        step={0.5}
                        w="120px"
                      >
                        <NumberInputField />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    </FormControl>
                  )}
                </SimpleGrid>
              )}
            </VStack>

            {/* Stress Tests */}
            <Divider />
            <VStack spacing={3} align="stretch">
              <Text fontWeight="bold">Stress Tests</Text>
              <Wrap spacing={3}>
                {Object.entries(STRESS_SCENARIOS).map(([key, preset]) => (
                  <WrapItem key={key}>
                    <Button
                      size="sm"
                      variant={stressBtnVariant}
                      colorScheme="red"
                      onClick={() => applyStressPreset(key)}
                    >
                      {preset.name}
                    </Button>
                  </WrapItem>
                ))}
              </Wrap>
              <Text fontSize="xs" color="text.muted">
                Applies deterministic market conditions then resumes randomized simulation.
              </Text>
            </VStack>

            <Divider />

            {/* Toggle Options */}
            <HStack spacing={6} pt={2}>
              <FormControl display="flex" alignItems="center" w="auto">
                <FormLabel mb="0" mr={2}>
                  Show Inflation-Adjusted
                </FormLabel>
                <Switch
                  isChecked={showInflationAdjusted}
                  onChange={(e) => setShowInflationAdjusted(e.target.checked)}
                  colorScheme="brand"
                />
              </FormControl>

              <Button onClick={handleReset} variant="outline" size="sm">
                Reset to Defaults
              </Button>
            </HStack>

            {/* Disclaimer */}
            <Text fontSize="xs" color="text.muted" fontStyle="italic">
              Note: These projections are based on Monte Carlo simulations using
              historical market data. Past performance does not guarantee future
              results. Consult a financial advisor for personalized advice.
            </Text>
          </VStack>
        </CardBody>
      </Card>
    </VStack>
  );
};
