/**
 * Main Retirement Planning page.
 *
 * Layout:
 * - Readiness score gauge at top
 * - Scenario tabs (create/select/duplicate/compare)
 * - Monte Carlo fan chart
 * - Life event timeline
 * - Two-column: scenario settings + details (portfolio, SS, healthcare, results, withdrawal comparison)
 */

import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Container,
  HStack,
  SimpleGrid,
  Spinner,
  Tab,
  TabList,
  Tabs,
  Text,
  useColorModeValue,
  useDisclosure,
  useToast,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useEffect, useRef, useState } from 'react';
import api from '../../../services/api';
import { AccountDataSummary } from '../components/AccountDataSummary';
import { HealthcareEstimator } from '../components/HealthcareEstimator';
import { LifeEventEditor } from '../components/LifeEventEditor';
import { LifeEventPresetPicker } from '../components/LifeEventPresetPicker';
import { LifeEventTimeline } from '../components/LifeEventTimeline';
import { RetirementFanChart } from '../components/RetirementFanChart';
import { RetirementScoreGauge } from '../components/RetirementScoreGauge';
import { ScenarioComparisonView } from '../components/ScenarioComparisonView';
import { ScenarioPanel } from '../components/ScenarioPanel';
import { SocialSecurityEstimator } from '../components/SocialSecurityEstimator';
import { WithdrawalStrategyComparison } from '../components/WithdrawalStrategyComparison';
import {
  useAddLifeEvent,
  useAddLifeEventFromPreset,
  useCreateDefaultScenario,
  useDeleteLifeEvent,
  useDuplicateScenario,
  useRetirementScenario,
  useRetirementScenarios,
  useRunSimulation,
  useScenarioComparison,
  useSimulationResults,
  useUpdateLifeEvent,
  useUpdateScenario,
} from '../hooks/useRetirementScenarios';
import type {
  LifeEvent,
  LifeEventCreate,
  RetirementScenarioSummary,
  ScenarioComparisonItem,
  WithdrawalComparison,
} from '../types/retirement';

export function RetirementPage() {
  const toast = useToast();
  const cardBg = useColorModeValue('white', 'gray.800');

  // Fetch scenarios list
  const { data: scenarios, isLoading: scenariosLoading } = useRetirementScenarios();
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(() => {
    try {
      return localStorage.getItem('retirement-active-scenario');
    } catch {
      return null;
    }
  });
  const scenarioIdRef = useRef(selectedScenarioId);

  // Fetch selected scenario detail
  const { data: scenario } = useRetirementScenario(selectedScenarioId);

  // Fetch simulation results for selected scenario
  const { data: results, isLoading: resultsLoading } = useSimulationResults(selectedScenarioId);

  // Mutations
  const createDefaultMutation = useCreateDefaultScenario();
  const updateMutation = useUpdateScenario();
  const simulateMutation = useRunSimulation();
  const duplicateMutation = useDuplicateScenario();
  const addLifeEventMutation = useAddLifeEvent();
  const addPresetMutation = useAddLifeEventFromPreset();
  const updateLifeEventMutation = useUpdateLifeEvent();
  const deleteLifeEventMutation = useDeleteLifeEvent();
  const comparisonMutation = useScenarioComparison();

  // Modal state
  const presetPicker = useDisclosure();
  const eventEditor = useDisclosure();
  const [editingEvent, setEditingEvent] = useState<LifeEvent | null>(null);
  const [comparisonData, setComparisonData] = useState<ScenarioComparisonItem[] | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  // Persist selected scenario to localStorage
  useEffect(() => {
    scenarioIdRef.current = selectedScenarioId;
    if (selectedScenarioId) {
      try {
        localStorage.setItem('retirement-active-scenario', selectedScenarioId);
      } catch { /* ignore */ }
    }
  }, [selectedScenarioId]);

  // Auto-select first scenario or default, and reset stale IDs
  useEffect(() => {
    if (!scenarios?.length) return;

    // If current selection exists in the fetched list, keep it
    if (selectedScenarioId && scenarios.find((s) => s.id === selectedScenarioId)) {
      return;
    }

    // Current ID is null or stale (not in DB) — pick a valid one
    const defaultScenario = scenarios.find((s) => s.is_default);
    setSelectedScenarioId(defaultScenario?.id ?? scenarios[0].id);
  }, [scenarios, selectedScenarioId]);

  // Handle creating first scenario
  const handleCreateDefault = useCallback(async () => {
    try {
      const newScenario = await createDefaultMutation.mutateAsync();
      setSelectedScenarioId(newScenario.id);
      toast({ title: 'Scenario created', status: 'success', duration: 2000 });
    } catch (err: any) {
      toast({
        title: 'Failed to create scenario',
        description: err?.response?.data?.detail || 'Please set your birthdate in preferences.',
        status: 'error',
        duration: 4000,
      });
    }
  }, [createDefaultMutation, toast]);

  // Handle scenario update
  const handleUpdate = useCallback(
    (updates: Record<string, unknown>) => {
      if (!selectedScenarioId) return;
      updateMutation.mutate({ id: selectedScenarioId, updates });
    },
    [selectedScenarioId, updateMutation]
  );

  // Handle running simulation
  const handleSimulate = useCallback(async () => {
    if (!selectedScenarioId) return;
    try {
      await simulateMutation.mutateAsync(selectedScenarioId);
      toast({ title: 'Simulation complete', status: 'success', duration: 2000 });
    } catch (err: any) {
      toast({
        title: 'Simulation failed',
        description: err?.response?.data?.detail || 'An error occurred.',
        status: 'error',
        duration: 4000,
      });
    }
  }, [selectedScenarioId, simulateMutation, toast]);

  // Handle tab selection
  const handleTabChange = useCallback(
    (index: number) => {
      if (scenarios && index < scenarios.length) {
        setSelectedScenarioId(scenarios[index].id);
        setShowComparison(false);
      }
    },
    [scenarios]
  );

  // Handle duplicate
  const handleDuplicate = useCallback(async () => {
    if (!selectedScenarioId) return;
    try {
      const dup = await duplicateMutation.mutateAsync({ id: selectedScenarioId });
      setSelectedScenarioId(dup.id);
      toast({ title: 'Scenario duplicated', status: 'success', duration: 2000 });
    } catch {
      toast({ title: 'Failed to duplicate', status: 'error', duration: 3000 });
    }
  }, [selectedScenarioId, duplicateMutation, toast]);

  // Handle compare
  const handleCompare = useCallback(async () => {
    if (!scenarios || scenarios.length < 2) {
      toast({ title: 'Need at least 2 scenarios to compare', status: 'warning', duration: 3000 });
      return;
    }
    try {
      const ids = scenarios.slice(0, 3).map((s) => s.id);
      const data = await comparisonMutation.mutateAsync(ids);
      setComparisonData(data);
      setShowComparison(true);
    } catch (err: any) {
      toast({
        title: 'Comparison failed',
        description: err?.response?.data?.detail || 'Run simulations on all scenarios first.',
        status: 'error',
        duration: 4000,
      });
    }
  }, [scenarios, comparisonMutation, toast]);

  // Life event handlers
  const handleAddPreset = useCallback(
    async (presetKey: string) => {
      if (!selectedScenarioId) return;
      try {
        await addPresetMutation.mutateAsync({ scenarioId: selectedScenarioId, presetKey });
        presetPicker.onClose();
        toast({ title: 'Life event added', status: 'success', duration: 2000 });
      } catch (err: any) {
        toast({
          title: 'Failed to add event',
          description: err?.response?.data?.detail || 'An error occurred.',
          status: 'error',
          duration: 3000,
        });
      }
    },
    [selectedScenarioId, addPresetMutation, presetPicker, toast]
  );

  const handleSaveEvent = useCallback(
    async (eventData: LifeEventCreate) => {
      if (!selectedScenarioId) return;
      try {
        if (editingEvent) {
          await updateLifeEventMutation.mutateAsync({
            eventId: editingEvent.id,
            updates: eventData,
          });
        } else {
          await addLifeEventMutation.mutateAsync({
            scenarioId: selectedScenarioId,
            event: eventData,
          });
        }
        eventEditor.onClose();
        setEditingEvent(null);
        toast({ title: editingEvent ? 'Event updated' : 'Event added', status: 'success', duration: 2000 });
      } catch (err: any) {
        toast({
          title: 'Failed to save event',
          description: err?.response?.data?.detail || 'An error occurred.',
          status: 'error',
          duration: 3000,
        });
      }
    },
    [selectedScenarioId, editingEvent, addLifeEventMutation, updateLifeEventMutation, eventEditor, toast]
  );

  const handleEditEvent = useCallback(
    (event: LifeEvent) => {
      setEditingEvent(event);
      eventEditor.onOpen();
    },
    [eventEditor]
  );

  const handleDeleteEvent = useCallback(
    async (eventId: string) => {
      try {
        await deleteLifeEventMutation.mutateAsync(eventId);
        toast({ title: 'Event removed', status: 'success', duration: 2000 });
      } catch {
        toast({ title: 'Failed to delete event', status: 'error', duration: 3000 });
      }
    },
    [deleteLifeEventMutation, toast]
  );

  const handleSsClaimingAgeChange = useCallback(
    (age: number) => {
      handleUpdate({ social_security_start_age: age });
    },
    [handleUpdate]
  );

  // CSV export
  const handleExportCsv = useCallback(async () => {
    if (!selectedScenarioId) return;
    try {
      const response = await api.get(
        `/retirement/scenarios/${selectedScenarioId}/export-csv`,
        { responseType: 'blob' }
      );
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `retirement_projections.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast({ title: 'Export failed', status: 'error', duration: 3000 });
    }
  }, [selectedScenarioId, toast]);

  const selectedTabIndex = scenarios?.findIndex((s) => s.id === selectedScenarioId) ?? 0;

  // Parse withdrawal comparison from results
  const withdrawalComparison: WithdrawalComparison | null =
    results?.withdrawal_comparison as WithdrawalComparison | null;

  // Empty state: no scenarios yet
  if (!scenariosLoading && (!scenarios || scenarios.length === 0)) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={6} textAlign="center" py={16}>
          <Text fontSize="2xl" fontWeight="bold">
            Retirement Planner
          </Text>
          <Text color="gray.500" maxW="md">
            Plan your retirement by modeling different scenarios with Monte Carlo simulation.
            See how different retirement ages, spending levels, and life events affect your
            financial future.
          </Text>
          <Button
            colorScheme="blue"
            size="lg"
            onClick={handleCreateDefault}
            isLoading={createDefaultMutation.isPending}
            loadingText="Setting up..."
          >
            Create Your First Scenario
          </Button>
          <Alert status="info" borderRadius="md" maxW="md">
            <AlertIcon />
            Make sure your birthdate is set in Preferences for accurate projections.
          </Alert>
        </VStack>
      </Container>
    );
  }

  if (scenariosLoading) {
    return (
      <Container maxW="container.xl" py={8} textAlign="center">
        <Spinner size="xl" />
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <Text fontSize="2xl" fontWeight="bold">
            Retirement Planner
          </Text>
          <HStack spacing={2}>
            <Button
              size="sm"
              variant="outline"
              onClick={handleDuplicate}
              isLoading={duplicateMutation.isPending}
              isDisabled={!selectedScenarioId}
            >
              Duplicate
            </Button>
            {results && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleExportCsv}
              >
                Export CSV
              </Button>
            )}
            {scenarios && scenarios.length >= 2 && (
              <Button
                size="sm"
                variant={showComparison ? 'solid' : 'outline'}
                colorScheme="purple"
                onClick={() => (showComparison ? setShowComparison(false) : handleCompare())}
                isLoading={comparisonMutation.isPending}
              >
                {showComparison ? 'Hide Comparison' : 'Compare Scenarios'}
              </Button>
            )}
          </HStack>
        </HStack>

        {/* Readiness Score */}
        <RetirementScoreGauge
          score={results?.readiness_score ?? null}
          successRate={results?.success_rate ?? null}
          isLoading={simulateMutation.isPending || resultsLoading}
        />

        {/* Scenario Comparison */}
        {showComparison && comparisonData && (
          <ScenarioComparisonView scenarios={comparisonData} />
        )}

        {/* Scenario Tabs */}
        {scenarios && scenarios.length > 0 && (
          <Tabs
            index={selectedTabIndex >= 0 ? selectedTabIndex : 0}
            onChange={handleTabChange}
            variant="enclosed"
            size="sm"
          >
            <TabList>
              {scenarios.map((s: RetirementScenarioSummary) => (
                <Tab key={s.id}>
                  {s.name}
                  {s.readiness_score !== null && (
                    <Text as="span" ml={2} fontSize="xs" color="gray.500">
                      ({s.readiness_score})
                    </Text>
                  )}
                </Tab>
              ))}
            </TabList>
          </Tabs>
        )}

        {/* Fan Chart */}
        {!showComparison && (
          <RetirementFanChart
            projections={results?.projections ?? []}
            retirementAge={scenario?.retirement_age ?? 67}
            socialSecurityStartAge={scenario?.social_security_start_age ?? undefined}
            isLoading={simulateMutation.isPending}
          />
        )}

        {/* Life Event Timeline */}
        {scenario && scenario.life_events.length > 0 && (
          <LifeEventTimeline
            events={scenario.life_events}
            retirementAge={scenario.retirement_age}
            lifeExpectancy={scenario.life_expectancy}
            onEventClick={handleEditEvent}
            onDeleteEvent={handleDeleteEvent}
          />
        )}

        {/* Add Life Event Buttons */}
        {scenario && (
          <HStack spacing={2}>
            <Button size="sm" variant="outline" colorScheme="blue" onClick={presetPicker.onOpen}>
              + Add Life Event
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setEditingEvent(null);
                eventEditor.onOpen();
              }}
            >
              Custom Event
            </Button>
          </HStack>
        )}

        {/* Two-column: Settings + Details */}
        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
          <VStack spacing={6} align="stretch">
            <ScenarioPanel
              scenario={scenario ?? null}
              onUpdate={handleUpdate}
              onSimulate={handleSimulate}
              isSimulating={simulateMutation.isPending}
            />

            {/* Account Data Summary */}
            <AccountDataSummary />
          </VStack>

          {/* Right column: SS, Healthcare, Withdrawal, Results */}
          <VStack spacing={4} align="stretch">
            {/* Social Security Estimator */}
            <SocialSecurityEstimator
              currentIncome={scenario?.current_annual_income}
              claimingAge={scenario?.social_security_start_age ?? 67}
              manualOverride={scenario?.social_security_monthly}
              onClaimingAgeChange={handleSsClaimingAgeChange}
            />

            {/* Healthcare Estimator */}
            <HealthcareEstimator
              retirementIncome={scenario?.annual_spending_retirement ?? 50000}
              medicalInflationRate={scenario?.medical_inflation_rate ?? 6}
            />

            {/* Withdrawal Strategy Comparison */}
            {withdrawalComparison && (
              <WithdrawalStrategyComparison
                comparison={withdrawalComparison}
                withdrawalRate={scenario?.withdrawal_rate ?? 4}
              />
            )}

            {/* Results summary */}
            {results && (
              <Box bg={cardBg} p={5} borderRadius="xl" shadow="sm">
                <Text fontSize="lg" fontWeight="semibold" mb={3}>
                  Simulation Summary
                </Text>
                <VStack spacing={2} align="stretch" fontSize="sm">
                  <HStack justify="space-between">
                    <Text color="gray.500">Success Rate</Text>
                    <Text fontWeight="bold">{results.success_rate.toFixed(1)}%</Text>
                  </HStack>
                  {results.median_portfolio_at_retirement && (
                    <HStack justify="space-between">
                      <Text color="gray.500">Portfolio at Retirement</Text>
                      <Text fontWeight="bold">
                        ${(results.median_portfolio_at_retirement / 1000000).toFixed(2)}M
                      </Text>
                    </HStack>
                  )}
                  {results.median_portfolio_at_end !== null && (
                    <HStack justify="space-between">
                      <Text color="gray.500">Portfolio at End</Text>
                      <Text fontWeight="bold">
                        ${(results.median_portfolio_at_end / 1000000).toFixed(2)}M
                      </Text>
                    </HStack>
                  )}
                  {results.median_depletion_age && (
                    <HStack justify="space-between">
                      <Text color="red.400">Median Depletion Age</Text>
                      <Text fontWeight="bold" color="red.400">
                        {results.median_depletion_age}
                      </Text>
                    </HStack>
                  )}
                  {results.estimated_pia && (
                    <HStack justify="space-between">
                      <Text color="gray.500">Estimated SS (PIA)</Text>
                      <Text fontWeight="bold">
                        ${results.estimated_pia.toFixed(0)}/mo
                      </Text>
                    </HStack>
                  )}
                  <HStack justify="space-between">
                    <Text color="gray.500">Simulations Run</Text>
                    <Text>{results.num_simulations.toLocaleString()}</Text>
                  </HStack>
                  {results.compute_time_ms && (
                    <HStack justify="space-between">
                      <Text color="gray.500">Compute Time</Text>
                      <Text>{(results.compute_time_ms / 1000).toFixed(1)}s</Text>
                    </HStack>
                  )}
                </VStack>
              </Box>
            )}

            {!results && !resultsLoading && selectedScenarioId && (
              <Alert status="info" borderRadius="md">
                <AlertIcon />
                Click "Run Simulation" to see your retirement projections.
              </Alert>
            )}
          </VStack>
        </SimpleGrid>

        {/* Disclaimer */}
        <Text fontSize="xs" color="gray.400" textAlign="center" pt={4}>
          This retirement planner uses Monte Carlo simulation for educational purposes only.
          Results are hypothetical and do not guarantee future performance. Consult a financial
          advisor for personalized advice.
        </Text>
      </VStack>

      {/* Modals */}
      <LifeEventPresetPicker
        isOpen={presetPicker.isOpen}
        onClose={presetPicker.onClose}
        onSelectPreset={handleAddPreset}
        isLoading={addPresetMutation.isPending}
      />

      <LifeEventEditor
        isOpen={eventEditor.isOpen}
        onClose={() => {
          eventEditor.onClose();
          setEditingEvent(null);
        }}
        onSave={handleSaveEvent}
        existingEvent={editingEvent}
        isLoading={addLifeEventMutation.isPending || updateLifeEventMutation.isPending}
      />
    </Container>
  );
}
