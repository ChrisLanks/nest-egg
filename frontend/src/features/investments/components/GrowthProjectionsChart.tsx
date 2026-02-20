/**
 * Growth Projections Chart Component
 *
 * Uses Monte Carlo simulation to project portfolio growth with:
 * - Configurable return rate, volatility, and inflation
 * - Percentile bands showing range of outcomes
 * - Inflation-adjusted projections
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
} from '@chakra-ui/react';
import { useState, useMemo } from 'react';
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
} from 'recharts';
import { runMonteCarloSimulation } from '../../../utils/monteCarloSimulation';

interface GrowthProjectionsChartProps {
  currentValue: number;
  monthlyContribution?: number;
}

export const GrowthProjectionsChart = ({ currentValue, monthlyContribution = 0 }: GrowthProjectionsChartProps) => {
  // Simulation parameters with defaults
  const [annualReturn, setAnnualReturn] = useState(7);
  const [volatility, setVolatility] = useState(15);
  const [inflationRate, setInflationRate] = useState(3);
  const [years, setYears] = useState(10);
  const [showInflationAdjusted, setShowInflationAdjusted] = useState(true);

  // Run simulation
  const projectionData = useMemo(() => {
    return runMonteCarloSimulation({
      currentValue,
      years,
      simulations: 1000,
      annualReturn,
      volatility,
      inflationRate,
      monthlyContribution,
    });
  }, [currentValue, years, annualReturn, volatility, inflationRate, monthlyContribution]);

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    const finalYear = projectionData[projectionData.length - 1];
    return {
      medianValue: finalYear.median,
      medianGain: finalYear.median - currentValue,
      medianGainPercent:
        ((finalYear.median - currentValue) / currentValue) * 100,
      pessimistic: finalYear.percentile10,
      optimistic: finalYear.percentile90,
      inflationAdjustedMedian: finalYear.medianInflationAdjusted,
    };
  }, [projectionData, currentValue]);

  // Reset to defaults
  const handleReset = () => {
    setAnnualReturn(7);
    setVolatility(15);
    setInflationRate(3);
    setYears(10);
  };

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Custom tooltip
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

  return (
    <VStack spacing={6} align="stretch">
      {/* Summary Statistics */}
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Median Projection</StatLabel>
              <StatNumber color="brand.600">
                {formatCurrency(summaryStats.medianValue)}
              </StatNumber>
              <StatHelpText>
                {summaryStats.medianGainPercent >= 0 ? '+' : ''}
                {summaryStats.medianGainPercent.toFixed(1)}% (
                {formatCurrency(summaryStats.medianGain)})
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Pessimistic (10th %ile)</StatLabel>
              <StatNumber color="red.600">
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
              <StatNumber color="green.600">
                {formatCurrency(summaryStats.optimistic)}
              </StatNumber>
              <StatHelpText>Upside scenario</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>

      {/* Chart */}
      <Box>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={projectionData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis
              dataKey="year"
              label={{
                value: 'Years',
                position: 'insideBottom',
                offset: -5,
              }}
            />
            <YAxis
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              label={{
                value: 'Portfolio Value',
                angle: -90,
                position: 'insideLeft',
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />

            {/* Percentile bands (background shading) */}
            <Area
              type="monotone"
              dataKey="percentile90"
              stroke="transparent"
              fill="#48BB78"
              fillOpacity={0.1}
              name=""
              legendType="none"
            />
            <Area
              type="monotone"
              dataKey="percentile75"
              stroke="transparent"
              fill="#4299E1"
              fillOpacity={0.15}
              name=""
              legendType="none"
            />
            <Area
              type="monotone"
              dataKey="percentile25"
              stroke="transparent"
              fill="#ED8936"
              fillOpacity={0.15}
              name=""
              legendType="none"
            />
            <Area
              type="monotone"
              dataKey="percentile10"
              stroke="transparent"
              fill="#F56565"
              fillOpacity={0.1}
              name=""
              legendType="none"
            />

            {/* Non-inflation-adjusted lines - only show when inflation adjustment is off */}
            {!showInflationAdjusted && (
              <>
                <Line
                  type="monotone"
                  dataKey="percentile90"
                  stroke="#48BB78"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                  name="Optimistic (90th percentile)"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="median"
                  stroke="#4299E1"
                  strokeWidth={3}
                  name="Average (50th percentile)"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="percentile10"
                  stroke="#F56565"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                  name="Conservative (10th percentile)"
                  dot={false}
                />
              </>
            )}

            {/* Inflation-adjusted lines - only show when inflation adjustment is on */}
            {showInflationAdjusted && (
              <>
                <Line
                  type="monotone"
                  dataKey="percentile90InflationAdjusted"
                  stroke="#48BB78"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  name="Optimistic (90th, Inflation Adjusted)"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="medianInflationAdjusted"
                  stroke="#ED8936"
                  strokeWidth={3}
                  strokeDasharray="5 5"
                  name="Average (50th, Inflation Adjusted)"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="percentile10InflationAdjusted"
                  stroke="#F56565"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  name="Conservative (10th, Inflation Adjusted)"
                  dot={false}
                />
              </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </Box>

      {/* Controls */}
      <Card>
        <CardBody>
          <VStack spacing={6} align="stretch">
            <Text fontWeight="bold" fontSize="lg">
              Simulation Parameters
            </Text>

            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
              {/* Annual Return */}
              <FormControl>
                <FormLabel>Annual Return (%)</FormLabel>
                <HStack spacing={4}>
                  <NumberInput
                    value={annualReturn}
                    onChange={(_, val) => setAnnualReturn(val)}
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
                  <Text fontSize="sm" color="gray.600">
                    Historical S&P 500: ~10%
                  </Text>
                </HStack>
              </FormControl>

              {/* Volatility */}
              <FormControl>
                <FormLabel>Volatility (%)</FormLabel>
                <HStack spacing={4}>
                  <NumberInput
                    value={volatility}
                    onChange={(_, val) => setVolatility(val)}
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
                  <Text fontSize="sm" color="gray.600">
                    S&P 500: ~15%
                  </Text>
                </HStack>
              </FormControl>

              {/* Inflation Rate */}
              <FormControl>
                <FormLabel>Inflation Rate (%)</FormLabel>
                <HStack spacing={4}>
                  <NumberInput
                    value={inflationRate}
                    onChange={(_, val) => setInflationRate(val)}
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
                  <Text fontSize="sm" color="gray.600">
                    Historical: ~3%
                  </Text>
                </HStack>
              </FormControl>

              {/* Years */}
              <FormControl>
                <FormLabel>
                  Years: <strong>{years}</strong>
                </FormLabel>
                <Slider
                  value={years}
                  onChange={(val) => setYears(val)}
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
            <Text fontSize="xs" color="gray.500" fontStyle="italic">
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
