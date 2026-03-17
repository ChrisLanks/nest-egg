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
  AlertDescription,
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  AlertIcon,
  AlertTitle,
  Badge,
  Box,
  Button,
  Checkbox,
  Collapse,
  Container,
  HStack,
  IconButton,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Radio,
  RadioGroup,
  SimpleGrid,
  Spinner,
  Tab,
  TabList,
  Tabs,
  Text,
  Tooltip,
  useColorModeValue,
  useDisclosure,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FiArchive, FiEdit2, FiRotateCcw, FiUsers, FiX } from "react-icons/fi";
import { useQueryClient } from "@tanstack/react-query";
import api from "../../../services/api";
import { useUserView } from "../../../contexts/UserViewContext";
import { AccountDataSummary } from "../components/AccountDataSummary";
import { HealthcareEstimator } from "../components/HealthcareEstimator";
import { LifeEventEditor } from "../components/LifeEventEditor";
import { LifeEventPresetPicker } from "../components/LifeEventPresetPicker";
import { LifeEventTimeline } from "../components/LifeEventTimeline";
import { RetirementFanChart } from "../components/RetirementFanChart";
import { RetirementScoreGauge } from "../components/RetirementScoreGauge";
import { ScenarioComparisonView } from "../components/ScenarioComparisonView";
import { ScenarioPanel } from "../components/ScenarioPanel";
import { SocialSecurityEstimator } from "../components/SocialSecurityEstimator";
import { WithdrawalStrategyComparison } from "../components/WithdrawalStrategyComparison";
import HelpHint from "../../../components/HelpHint";
import { helpContent } from "../../../constants/helpContent";
import {
  useAddLifeEvent,
  useAddLifeEventFromPreset,
  useArchiveScenario,
  useCreateDefaultScenario,
  useCreateScenario,
  useDeleteLifeEvent,
  useDeleteScenario,
  useDuplicateScenario,
  useRefreshHouseholdHash,
  useRetirementScenario,
  useRetirementScenarios,
  useRunSimulation,
  useScenarioComparison,
  useSimulationResults,
  useUnarchiveScenario,
  useUpdateLifeEvent,
  useUpdateScenario,
} from "../hooks/useRetirementScenarios";
import type {
  LifeEvent,
  LifeEventCreate,
  RetirementScenarioCreate,
  RetirementScenarioSummary,
  ScenarioComparisonItem,
  WithdrawalComparison,
} from "../types/retirement";

export function RetirementPage() {
  const toast = useToast();
  const cardBg = useColorModeValue("white", "gray.800");
  const {
    isCombinedView,
    isOtherUserView,
    selectedUserId,
    canWriteResource,
    selectedMemberIds,
    householdMembers,
  } = useUserView();
  const queryClient = useQueryClient();
  const readOnly = !canWriteResource("retirement_scenario");

  const selectedIds = selectedMemberIds;

  // Retirement is per-person: only show scenarios when exactly one member is selected
  const singleSelectedId = selectedIds.size === 1 ? [...selectedIds][0] : null;
  const filterUserId = isCombinedView ? singleSelectedId : null;
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
  // In combined view with "All" selected, still fetch (for multi-member scenarios)
  const shouldFetchScenarios = true;
  const { data: allScenarios, isLoading: scenariosLoading } =
    useRetirementScenarios(scenarioUserId, shouldFetchScenarios, true);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(
    () => {
      try {
        return localStorage.getItem("retirement-active-scenario");
      } catch {
        return null;
      }
    },
  );
  const scenarioIdRef = useRef(selectedScenarioId);

  // Fetch selected scenario detail
  const { data: scenario } = useRetirementScenario(selectedScenarioId);

  // Fetch simulation results for selected scenario
  const { data: results, isLoading: resultsLoading } =
    useSimulationResults(selectedScenarioId);

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
  const refreshHouseholdMutation = useRefreshHouseholdHash();
  const archiveMutation = useArchiveScenario();
  const unarchiveMutation = useUnarchiveScenario();
  const createScenarioMutation = useCreateScenario();

  // Split active vs archived scenarios
  const scenarios = useMemo(
    () => allScenarios?.filter((s) => !s.is_archived),
    [allScenarios],
  );
  const archivedScenarios = useMemo(
    () => allScenarios?.filter((s) => s.is_archived) ?? [],
    [allScenarios],
  );
  const [showArchived, setShowArchived] = useState(false);

  // Modal state
  const presetPicker = useDisclosure();
  const eventEditor = useDisclosure();
  const [editingEvent, setEditingEvent] = useState<LifeEvent | null>(null);
  const [comparisonData, setComparisonData] = useState<
    ScenarioComparisonItem[] | null
  >(null);
  const [showComparison, setShowComparison] = useState(false);

  // Member picker modal for multi-user scenario creation
  const memberPicker = useDisclosure();
  const [memberPickerMode, setMemberPickerMode] = useState<
    "just_me" | "select" | "all"
  >("just_me");
  const [selectedMemberIdsForCreate, setSelectedMemberIdsForCreate] = useState<
    Set<string>
  >(new Set());
  const [newScenarioName, setNewScenarioName] = useState("My Retirement Plan");

  // Tab rename state
  const [editingTabId, setEditingTabId] = useState<string | null>(null);
  const [editingTabName, setEditingTabName] = useState("");

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
        localStorage.setItem("retirement-active-scenario", selectedScenarioId);
      } catch {
        /* ignore */
      }
    }
  }, [selectedScenarioId]);

  // Reset selection when the view/user changes (global or local filter)
  /* eslint-disable react-hooks/set-state-in-effect -- intentional: sync state to prop changes */
  useEffect(() => {
    setSelectedScenarioId(null);
    setSettingsDirty(false);
  }, [scenarioUserId]);

  // Auto-select first scenario or default, and reset stale IDs
  useEffect(() => {
    if (!scenarios?.length) return;

    // If current selection exists in the fetched list, keep it
    if (
      selectedScenarioId &&
      scenarios.find((s) => s.id === selectedScenarioId)
    ) {
      return;
    }

    // Current ID is null or stale (not in DB) — pick a valid one
    const defaultScenario = scenarios.find((s) => s.is_default);
    setSelectedScenarioId(defaultScenario?.id ?? scenarios[0].id);
  }, [scenarios, selectedScenarioId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Handle creating first scenario
  const handleCreateDefault = useCallback(async () => {
    try {
      const newScenario = await createDefaultMutation.mutateAsync();
      setSelectedScenarioId(newScenario.id);
      toast({ title: "Scenario created", status: "success", duration: 2000 });
    } catch (err: any) {
      toast({
        title: "Failed to create scenario",
        description:
          err?.response?.data?.detail ||
          "Please set your birthdate in preferences.",
        status: "error",
        duration: 4000,
      });
    }
  }, [createDefaultMutation, toast]);

  // Handle scenario update
  const handleUpdate = useCallback(
    (updates: Record<string, unknown>) => {
      if (!selectedScenarioId) return;
      updateMutation
        .mutateAsync({ id: selectedScenarioId, updates })
        .then(() => {
          queryClient.invalidateQueries({ queryKey: ["retirement-scenarios"] });
        })
        .catch((err: any) => {
          toast({
            title: "Failed to update scenario",
            description: err?.response?.data?.detail || "An error occurred.",
            status: "error",
            duration: 3000,
          });
        });
      setSettingsDirty(true);
    },
    [selectedScenarioId, updateMutation, queryClient, toast],
  );

  // Handle tab rename
  const handleTabDoubleClick = useCallback(
    (scenarioId: string, currentName: string) => {
      setEditingTabId(scenarioId);
      setEditingTabName(currentName);
    },
    [],
  );

  const handleTabRenameSubmit = useCallback(() => {
    if (editingTabId && editingTabName.trim()) {
      updateMutation.mutate({
        id: editingTabId,
        updates: { name: editingTabName.trim() },
      });
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
      toast({
        title: "Simulation complete",
        status: "success",
        duration: 2000,
      });
    } catch (err: any) {
      toast({
        title: "Simulation failed",
        description: err?.response?.data?.detail || "An error occurred.",
        status: "error",
        duration: 4000,
      });
    }
  }, [selectedScenarioId, simulateMutation, toast]);

  // Handle refreshing household hash and re-running simulation
  const handleRefreshHousehold = useCallback(async () => {
    if (!selectedScenarioId) return;
    try {
      await refreshHouseholdMutation.mutateAsync(selectedScenarioId);
      await simulateMutation.mutateAsync(selectedScenarioId);
      setSettingsDirty(false);
      toast({
        title: "Household updated and simulation complete",
        status: "success",
        duration: 2000,
      });
    } catch (err: any) {
      toast({
        title: "Failed to refresh household",
        description: err?.response?.data?.detail || "An error occurred.",
        status: "error",
        duration: 4000,
      });
    }
  }, [selectedScenarioId, refreshHouseholdMutation, simulateMutation, toast]);

  // Auto-run simulation (used after life event changes to update chart immediately)
  const autoSimulate = useCallback(() => {
    if (!selectedScenarioId) return;
    simulateMutation
      .mutateAsync(selectedScenarioId)
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
    [scenarios],
  );

  // Handle duplicate
  const handleDuplicate = useCallback(async () => {
    if (!selectedScenarioId) return;
    try {
      const dup = await duplicateMutation.mutateAsync({
        id: selectedScenarioId,
      });
      setSelectedScenarioId(dup.id);
      toast({
        title: "Scenario duplicated",
        status: "success",
        duration: 2000,
      });
    } catch {
      toast({ title: "Failed to duplicate", status: "error", duration: 3000 });
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
        try {
          localStorage.removeItem("retirement-active-scenario");
        } catch {
          /* ignore */
        }
      }
      toast({ title: "Scenario deleted", status: "success", duration: 2000 });
    } catch {
      toast({
        title: "Failed to delete scenario",
        status: "error",
        duration: 3000,
      });
    }
  }, [pendingDeleteId, deleteScenarioMutation, selectedScenarioId, toast]);

  // Handle compare
  const handleCompare = useCallback(async () => {
    if (!scenarios || scenarios.length < 2) {
      toast({
        title: "Need at least 2 scenarios to compare",
        status: "warning",
        duration: 3000,
      });
      return;
    }
    try {
      const ids = scenarios.slice(0, 3).map((s) => s.id);
      const data = await comparisonMutation.mutateAsync(ids);
      setComparisonData(data);
      setShowComparison(true);
    } catch (err: any) {
      toast({
        title: "Comparison failed",
        description:
          err?.response?.data?.detail ||
          "Run simulations on all scenarios first.",
        status: "error",
        duration: 4000,
      });
    }
  }, [scenarios, comparisonMutation, toast]);

  // Life event handlers
  const handleAddPreset = useCallback(
    async (presetKey: string) => {
      if (!selectedScenarioId) return;
      try {
        await addPresetMutation.mutateAsync({
          scenarioId: selectedScenarioId,
          presetKey,
        });
        presetPicker.onClose();
        toast({ title: "Life event added", status: "success", duration: 2000 });
        autoSimulate();
      } catch (err: any) {
        toast({
          title: "Failed to add event",
          description: err?.response?.data?.detail || "An error occurred.",
          status: "error",
          duration: 3000,
        });
      }
    },
    [selectedScenarioId, addPresetMutation, presetPicker, toast, autoSimulate],
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
        toast({
          title: editingEvent ? "Event updated" : "Event added",
          status: "success",
          duration: 2000,
        });
        autoSimulate();
      } catch (err: any) {
        toast({
          title: "Failed to save event",
          description: err?.response?.data?.detail || "An error occurred.",
          status: "error",
          duration: 3000,
        });
      }
    },
    [
      selectedScenarioId,
      editingEvent,
      addLifeEventMutation,
      updateLifeEventMutation,
      eventEditor,
      toast,
      autoSimulate,
    ],
  );

  const handleEditEvent = useCallback(
    (event: LifeEvent) => {
      setEditingEvent(event);
      eventEditor.onOpen();
    },
    [eventEditor],
  );

  const handleDeleteEvent = useCallback(
    async (eventId: string) => {
      try {
        await deleteLifeEventMutation.mutateAsync(eventId);
        toast({ title: "Event removed", status: "success", duration: 2000 });
        autoSimulate();
      } catch {
        toast({
          title: "Failed to delete event",
          status: "error",
          duration: 3000,
        });
      }
    },
    [deleteLifeEventMutation, toast, autoSimulate],
  );

  // Handle creating a scenario with member selection
  const handleOpenMemberPicker = useCallback(() => {
    setMemberPickerMode("just_me");
    setSelectedMemberIdsForCreate(new Set());
    setNewScenarioName("My Retirement Plan");
    memberPicker.onOpen();
  }, [memberPicker]);

  const handleCreateWithMembers = useCallback(async () => {
    const payload: RetirementScenarioCreate = {
      name: newScenarioName.trim() || "My Retirement Plan",
      retirement_age: 67,
      annual_spending_retirement: 60000,
    };

    if (memberPickerMode === "all") {
      payload.include_all_members = true;
    } else if (
      memberPickerMode === "select" &&
      selectedMemberIdsForCreate.size >= 2
    ) {
      payload.member_ids = [...selectedMemberIdsForCreate];
    }

    try {
      const newScenario = await createScenarioMutation.mutateAsync(payload);
      setSelectedScenarioId(newScenario.id);
      memberPicker.onClose();
      toast({ title: "Scenario created", status: "success", duration: 2000 });
    } catch (err: any) {
      toast({
        title: "Failed to create scenario",
        description:
          err?.response?.data?.detail ||
          "Please set your birthdate in preferences.",
        status: "error",
        duration: 4000,
      });
    }
  }, [
    newScenarioName,
    memberPickerMode,
    selectedMemberIdsForCreate,
    createScenarioMutation,
    memberPicker,
    toast,
  ]);

  // Handle archive/unarchive
  const handleArchive = useCallback(
    async (scenarioId: string) => {
      try {
        await archiveMutation.mutateAsync(scenarioId);
        if (scenarioId === selectedScenarioId) {
          setSelectedScenarioId(null);
        }
        toast({
          title: "Scenario archived",
          status: "success",
          duration: 2000,
        });
      } catch {
        toast({
          title: "Failed to archive",
          status: "error",
          duration: 3000,
        });
      }
    },
    [archiveMutation, selectedScenarioId, toast],
  );

  const handleUnarchive = useCallback(
    async (scenarioId: string) => {
      try {
        await unarchiveMutation.mutateAsync(scenarioId);
        toast({
          title: "Scenario restored",
          status: "success",
          duration: 2000,
        });
      } catch (err: any) {
        toast({
          title: "Failed to restore",
          description:
            err?.response?.data?.detail || "No active members remain.",
          status: "error",
          duration: 4000,
        });
      }
    },
    [unarchiveMutation, toast],
  );

  const handleSsClaimingAgeChange = useCallback(
    (age: number) => {
      handleUpdate({ social_security_start_age: age });
    },
    [handleUpdate],
  );

  // CSV export
  const handleExportCsv = useCallback(async () => {
    if (!selectedScenarioId) return;
    try {
      const response = await api.get(
        `/retirement/scenarios/${selectedScenarioId}/export-csv`,
        { responseType: "blob" },
      );
      const blob = new Blob([response.data], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `retirement_projections.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast({ title: "Export failed", status: "error", duration: 3000 });
    }
  }, [selectedScenarioId, toast]);

  const selectedTabIndex =
    scenarios?.findIndex((s) => s.id === selectedScenarioId) ?? 0;

  // Parse withdrawal comparison from results
  const withdrawalComparison: WithdrawalComparison | null =
    results?.withdrawal_comparison as WithdrawalComparison | null;

  // In combined view with "All" selected, show household-wide and multi-member scenarios
  // or prompt to create one
  if (isCombinedView && !filterUserId) {
    // Filter to only show multi-member scenarios (include_all_members or household_member_ids)
    const multiMemberScenarios = allScenarios?.filter(
      (s) =>
        !s.is_archived &&
        (s.include_all_members ||
          (s.household_member_ids && s.household_member_ids.length > 1)),
    );
    const archivedMultiMember = allScenarios?.filter(
      (s) =>
        s.is_archived &&
        (s.include_all_members ||
          (s.household_member_ids && s.household_member_ids.length > 1)),
    );

    if (
      !scenariosLoading &&
      (!multiMemberScenarios || multiMemberScenarios.length === 0)
    ) {
      return (
        <Container maxW="container.xl" py={8}>
          <VStack spacing={6} align="stretch">
            <VStack spacing={6} textAlign="center" py={16}>
              <Text fontSize="2xl" fontWeight="bold">
                Retirement Planner
              </Text>
              <Text color="gray.500" maxW="md">
                Create a household retirement plan that combines accounts from
                multiple members, or select a single member above to view their
                individual scenarios.
              </Text>
              {!readOnly && householdMembers.length >= 2 && (
                <Button
                  colorScheme="blue"
                  size="lg"
                  onClick={handleOpenMemberPicker}
                >
                  Create Household Plan
                </Button>
              )}
              {archivedMultiMember && archivedMultiMember.length > 0 && (
                <Box w="full" maxW="md">
                  <Button
                    size="sm"
                    variant="ghost"
                    leftIcon={<FiArchive />}
                    onClick={() => setShowArchived(!showArchived)}
                    mb={2}
                  >
                    {archivedMultiMember.length} archived scenario
                    {archivedMultiMember.length > 1 ? "s" : ""}
                  </Button>
                  <Collapse in={showArchived}>
                    <VStack spacing={2} align="stretch">
                      {archivedMultiMember.map((s) => (
                        <HStack
                          key={s.id}
                          p={3}
                          bg={cardBg}
                          borderRadius="md"
                          justify="space-between"
                        >
                          <Text fontSize="sm" color="gray.500">
                            {s.name}
                          </Text>
                          {!readOnly && (
                            <Button
                              size="xs"
                              leftIcon={<FiRotateCcw />}
                              onClick={() => handleUnarchive(s.id)}
                              isLoading={unarchiveMutation.isPending}
                            >
                              Restore
                            </Button>
                          )}
                        </HStack>
                      ))}
                    </VStack>
                  </Collapse>
                </Box>
              )}
            </VStack>
          </VStack>
        </Container>
      );
    }
    // If there are multi-member scenarios, fall through to the normal rendering
    // but we need to set scenarios to the multi-member subset
  }

  // Empty state: no scenarios for the current view
  if (!scenariosLoading && (!scenarios || scenarios.length === 0)) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={6} align="stretch">
          <VStack spacing={6} textAlign="center" py={16}>
            <Text fontSize="2xl" fontWeight="bold">
              Retirement Planner
            </Text>
            {filterUserId || isOtherUserView ? (
              <Text color="gray.500" maxW="md">
                {(() => {
                  if (isOtherUserView && selectedUserId) {
                    const member = householdMembers.find(
                      (m) => m.id === selectedUserId,
                    );
                    const name =
                      member?.display_name || member?.first_name || "This user";
                    return `${name} doesn't have any retirement scenarios yet.`;
                  }
                  const member = householdMembers.find(
                    (m) => m.id === filterUserId,
                  );
                  const name =
                    member?.display_name || member?.first_name || "This member";
                  return `${name} doesn't have any retirement scenarios yet.`;
                })()}
              </Text>
            ) : (
              <>
                <Text color="gray.500" maxW="md">
                  Plan your retirement by modeling different scenarios with
                  Monte Carlo simulation. See how different retirement ages,
                  spending levels, and life events affect your financial future.
                </Text>
                <HStack spacing={3}>
                  <Button
                    colorScheme="blue"
                    size="lg"
                    onClick={handleCreateDefault}
                    isLoading={createDefaultMutation.isPending}
                    loadingText="Setting up..."
                  >
                    Create Your First Scenario
                  </Button>
                  {householdMembers.length >= 2 && (
                    <Button
                      size="lg"
                      variant="outline"
                      colorScheme="blue"
                      leftIcon={<FiUsers />}
                      onClick={handleOpenMemberPicker}
                    >
                      Household Plan
                    </Button>
                  )}
                </HStack>
                <Alert status="info" borderRadius="md" maxW="md">
                  <AlertIcon />
                  Make sure your birthdate is set in Preferences for accurate
                  projections.
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
            <HelpHint hint={helpContent.retirement.monteCarlo} />
          </Text>
          <HStack spacing={2}>
            {!readOnly && householdMembers.length >= 2 && (
              <Button
                size="sm"
                variant="outline"
                colorScheme="purple"
                leftIcon={<FiUsers />}
                onClick={handleOpenMemberPicker}
              >
                New Plan
              </Button>
            )}
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
              <Button size="sm" variant="outline" onClick={handleExportCsv}>
                Export CSV
              </Button>
            )}
            {scenarios && scenarios.length >= 2 && (
              <Button
                size="sm"
                variant={showComparison ? "solid" : "outline"}
                colorScheme="purple"
                onClick={() =>
                  showComparison ? setShowComparison(false) : handleCompare()
                }
                isLoading={comparisonMutation.isPending}
              >
                {showComparison ? "Hide Comparison" : "Compare Scenarios"}
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

        {/* Stale household warning */}
        {scenario?.is_stale && (
          <Alert status="warning" borderRadius="md">
            <AlertIcon />
            <Box flex="1">
              <AlertTitle>Household membership has changed</AlertTitle>
              <AlertDescription>
                This scenario was created with a different set of household
                members. Results may be inaccurate.
              </AlertDescription>
            </Box>
            <Button
              size="sm"
              onClick={handleRefreshHousehold}
              isLoading={refreshHouseholdMutation.isPending}
            >
              Recalculate
            </Button>
          </Alert>
        )}

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
                <Tab key={s.id} px={3} py={2}>
                  {editingTabId === s.id ? (
                    <Input
                      size="xs"
                      value={editingTabName}
                      onChange={(e) => setEditingTabName(e.target.value)}
                      onBlur={handleTabRenameSubmit}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleTabRenameSubmit();
                        if (e.key === "Escape") handleTabRenameCancel();
                      }}
                      autoFocus
                      width="auto"
                      minW="60px"
                      maxW="200px"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <HStack spacing={1}>
                      {/* Multi-member badge */}
                      {(s.include_all_members ||
                        (s.household_member_ids &&
                          s.household_member_ids.length > 1)) && (
                        <Tooltip
                          label={
                            s.include_all_members
                              ? "All household members"
                              : `${s.household_member_ids?.length} members`
                          }
                        >
                          <Badge
                            colorScheme="purple"
                            variant="subtle"
                            fontSize="9px"
                            px={1}
                          >
                            <HStack spacing={0.5}>
                              <FiUsers size={9} />
                              <Text>
                                {s.include_all_members
                                  ? "All"
                                  : s.household_member_ids?.length}
                              </Text>
                            </HStack>
                          </Badge>
                        </Tooltip>
                      )}
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
                          {(s.include_all_members ||
                            (s.household_member_ids &&
                              s.household_member_ids.length > 1)) && (
                            <IconButton
                              aria-label="Archive scenario"
                              icon={<FiArchive />}
                              size="xs"
                              variant="ghost"
                              minW="auto"
                              h="auto"
                              p={0.5}
                              fontSize="10px"
                              opacity={0.5}
                              _hover={{ opacity: 1, color: "orange.400" }}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleArchive(s.id);
                              }}
                            />
                          )}
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
                            _hover={{ opacity: 1, color: "red.400" }}
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
            socialSecurityStartAge={
              scenario?.social_security_start_age ?? undefined
            }
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
            <Button
              size="sm"
              variant="outline"
              colorScheme="blue"
              onClick={presetPicker.onOpen}
            >
              + Add Life Event
              <HelpHint hint={helpContent.retirement.lifeEvents} />
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
              colorScheme={settingsDirty ? "orange" : "blue"}
              size="lg"
              onClick={handleSimulate}
              isLoading={simulateMutation.isPending}
              loadingText="Running Simulation..."
              isDisabled={!selectedScenarioId || readOnly}
              w="100%"
            >
              {settingsDirty ? "Re-run Simulation" : "Run Simulation"}
            </Button>
            {settingsDirty && !readOnly && (
              <Text fontSize="xs" color="orange.400" textAlign="center">
                Settings have changed since your last simulation. Click above to
                update results.
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
              onMedicalInflationChange={(rate) =>
                handleUpdate({ medical_inflation_rate: rate })
              }
              onRetirementIncomeChange={(income) =>
                handleUpdate({ annual_spending_retirement: income })
              }
              pre65Override={scenario?.healthcare_pre65_override ?? null}
              medicareOverride={scenario?.healthcare_medicare_override ?? null}
              ltcOverride={scenario?.healthcare_ltc_override ?? null}
              onHealthcareOverridesChange={(overrides) =>
                handleUpdate(overrides)
              }
              readOnly={readOnly}
            />

            {/* Withdrawal Strategy Comparison */}
            {withdrawalComparison && (
              <WithdrawalStrategyComparison
                comparison={withdrawalComparison}
                withdrawalRate={scenario?.withdrawal_rate ?? 4}
                selectedStrategy={scenario?.withdrawal_strategy}
                onStrategySelect={(strategy) =>
                  handleUpdate({ withdrawal_strategy: strategy })
                }
                readOnly={readOnly}
              />
            )}

            {/* Results summary */}
            {results && (
              <Box bg={cardBg} p={5} borderRadius="xl" shadow="sm">
                <Text fontSize="lg" fontWeight="semibold" mb={3}>
                  Simulation Summary
                  <HelpHint hint={helpContent.retirement.readinessScore} />
                </Text>
                <VStack spacing={2} align="stretch" fontSize="sm">
                  <HStack justify="space-between">
                    <Text color="gray.500">Success Rate</Text>
                    <Text fontWeight="bold">
                      {results.success_rate.toFixed(1)}%
                    </Text>
                  </HStack>
                  {results.median_portfolio_at_retirement && (
                    <HStack justify="space-between">
                      <Text color="gray.500">Portfolio at Retirement</Text>
                      <Text fontWeight="bold">
                        $
                        {(
                          results.median_portfolio_at_retirement / 1000000
                        ).toFixed(2)}
                        M
                      </Text>
                    </HStack>
                  )}
                  {results.median_portfolio_at_end !== null && (
                    <HStack justify="space-between">
                      <Text color="gray.500">Portfolio at End</Text>
                      <Text fontWeight="bold">
                        $
                        {(results.median_portfolio_at_end / 1000000).toFixed(2)}
                        M
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
                      <Text>
                        {(results.compute_time_ms / 1000).toFixed(1)}s
                      </Text>
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

        {/* Archived Scenarios */}
        {archivedScenarios.length > 0 && (
          <Box>
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<FiArchive />}
              onClick={() => setShowArchived(!showArchived)}
              color="gray.500"
            >
              {archivedScenarios.length} archived scenario
              {archivedScenarios.length > 1 ? "s" : ""}
            </Button>
            <Collapse in={showArchived}>
              <VStack spacing={2} align="stretch" mt={2}>
                {archivedScenarios.map((s) => (
                  <HStack
                    key={s.id}
                    p={3}
                    bg={cardBg}
                    borderRadius="md"
                    justify="space-between"
                    opacity={0.7}
                  >
                    <VStack align="start" spacing={0}>
                      <Text fontSize="sm" fontWeight="medium">
                        {s.name}
                      </Text>
                    </VStack>
                    {!readOnly && (
                      <Button
                        size="xs"
                        leftIcon={<FiRotateCcw />}
                        onClick={() => handleUnarchive(s.id)}
                        isLoading={unarchiveMutation.isPending}
                      >
                        Restore
                      </Button>
                    )}
                  </HStack>
                ))}
              </VStack>
            </Collapse>
          </Box>
        )}

        {/* Disclaimer */}
        <Text fontSize="xs" color="gray.400" textAlign="center" pt={4}>
          This retirement planner uses Monte Carlo simulation for educational
          purposes only. Results are hypothetical and do not guarantee future
          performance. Consult a financial advisor for personalized advice.
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
        isLoading={
          addLifeEventMutation.isPending || updateLifeEventMutation.isPending
        }
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
              Are you sure you want to delete this retirement scenario? This
              action cannot be undone.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button
                ref={deleteDialogCancelRef}
                onClick={() => setPendingDeleteId(null)}
              >
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

      {/* Member Picker Modal */}
      <Modal isOpen={memberPicker.isOpen} onClose={memberPicker.onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create Retirement Plan</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Box>
                <Text fontSize="sm" fontWeight="medium" mb={2}>
                  Plan Name
                </Text>
                <Input
                  value={newScenarioName}
                  onChange={(e) => setNewScenarioName(e.target.value)}
                  placeholder="My Retirement Plan"
                />
              </Box>

              <Box>
                <Text fontSize="sm" fontWeight="medium" mb={2}>
                  Who is this plan for?
                </Text>
                <RadioGroup
                  value={memberPickerMode}
                  onChange={(val) =>
                    setMemberPickerMode(val as "just_me" | "select" | "all")
                  }
                >
                  <VStack align="start" spacing={2}>
                    <Radio value="just_me">Just me</Radio>
                    <Radio value="all">All household members</Radio>
                    <Radio value="select">Select specific members</Radio>
                  </VStack>
                </RadioGroup>
              </Box>

              {memberPickerMode === "select" && (
                <VStack align="stretch" spacing={2} pl={6}>
                  {householdMembers.map((m) => (
                    <Checkbox
                      key={m.id}
                      isChecked={selectedMemberIdsForCreate.has(m.id)}
                      onChange={(e) => {
                        const next = new Set(selectedMemberIdsForCreate);
                        if (e.target.checked) {
                          next.add(m.id);
                        } else {
                          next.delete(m.id);
                        }
                        setSelectedMemberIdsForCreate(next);
                      }}
                    >
                      {m.display_name || m.first_name || m.email}
                    </Checkbox>
                  ))}
                  {selectedMemberIdsForCreate.size < 2 && (
                    <Text fontSize="xs" color="orange.400">
                      Select at least 2 members for a multi-person plan.
                    </Text>
                  )}
                </VStack>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={memberPicker.onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleCreateWithMembers}
              isLoading={createScenarioMutation.isPending}
              isDisabled={
                memberPickerMode === "select" &&
                selectedMemberIdsForCreate.size < 2
              }
            >
              Create Plan
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
}
