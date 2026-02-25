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
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  AlertIcon,
  Box,
  Button,
  ButtonGroup,
  Container,
  HStack,
  IconButton,
  Input,
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
import { FiEdit2, FiX } from 'react-icons/fi';
import api from '../../../services/api';
import { useUserView } from '../../../contexts/UserViewContext';
import { useHouseholdMembers } from '../../../hooks/useHouseholdMembers';
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
  useDeleteScenario,
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
  const accent = useColorModeValue('blue', 'cyan');
  const { isCombinedView, isSelfView, isOtherUserView, selectedUserId, canWriteResource } = useUserView();
  const readOnly = !canWriteResource('retirement_scenario');
  const { data: householdMembers = [] } = useHouseholdMembers();
  const [filterUserId, setFilterUserId] = useState<string | null>(null);
  const showMemberFilter = isCombinedView && householdMembers.length > 1;
  const tabsRef = useRef<HTMLDivElement>(null);

  // Track whether settings changed since last simulation
  const [settingsDirty, setSettingsDirty] = useState(false);

  // Derive effective userId for fetching scenarios:
  // - Non-combined view (Self / Other user): use the global selectedUserId
  // - Combined view with member filter: use that member's ID
  // - Combined view without filter ("All"): no fetch — retirement plans are per-person
  const scenarioUserId = !isCombinedView
    ? (selectedUserId ?? undefined)
    : (filterUserId ?? undefined);
  // In combined view with "All" selected, don't fetch any scenarios
  const shouldFetchScenarios = !isCombinedView || !!filterUserId;
  const { data: scenarios, isLoading: scenariosLoading } = useRetirementScenarios(scenarioUserId, shouldFetchScenarios);
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
  const deleteScenarioMutation = useDeleteScenario();
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

  // Tab rename state
  const [editingTabId, setEditingTabId] = useState<string | null>(null);
  const [editingTabName, setEditingTabName] = useState('');

  // Delete confirmation state
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const deleteDialogCancelRef = useRef<HTMLButtonElement>(null);

  // Scroll to top after first scenario data loads (not on mount, which fires before content renders)
  const isInitialLoad = useRef(true);
  useEffect(() => {
    if (isInitialLoad.current && scenario) {
      isInitialLoad.current = false;
      // Double rAF ensures the DOM has fully painted after data-driven render
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.scrollTo(0, 0);
        });
      });
    }
  }, [scenario]);

  // Persist selected scenario to localStorage
  useEffect(() => {
    scenarioIdRef.current = selectedScenarioId;
    if (selectedScenarioId) {
      try {
        localStorage.setItem('retirement-active-scenario', selectedScenarioId);
      } catch { /* ignore */ }
    }
  }, [selectedScenarioId]);

  // Reset selection when the view/user changes (global or local filter)
  useEffect(() => {
    setSelectedScenarioId(null);
    setSettingsDirty(false);
  }, [scenarioUserId]);

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
      setSettingsDirty(true);
    },
    [selectedScenarioId, updateMutation]
  );

  // Handle tab rename
  const handleTabDoubleClick = useCallback(
    (scenarioId: string, currentName: string) => {
      setEditingTabId(scenarioId);
      setEditingTabName(currentName);
    },
    []
  );

  const handleTabRenameSubmit = useCallback(() => {
    if (editingTabId && editingTabName.trim()) {
      updateMutation.mutate({ id: editingTabId, updates: { name: editingTabName.trim() } });
    }
    setEditingTabId(null);
  }, [editingTabId, editingTabName, updateMutation]);

  const handleTabRenameCancel = useCallback(() => {
    setEditingTabId(null);
  }, []);

  // Handle running simulation
  const handleSimulate = useCallback(async () => {
    if (!selectedScenarioId) return;
    try {
      await simulateMutation.mutateAsync(selectedScenarioId);
      setSettingsDirty(false);
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

  // Auto-run simulation (used after life event changes to update chart immediately)
  const autoSimulate = useCallback(() => {
    if (!selectedScenarioId) return;
    simulateMutation.mutateAsync(selectedScenarioId)
      .then(() => setSettingsDirty(false))
      .catch(() => {}); // Swallow errors for auto-simulate
  }, [selectedScenarioId, simulateMutation]);

  // Handle tab selection
  const handleTabChange = useCallback(
    (index: number) => {
      if (scenarios && index < scenarios.length) {
        setSelectedScenarioId(scenarios[index].id);
        setShowComparison(false);
        setSettingsDirty(false);
        window.scrollTo(0, 0);
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

  // Handle delete scenario — opens confirmation dialog
  const handleRequestDelete = useCallback((scenarioId: string) => {
    setPendingDeleteId(scenarioId);
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDeleteId) return;
    const scenarioId = pendingDeleteId;
    setPendingDeleteId(null);
    try {
      await deleteScenarioMutation.mutateAsync(scenarioId);
      if (scenarioId === selectedScenarioId) {
        setSelectedScenarioId(null);
        try { localStorage.removeItem('retirement-active-scenario'); } catch { /* ignore */ }
      }
      toast({ title: 'Scenario deleted', status: 'success', duration: 2000 });
    } catch {
      toast({ title: 'Failed to delete scenario', status: 'error', duration: 3000 });
    }
  }, [pendingDeleteId, deleteScenarioMutation, selectedScenarioId, toast]);

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
        autoSimulate();
      } catch (err: any) {
        toast({
          title: 'Failed to add event',
          description: err?.response?.data?.detail || 'An error occurred.',
          status: 'error',
          duration: 3000,
        });
      }
    },
    [selectedScenarioId, addPresetMutation, presetPicker, toast, autoSimulate]
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
        autoSimulate();
      } catch (err: any) {
        toast({
          title: 'Failed to save event',
          description: err?.response?.data?.detail || 'An error occurred.',
          status: 'error',
          duration: 3000,
        });
      }
    },
    [selectedScenarioId, editingEvent, addLifeEventMutation, updateLifeEventMutation, eventEditor, toast, autoSimulate]
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
        autoSimulate();
      } catch {
        toast({ title: 'Failed to delete event', status: 'error', duration: 3000 });
      }
    },
    [deleteLifeEventMutation, toast, autoSimulate]
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

  // Combined "All" view: retirement plans are per-person, prompt to select a member
  if (isCombinedView && !filterUserId) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={6} align="stretch">
          {showMemberFilter && (
            <HStack spacing={2}>
              <Text fontSize="sm" fontWeight="medium" color="gray.500">
                Member:
              </Text>
              <ButtonGroup size="sm" isAttached variant="outline">
                <Button colorScheme={accent} variant="solid">
                  All
                </Button>
                {householdMembers.map((member) => (
                  <Button
                    key={member.id}
                    variant="outline"
                    onClick={() => setFilterUserId(member.id)}
                  >
                    {member.display_name || member.first_name || member.email.split('@')[0]}
                  </Button>
                ))}
              </ButtonGroup>
            </HStack>
          )}
          <VStack spacing={6} textAlign="center" py={16}>
            <Text fontSize="2xl" fontWeight="bold">
              Retirement Planner
            </Text>
            <Text color="gray.500" maxW="md">
              Retirement plans are personal to each household member. Select a member above
              to view or create their retirement scenarios.
            </Text>
          </VStack>
        </VStack>
      </Container>
    );
  }

  // Empty state: no scenarios for the current view
  if (!scenariosLoading && (!scenarios || scenarios.length === 0)) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={6} align="stretch">
          {/* Member filter — always visible in combined household view */}
          {showMemberFilter && (
            <HStack spacing={2}>
              <Text fontSize="sm" fontWeight="medium" color="gray.500">
                Member:
              </Text>
              <ButtonGroup size="sm" isAttached variant="outline">
                <Button
                  variant="outline"
                  onClick={() => setFilterUserId(null)}
                >
                  All
                </Button>
                {householdMembers.map((member) => (
                  <Button
                    key={member.id}
                    colorScheme={filterUserId === member.id ? accent : 'gray'}
                    variant={filterUserId === member.id ? 'solid' : 'outline'}
                    onClick={() => setFilterUserId(member.id)}
                  >
                    {member.display_name || member.first_name || member.email.split('@')[0]}
                  </Button>
                ))}
              </ButtonGroup>
            </HStack>
          )}
          <VStack spacing={6} textAlign="center" py={16}>
            <Text fontSize="2xl" fontWeight="bold">
              Retirement Planner
            </Text>
            {filterUserId || isOtherUserView ? (
              <Text color="gray.500" maxW="md">
                {(() => {
                  if (isOtherUserView && selectedUserId) {
                    const member = householdMembers.find((m) => m.id === selectedUserId);
                    const name = member?.display_name || member?.first_name || 'This user';
                    return `${name} doesn't have any retirement scenarios yet.`;
                  }
                  const member = householdMembers.find((m) => m.id === filterUserId);
                  const name = member?.display_name || member?.first_name || 'This member';
                  return `${name} doesn't have any retirement scenarios yet.`;
                })()}
              </Text>
            ) : (
              <>
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
              </>
            )}
          </VStack>
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
        <HStack justify="space-between" align="center" wrap="wrap" gap={2}>
          <Text fontSize="2xl" fontWeight="bold">
            Retirement Planner
          </Text>
          <HStack spacing={2}>
            {!readOnly && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleDuplicate}
                isLoading={duplicateMutation.isPending}
                isDisabled={!selectedScenarioId}
              >
                Duplicate
              </Button>
            )}
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

        {/* Member filter */}
        {showMemberFilter && (
          <HStack spacing={2}>
            <Text fontSize="sm" fontWeight="medium" color="gray.500">
              Member:
            </Text>
            <ButtonGroup size="sm" isAttached variant="outline">
              <Button
                colorScheme={!filterUserId ? accent : 'gray'}
                variant={!filterUserId ? 'solid' : 'outline'}
                onClick={() => setFilterUserId(null)}
              >
                All
              </Button>
              {householdMembers.map((member) => (
                <Button
                  key={member.id}
                  colorScheme={filterUserId === member.id ? accent : 'gray'}
                  variant={filterUserId === member.id ? 'solid' : 'outline'}
                  onClick={() => setFilterUserId(member.id)}
                >
                  {member.display_name || member.first_name || member.email.split('@')[0]}
                </Button>
              ))}
            </ButtonGroup>
          </HStack>
        )}

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
            ref={tabsRef}
            index={selectedTabIndex >= 0 ? selectedTabIndex : 0}
            onChange={handleTabChange}
            variant="enclosed"
            size="sm"
          >
            <TabList>
              {scenarios.map((s: RetirementScenarioSummary) => (
                <Tab
                  key={s.id}
                  px={3}
                  py={2}
                >
                  {editingTabId === s.id ? (
                    <Input
                      size="xs"
                      value={editingTabName}
                      onChange={(e) => setEditingTabName(e.target.value)}
                      onBlur={handleTabRenameSubmit}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleTabRenameSubmit();
                        if (e.key === 'Escape') handleTabRenameCancel();
                      }}
                      autoFocus
                      width="auto"
                      minW="60px"
                      maxW="200px"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <HStack spacing={1}>
                      <Text as="span">
                        {s.name}
                        {s.readiness_score !== null && (
                          <Text as="span" ml={1} fontSize="xs" color="gray.500">
                            ({s.readiness_score})
                          </Text>
                        )}
                      </Text>
                      {!readOnly && (
                        <>
                          <IconButton
                            aria-label="Rename scenario"
                            icon={<FiEdit2 />}
                            size="xs"
                            variant="ghost"
                            minW="auto"
                            h="auto"
                            p={0.5}
                            fontSize="10px"
                            opacity={0.5}
                            _hover={{ opacity: 1 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleTabDoubleClick(s.id, s.name);
                            }}
                          />
                          <IconButton
                            aria-label="Delete scenario"
                            icon={<FiX />}
                            size="xs"
                            variant="ghost"
                            minW="auto"
                            h="auto"
                            p={0.5}
                            fontSize="10px"
                            opacity={0.5}
                            _hover={{ opacity: 1, color: 'red.400' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRequestDelete(s.id);
                            }}
                          />
                        </>
                      )}
                    </HStack>
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
            onEventClick={readOnly ? undefined : handleEditEvent}
            onDeleteEvent={readOnly ? undefined : handleDeleteEvent}
          />
        )}

        {/* Add Life Event Buttons */}
        {scenario && !readOnly && (
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

        {/* Run Simulation */}
        {scenario && (
          <VStack spacing={2} align="stretch">
            <Button
              colorScheme={settingsDirty ? 'orange' : 'blue'}
              size="lg"
              onClick={handleSimulate}
              isLoading={simulateMutation.isPending}
              loadingText="Running Simulation..."
              isDisabled={!selectedScenarioId || readOnly}
              w="100%"
            >
              {settingsDirty ? 'Re-run Simulation' : 'Run Simulation'}
            </Button>
            {settingsDirty && !readOnly && (
              <Text fontSize="xs" color="orange.400" textAlign="center">
                Settings have changed since your last simulation. Click above to update results.
              </Text>
            )}
          </VStack>
        )}

        {/* Two-column: Settings + Details */}
        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
          <VStack spacing={6} align="stretch">
            <ScenarioPanel
              scenario={scenario ?? null}
              onUpdate={handleUpdate}
              readOnly={readOnly}
            />

            {/* Account Data Summary */}
            <AccountDataSummary
              scenario={scenario ?? null}
              userId={scenarioUserId}
              onTaxRateChange={(changes) => handleUpdate(changes)}
              readOnly={readOnly}
            />
          </VStack>

          {/* Right column: SS, Healthcare, Withdrawal, Results */}
          <VStack spacing={4} align="stretch">
            {/* Social Security Estimator */}
            <SocialSecurityEstimator
              currentIncome={scenario?.current_annual_income}
              claimingAge={scenario?.social_security_start_age ?? 67}
              manualOverride={scenario?.social_security_monthly}
              onClaimingAgeChange={handleSsClaimingAgeChange}
              onManualOverrideChange={(amount) =>
                handleUpdate({
                  social_security_monthly: amount,
                  use_estimated_pia: amount === null,
                })
              }
              readOnly={readOnly}
            />

            {/* Healthcare Estimator */}
            <HealthcareEstimator
              retirementIncome={scenario?.annual_spending_retirement ?? 50000}
              medicalInflationRate={scenario?.medical_inflation_rate ?? 6}
              onMedicalInflationChange={(rate) => handleUpdate({ medical_inflation_rate: rate })}
              onRetirementIncomeChange={(income) => handleUpdate({ annual_spending_retirement: income })}
              pre65Override={scenario?.healthcare_pre65_override ?? null}
              medicareOverride={scenario?.healthcare_medicare_override ?? null}
              ltcOverride={scenario?.healthcare_ltc_override ?? null}
              onHealthcareOverridesChange={(overrides) => handleUpdate(overrides)}
              readOnly={readOnly}
            />

            {/* Withdrawal Strategy Comparison */}
            {withdrawalComparison && (
              <WithdrawalStrategyComparison
                comparison={withdrawalComparison}
                withdrawalRate={scenario?.withdrawal_rate ?? 4}
                selectedStrategy={scenario?.withdrawal_strategy}
                onStrategySelect={(strategy) => handleUpdate({ withdrawal_strategy: strategy })}
                readOnly={readOnly}
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

      {/* Delete scenario confirmation */}
      <AlertDialog
        isOpen={!!pendingDeleteId}
        leastDestructiveRef={deleteDialogCancelRef}
        onClose={() => setPendingDeleteId(null)}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Scenario
            </AlertDialogHeader>
            <AlertDialogBody>
              Are you sure you want to delete this retirement scenario? This action cannot be undone.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={deleteDialogCancelRef} onClick={() => setPendingDeleteId(null)}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={handleConfirmDelete}
                ml={3}
                isLoading={deleteScenarioMutation.isPending}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Container>
  );
}
