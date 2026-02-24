/**
 * Rebalancing Panel
 *
 * Shows target vs current allocation, drift analysis, and trade recommendations.
 * Supports preset portfolios (Bogleheads 3-Fund, 60/40, etc.) and custom allocations.
 */

import {
  Box,
  VStack,
  HStack,
  Text,
  SimpleGrid,
  Card,
  CardBody,
  Button,
  Badge,
  Heading,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  FormControl,
  FormLabel,
  Spinner,
  Center,
  Alert,
  AlertIcon,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Wrap,
  WrapItem,
  Divider,
  Input,
  IconButton,
  useColorModeValue,
  useToast,
} from '@chakra-ui/react';
import { AddIcon, CloseIcon, CheckIcon } from '@chakra-ui/icons';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
} from 'recharts';
import api from '../../../services/api';

interface AllocationSlice {
  asset_class: string;
  target_percent: number;
  label: string;
}

interface TargetAllocation {
  id: string;
  name: string;
  allocations: AllocationSlice[];
  drift_threshold: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface DriftItem {
  asset_class: string;
  label: string;
  target_percent: number;
  current_percent: number;
  current_value: number;
  drift_percent: number;
  drift_value: number;
  status: 'overweight' | 'underweight' | 'on_target';
}

interface TradeRecommendation {
  asset_class: string;
  label: string;
  action: 'BUY' | 'SELL';
  amount: number;
  current_value: number;
  target_value: number;
  current_percent: number;
  target_percent: number;
}

interface RebalancingAnalysis {
  target_allocation_id: string;
  target_allocation_name: string;
  portfolio_total: number;
  drift_items: DriftItem[];
  needs_rebalancing: boolean;
  max_drift_percent: number;
  trade_recommendations: TradeRecommendation[];
}

interface PresetPortfolio {
  name: string;
  allocations: AllocationSlice[];
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export const RebalancingPanel = () => {
  const [showCustomBuilder, setShowCustomBuilder] = useState(false);
  const [customName, setCustomName] = useState('');
  const [customSlices, setCustomSlices] = useState<AllocationSlice[]>([
    { asset_class: 'domestic', target_percent: 60, label: 'US Stocks' },
    { asset_class: 'international', target_percent: 30, label: 'International Stocks' },
    { asset_class: 'bond', target_percent: 10, label: 'Bonds' },
  ]);

  const toast = useToast();
  const queryClient = useQueryClient();

  // Dark mode colors
  const overweightColor = useColorModeValue('red.600', 'red.300');
  const underweightColor = useColorModeValue('orange.600', 'orange.300');
  const onTargetColor = useColorModeValue('green.600', 'green.300');
  const buyBadgeBg = useColorModeValue('green.50', 'green.900');
  const sellBadgeBg = useColorModeValue('red.50', 'red.900');
  const cardBg = useColorModeValue('gray.50', 'gray.700');
  const barCurrentColor = useColorModeValue('#4299E1', '#63B3ED');
  const barTargetColor = useColorModeValue('#A0AEC0', '#718096');

  // Fetch presets
  const { data: presets } = useQuery<Record<string, PresetPortfolio>>({
    queryKey: ['rebalancing-presets'],
    queryFn: async () => {
      const res = await api.get('/rebalancing/presets');
      return res.data;
    },
  });

  // Fetch active target allocation
  const { data: allocations, isLoading: allocationsLoading } = useQuery<TargetAllocation[]>({
    queryKey: ['target-allocations'],
    queryFn: async () => {
      const res = await api.get('/rebalancing/target-allocations');
      return res.data;
    },
  });

  const activeAllocation = allocations?.find((a) => a.is_active);

  // Fetch analysis (only when active allocation exists)
  const {
    data: analysis,
    isLoading: analysisLoading,
  } = useQuery<RebalancingAnalysis>({
    queryKey: ['rebalancing-analysis'],
    queryFn: async () => {
      const res = await api.get('/rebalancing/analysis');
      return res.data;
    },
    enabled: !!activeAllocation,
  });

  // Create from preset
  const createFromPreset = useMutation({
    mutationFn: async (presetKey: string) => {
      const res = await api.post(`/rebalancing/target-allocations/from-preset?preset_key=${presetKey}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['target-allocations'] });
      queryClient.invalidateQueries({ queryKey: ['rebalancing-analysis'] });
      toast({ title: 'Target allocation set', status: 'success', duration: 3000 });
    },
    onError: () => {
      toast({ title: 'Failed to set allocation', status: 'error', duration: 3000 });
    },
  });

  // Create custom
  const createCustom = useMutation({
    mutationFn: async () => {
      const res = await api.post('/rebalancing/target-allocations', {
        name: customName || 'Custom Allocation',
        allocations: customSlices,
        drift_threshold: 5.0,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['target-allocations'] });
      queryClient.invalidateQueries({ queryKey: ['rebalancing-analysis'] });
      setShowCustomBuilder(false);
      toast({ title: 'Custom allocation created', status: 'success', duration: 3000 });
    },
    onError: () => {
      toast({ title: 'Allocations must sum to 100%', status: 'error', duration: 3000 });
    },
  });

  // Delete allocation
  const deleteAllocation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/rebalancing/target-allocations/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['target-allocations'] });
      queryClient.invalidateQueries({ queryKey: ['rebalancing-analysis'] });
      toast({ title: 'Allocation removed', status: 'info', duration: 3000 });
    },
  });

  // Update drift threshold
  const updateThreshold = useMutation({
    mutationFn: async ({ id, threshold }: { id: string; threshold: number }) => {
      const res = await api.patch(`/rebalancing/target-allocations/${id}`, {
        drift_threshold: threshold,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['target-allocations'] });
      queryClient.invalidateQueries({ queryKey: ['rebalancing-analysis'] });
    },
  });

  const customTotal = customSlices.reduce((s, c) => s + Number(c.target_percent), 0);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'overweight':
        return <Badge colorScheme="red">Overweight</Badge>;
      case 'underweight':
        return <Badge colorScheme="orange">Underweight</Badge>;
      default:
        return <Badge colorScheme="green">On Target</Badge>;
    }
  };

  if (allocationsLoading) {
    return (
      <Center py={12}>
        <Spinner size="lg" color="brand.500" />
      </Center>
    );
  }

  // ── Setup view (no active allocation) ────────────────────────────────
  if (!activeAllocation) {
    return (
      <VStack spacing={6} align="stretch">
        <VStack spacing={2} align="flex-start">
          <Heading size="md">Portfolio Rebalancing</Heading>
          <Text color="text.secondary">
            Select a target allocation to see how your portfolio compares and get rebalancing recommendations.
          </Text>
        </VStack>

        {/* Preset portfolios */}
        <Heading size="sm">Preset Portfolios</Heading>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {presets &&
            Object.entries(presets).map(([key, preset]) => (
              <Card key={key} variant="outline" cursor="pointer" _hover={{ borderColor: 'blue.400' }}>
                <CardBody>
                  <VStack align="stretch" spacing={3}>
                    <Text fontWeight="bold">{preset.name}</Text>
                    <VStack spacing={1} align="stretch">
                      {preset.allocations.map((s) => (
                        <HStack key={s.asset_class} justify="space-between">
                          <Text fontSize="sm" color="text.secondary">
                            {s.label}
                          </Text>
                          <Text fontSize="sm" fontWeight="medium">
                            {s.target_percent}%
                          </Text>
                        </HStack>
                      ))}
                    </VStack>
                    <Button
                      size="sm"
                      colorScheme="blue"
                      onClick={() => createFromPreset.mutate(key)}
                      isLoading={createFromPreset.isPending}
                    >
                      Use This
                    </Button>
                  </VStack>
                </CardBody>
              </Card>
            ))}
        </SimpleGrid>

        <Divider />

        {/* Custom builder */}
        {!showCustomBuilder ? (
          <Button
            leftIcon={<AddIcon />}
            variant="outline"
            onClick={() => setShowCustomBuilder(true)}
            alignSelf="flex-start"
          >
            Create Custom Allocation
          </Button>
        ) : (
          <Card>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <Heading size="sm">Custom Allocation</Heading>
                <FormControl>
                  <FormLabel>Name</FormLabel>
                  <Input
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    placeholder="My Custom Portfolio"
                    maxW="300px"
                  />
                </FormControl>

                {customSlices.map((slice, i) => (
                  <HStack key={i} spacing={4}>
                    <FormControl flex={1}>
                      <Input
                        value={slice.label}
                        onChange={(e) => {
                          const next = [...customSlices];
                          next[i] = { ...next[i], label: e.target.value };
                          setCustomSlices(next);
                        }}
                        placeholder="Label"
                        size="sm"
                      />
                    </FormControl>
                    <FormControl flex={1}>
                      <Input
                        value={slice.asset_class}
                        onChange={(e) => {
                          const next = [...customSlices];
                          next[i] = { ...next[i], asset_class: e.target.value };
                          setCustomSlices(next);
                        }}
                        placeholder="asset_class"
                        size="sm"
                      />
                    </FormControl>
                    <FormControl w="100px">
                      <NumberInput
                        value={slice.target_percent}
                        onChange={(_, val) => {
                          if (isNaN(val)) return;
                          const next = [...customSlices];
                          next[i] = { ...next[i], target_percent: val };
                          setCustomSlices(next);
                        }}
                        min={0}
                        max={100}
                        size="sm"
                      >
                        <NumberInputField />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    </FormControl>
                    <IconButton
                      aria-label="Remove"
                      icon={<CloseIcon />}
                      size="sm"
                      variant="ghost"
                      onClick={() => setCustomSlices((prev) => prev.filter((_, j) => j !== i))}
                      isDisabled={customSlices.length <= 1}
                    />
                  </HStack>
                ))}

                <HStack>
                  <Button
                    size="sm"
                    leftIcon={<AddIcon />}
                    variant="ghost"
                    onClick={() =>
                      setCustomSlices((prev) => [
                        ...prev,
                        { asset_class: '', target_percent: 0, label: '' },
                      ])
                    }
                  >
                    Add Class
                  </Button>
                  <Text fontSize="sm" color={customTotal === 100 ? onTargetColor : overweightColor}>
                    Total: {customTotal}%{customTotal !== 100 && ' (must be 100%)'}
                  </Text>
                </HStack>

                <HStack>
                  <Button
                    colorScheme="blue"
                    size="sm"
                    leftIcon={<CheckIcon />}
                    onClick={() => createCustom.mutate()}
                    isLoading={createCustom.isPending}
                    isDisabled={customTotal !== 100}
                  >
                    Save
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowCustomBuilder(false)}
                  >
                    Cancel
                  </Button>
                </HStack>
              </VStack>
            </CardBody>
          </Card>
        )}
      </VStack>
    );
  }

  // ── Analysis view (active allocation exists) ─────────────────────────
  return (
    <VStack spacing={6} align="stretch">
      {/* Header */}
      <HStack justify="space-between" flexWrap="wrap">
        <VStack align="flex-start" spacing={0}>
          <Heading size="md">Portfolio Rebalancing</Heading>
          <HStack spacing={2}>
            <Text color="text.secondary">Target: {activeAllocation.name}</Text>
            <Badge colorScheme="blue">Active</Badge>
          </HStack>
        </VStack>
        <HStack>
          <Button
            size="sm"
            variant="outline"
            colorScheme="red"
            onClick={() => deleteAllocation.mutate(activeAllocation.id)}
            isLoading={deleteAllocation.isPending}
          >
            Remove
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => deleteAllocation.mutate(activeAllocation.id)}
          >
            Switch Allocation
          </Button>
        </HStack>
      </HStack>

      {analysisLoading ? (
        <Center py={12}>
          <Spinner size="lg" color="brand.500" />
        </Center>
      ) : analysis ? (
        <>
          {/* Summary stats */}
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Card>
              <CardBody>
                <Text fontSize="sm" color="text.secondary">Portfolio Total</Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {formatCurrency(Number(analysis.portfolio_total))}
                </Text>
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <Text fontSize="sm" color="text.secondary">Max Drift</Text>
                <Text
                  fontSize="2xl"
                  fontWeight="bold"
                  color={analysis.needs_rebalancing ? overweightColor : onTargetColor}
                >
                  {Number(analysis.max_drift_percent).toFixed(1)}%
                </Text>
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <Text fontSize="sm" color="text.secondary">Status</Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {analysis.needs_rebalancing ? (
                    <Badge colorScheme="orange" fontSize="lg" px={3} py={1}>
                      Rebalance Needed
                    </Badge>
                  ) : (
                    <Badge colorScheme="green" fontSize="lg" px={3} py={1}>
                      On Target
                    </Badge>
                  )}
                </Text>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* Current vs Target bar chart */}
          <Card>
            <CardBody>
              <Heading size="sm" mb={4}>
                Current vs Target Allocation
              </Heading>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={analysis.drift_items.map((d) => ({
                    name: d.label,
                    Current: Number(d.current_percent),
                    Target: Number(d.target_percent),
                    status: d.status,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis tickFormatter={(v) => `${v}%`} />
                  <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                  <Legend />
                  <Bar dataKey="Current" fill={barCurrentColor} name="Current %" />
                  <Bar dataKey="Target" fill={barTargetColor} name="Target %" />
                </BarChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>

          {/* Drift cards */}
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
            {analysis.drift_items.map((item) => (
              <Card key={item.asset_class} bg={cardBg}>
                <CardBody>
                  <HStack justify="space-between" mb={2}>
                    <Text fontWeight="bold">{item.label}</Text>
                    {getStatusBadge(item.status)}
                  </HStack>
                  <SimpleGrid columns={2} spacing={2} fontSize="sm">
                    <Text color="text.secondary">Target</Text>
                    <Text textAlign="right">{Number(item.target_percent).toFixed(1)}%</Text>
                    <Text color="text.secondary">Current</Text>
                    <Text textAlign="right">{Number(item.current_percent).toFixed(1)}%</Text>
                    <Text color="text.secondary">Drift</Text>
                    <Text
                      textAlign="right"
                      fontWeight="bold"
                      color={
                        item.status === 'overweight'
                          ? overweightColor
                          : item.status === 'underweight'
                          ? underweightColor
                          : onTargetColor
                      }
                    >
                      {Number(item.drift_percent) > 0 ? '+' : ''}
                      {Number(item.drift_percent).toFixed(1)}%
                    </Text>
                    <Text color="text.secondary">Value</Text>
                    <Text textAlign="right">{formatCurrency(Number(item.current_value))}</Text>
                  </SimpleGrid>
                </CardBody>
              </Card>
            ))}
          </SimpleGrid>

          {/* Drift threshold setting */}
          <Card>
            <CardBody>
              <HStack spacing={4} align="center">
                <FormControl display="flex" alignItems="center" w="auto">
                  <FormLabel mb="0" mr={2} whiteSpace="nowrap">
                    Drift Threshold (%)
                  </FormLabel>
                  <NumberInput
                    value={Number(activeAllocation.drift_threshold)}
                    onChange={(_, val) => {
                      if (!isNaN(val) && val >= 0 && val <= 50) {
                        updateThreshold.mutate({ id: activeAllocation.id, threshold: val });
                      }
                    }}
                    min={1}
                    max={50}
                    step={1}
                    w="100px"
                    size="sm"
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </FormControl>
                <Text fontSize="xs" color="text.muted">
                  Trade suggestions appear when any asset class drifts beyond this threshold.
                </Text>
              </HStack>
            </CardBody>
          </Card>

          {/* Trade recommendations */}
          {analysis.needs_rebalancing && analysis.trade_recommendations.length > 0 && (
            <Card>
              <CardBody>
                <Heading size="sm" mb={4}>
                  Suggested Trades
                </Heading>
                <Alert status="info" mb={4}>
                  <AlertIcon />
                  These are suggestions only. Consider tax implications and transaction costs before trading.
                </Alert>
                <Box overflowX="auto">
                  <Table size="sm" variant="simple">
                    <Thead>
                      <Tr>
                        <Th>Asset Class</Th>
                        <Th>Action</Th>
                        <Th isNumeric>Amount</Th>
                        <Th isNumeric>Current</Th>
                        <Th isNumeric>Target</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {analysis.trade_recommendations.map((rec) => (
                        <Tr key={rec.asset_class}>
                          <Td fontWeight="medium">{rec.label}</Td>
                          <Td>
                            <Badge
                              bg={rec.action === 'BUY' ? buyBadgeBg : sellBadgeBg}
                              color={rec.action === 'BUY' ? onTargetColor : overweightColor}
                              px={2}
                            >
                              {rec.action}
                            </Badge>
                          </Td>
                          <Td isNumeric fontWeight="bold">
                            {formatCurrency(Number(rec.amount))}
                          </Td>
                          <Td isNumeric>{Number(rec.current_percent).toFixed(1)}%</Td>
                          <Td isNumeric>{Number(rec.target_percent).toFixed(1)}%</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </CardBody>
            </Card>
          )}

          {!analysis.needs_rebalancing && (
            <Alert status="success">
              <AlertIcon />
              Your portfolio is within the drift threshold. No rebalancing needed right now.
            </Alert>
          )}
        </>
      ) : (
        <Alert status="warning">
          <AlertIcon />
          Unable to load analysis. Make sure you have holdings data in your portfolio.
        </Alert>
      )}
    </VStack>
  );
};
