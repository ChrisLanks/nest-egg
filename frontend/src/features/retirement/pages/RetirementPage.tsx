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
import { useNavigate } from "react-router-dom";
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
  const mutedTextColor = useColorModeValue("gray.400", "gray.500");
  const {
    isCombinedView,
    isOtherUserView,
    selectedUserId,
    canWriteResource,
    selectedMemberIds,
    selectedMemberIdsKey,
    householdMembers,
    isAllSelected: contextAllSelected,
    matchesMemberFilter,
  } = useUserView();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const readOnly = !canWriteResource("retirement_scenario");

  // Derive current user's age from the shared profile cache (no extra request).
  // Social Security planning is only relevant from ~55 onwards.
  const SS_SHOW_AGE = 55;
  const userProfile = queryClient.getQueryData<{
    birthdate?: string | null;
    birth_year?: number | null;
    birth_month?: number | null;
    birth_day?: number | null;
  }>(["userProfile"]);
  const hasBirthdate = !!(userProfile?.birthdate || userProfile?.birth_year);
  const currentUserAge = useMemo(() => {
    if (userProfile?.birthdate) {
      const birth = new Date(userProfile.birthdate);
      const today = new Date();
      let age = today.getFullYear() - birth.getFullYear();
      const m = today.getMonth() - birth.getMonth();
      if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
      return age;
    }
    if (userProfile?.birth_year) {
      return new Date().getFullYear() - userProfile.birth_year;
    }
    return null;
  }, [userProfile?.birthdate, userProfile?.birth_year]);
  // Show SS estimator only when age is known AND >= 55. When age is unknown
  // (new user, no birthdate yet) we hide it — defaulting to visible would
  // show it to every new user and defeat the gate.
  const showSocialSecurity = currentUserAge !== null && currentUserAge >= SS_SHOW_AGE;

  const selectedIds = selectedMemberIds;

  // Retirement is per-person: only show scenarios when exactly one member is selected
  const singleSelectedId = selectedIds.size === 1 ? [...selectedIds][0] : null;
  const filterUserId = isCombinedView ? singleSelectedId : null;
  const isAllSelected = isCombinedView && contextAllSelected;
  const tabsRef = useRef<HTMLDivElement>(null);

  // Track whether settings changed since last simulation
  const [settingsDirty, setSettingsDirty] = useState(false);

  // Derive effective userId for fetching scenarios:
  // - Non-combined view (Self / Other user): use the global selectedUserId
  // - Combined view: fetch all org scenarios (no user filter) and filter client-side
  const scenarioUserId = !isCombinedView
    ? (selectedUserId ?? undefined)
    : undefined;
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

  // Filter scenarios based on which members are selected in the View picker.
  // A plan belongs to its creator (user_id). When all members are selected, show everything.
  // Otherwise filter by owner — even include_all_members plans belong to whoever created them.
  const filterForView = useCallback(
    (s: RetirementScenarioSummary): boolean => {
      if (!isCombinedView) return true; // non-combined: already user-scoped by API
      if (isAllSelected) return true; // all members selected — show everything
      return matchesMemberFilter(s.user_id);
    },
    [isCombinedView, isAllSelected, matchesMemberFilter],
  );

  const scenarios = useMemo(
    () => allScenarios?.filter((s) => !s.is_archived && filterForView(s)),
    [allScenarios, filterForView],
  );
  const archivedScenarios = useMemo(
    () => allScenarios?.filter((s) => s.is_archived && filterForView(s)) ?? [],
    [allScenarios, filterForView],
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

  // Edit members modal for existing scenarios
  const memberEditor = useDisclosure();
  const [editingMembersScenarioId, setEditingMembersScenarioId] = useState<
    string | null
  >(null);
  const [editMemberMode, setEditMemberMode] = useState<
    "just_me" | "select" | "all"
  >("select");
  const [editMemberIds, setEditMemberIds] = useState<Set<string>>(new Set());

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
  }, [scenarioUserId, selectedMemberIdsKey]);

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
      .catch((err: unknown) => {
        // Auto-simulate failure is non-blocking; log so it's visible in dev tools
        console.warn("[autoSimulate] simulation failed:", err);
      });
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
    setMemberPickerMode("all");
    setSelectedMemberIdsForCreate(new Set());
    setNewScenarioName("Household Retirement Plan");
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

  // Handle opening member editor for an existing scenario
  const handleOpenMemberEditor = useCallback(
    (scenarioId: string) => {
      const s = scenarios?.find((sc) => sc.id === scenarioId);
      if (!s) return;
      setEditingMembersScenarioId(scenarioId);
      if (s.include_all_members) {
        setEditMemberMode("all");
        setEditMemberIds(new Set());
      } else if (s.household_member_ids && s.household_member_ids.length > 1) {
        setEditMemberMode("select");
        setEditMemberIds(new Set(s.household_member_ids));
      } else {
        setEditMemberMode("just_me");
        setEditMemberIds(new Set());
      }
      memberEditor.onOpen();
    },
    [scenarios, memberEditor],
  );

  const handleSaveMemberEdit = useCallback(async () => {
    if (!editingMembersScenarioId) return;
    const updates: Record<string, unknown> = {};

    // If all household members are selected, treat as "all"
    const allSelected =
      editMemberMode === "select" &&
      householdMembers.length > 0 &&
      editMemberIds.size >= householdMembers.length &&
      householdMembers.every((m) => editMemberIds.has(m.id));

    if (editMemberMode === "all" || allSelected) {
      updates.include_all_members = true;
      updates.member_ids = null;
    } else if (editMemberMode === "select" && editMemberIds.size >= 2) {
      updates.include_all_members = false;
      updates.member_ids = [...editMemberIds];
    } else {
      // "just_me" or <2 selected: revert to personal
      updates.include_all_members = false;
      updates.member_ids = [];
    }

    try {
      await updateMutation.mutateAsync({
        id: editingMembersScenarioId,
        updates,
      });
      // Invalidate only the scenario list (for updated readiness scores etc.),
      // NOT results. The auto-simulate below will populate fresh results via
      // setQueryData — refetching results would race and overwrite with stale data.
      queryClient.invalidateQueries({
        predicate: (query) =>
          query.queryKey[0] === "retirement-scenarios" &&
          !query.queryKey.includes("results"),
      });
      memberEditor.onClose();
      toast({
        title: "Plan members updated",
        status: "success",
        duration: 2000,
      });
      // Auto-run simulation after member changes
      if (editingMembersScenarioId) {
        simulateMutation
          .mutateAsync(editingMembersScenarioId)
          .then(() => {
            if (editingMembersScenarioId === selectedScenarioId) {
              setSettingsDirty(false);
            }
          })
          .catch((err: unknown) => {
            console.warn("[autoSimulate] post-member-change simulation failed:", err);
          });
      }
    } catch (err: any) {
      toast({
        title: "Failed to update members",
        description: err?.response?.data?.detail || "An error occurred.",
        status: "error",
        duration: 3000,
      });
    }
  }, [
    editingMembersScenarioId,
    editMemberMode,
    editMemberIds,
    householdMembers,
    updateMutation,
    queryClient,
    memberEditor,
    toast,
    simulateMutation,
    selectedScenarioId,
    setSettingsDirty,
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

  // In combined view with "All" selected, show household-wide scenarios
  // or prompt to create one. Single-user households fall through to the
  // regular empty state so the "Create Your First Scenario" button appears.
  if (isCombinedView && isAllSelected && householdMembers.length > 1) {
    if (!scenariosLoading && (!scenarios || scenarios.length === 0)) {
      return (
        <>
          <Container maxW="container.xl" py={8}>
            <VStack spacing={6} align="stretch">
              <VStack spacing={6} textAlign="center" py={16}>
                <Text fontSize="2xl" fontWeight="bold">
                  Retirement Planner
                </Text>
                <Text color="gray.500" maxW="md">
                  Plan your retirement by modeling different scenarios with
                  Monte Carlo simulation. See how different retirement ages,
                  spending levels, and life events affect your financial future.
                </Text>
                <Text color="gray.500" maxW="md">
                  Create a household retirement plan that combines accounts from
                  multiple members, or select a single member above to view
                  their individual scenarios.
                </Text>
                {!readOnly && householdMembers.length >= 2 && (
                  <Tooltip
                    label="Create a combined retirement plan that merges all selected household members' accounts into one shared projection"
                    placement="top"
                  >
                    <Button
                      colorScheme="blue"
                      size="lg"
                      onClick={handleOpenMemberPicker}
                    >
                      Create Household Plan
                    </Button>
                  </Tooltip>
                )}
                {archivedScenarios && archivedScenarios.length > 0 && (
                  <Box w="full" maxW="md">
                    <Button
                      size="sm"
                      variant="ghost"
                      leftIcon={<FiArchive />}
                      onClick={() => setShowArchived(!showArchived)}
                      mb={2}
                    >
                      {archivedScenarios.length} archived scenario
                      {archivedScenarios.length > 1 ? "s" : ""}
                    </Button>
                    <Collapse in={showArchived}>
                      <VStack spacing={2} align="stretch">
                        {archivedScenarios.map((s) => (
                          <HStack
                            key={s.id}
                            p={3}
                            bg={cardBg}
                            borderRadius="md"
                            justify="space-between"
                          >
                            <Text fontSize="sm" color="gray.500">
                              {s.name}
                              {isCombinedView &&
                                (s.include_all_members ||
                                  (s.household_member_ids &&
                                    s.household_member_ids.length > 1)) &&
                                (() => {
                                  const owner = householdMembers.find(
                                    (m) => m.id === s.user_id,
                                  );
                                  const ownerName =
                                    owner?.display_name ?? owner?.first_name;
                                  return ownerName ? (
                                    <Text
                                      as="span"
                                      ml={1}
                                      fontSize="xs"
                                      color="gray.400"
                                    >
                                      by {ownerName}
                                    </Text>
                                  ) : null;
                                })()}
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
                      onChange={(val) => {
                        const mode = val as "just_me" | "select" | "all";
                        setMemberPickerMode(mode);
                        setNewScenarioName(
                          mode === "just_me"
                            ? "My Retirement Plan"
                            : "Household Retirement Plan",
                        );
                      }}
                    >
                      <VStack align="start" spacing={2}>
                        <Radio value="just_me">Just me</Radio>
                        <VStack align="start" spacing={0}>
                          <Radio value="all">All household members</Radio>
                          <Text fontSize="xs" color="text.muted" pl={6}>
                            Combines everyone's accounts into one shared projection
                          </Text>
                        </VStack>
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
        </>
      );
    }
    // If there are multi-member scenarios, fall through to the normal rendering
    // but we need to set scenarios to the multi-member subset
  }

  // Empty state: no scenarios for the current view
  if (!scenariosLoading && (!scenarios || scenarios.length === 0)) {
    return (
      <>
        <Container maxW="container.xl" py={8}>
          <VStack spacing={6} align="stretch">
            <VStack spacing={6} textAlign="center" py={16}>
              <Text fontSize="2xl" fontWeight="bold">
                Retirement Planner
              </Text>
              {isOtherUserView ? (
                <Text color="gray.500" maxW="md">
                  {(() => {
                    const member = householdMembers.find(
                      (m) => m.id === selectedUserId,
                    );
                    const name =
                      member?.display_name ||
                      member?.first_name ||
                      "This user";
                    return `${name} doesn't have any retirement scenarios yet.`;
                  })()}
                </Text>
              ) : isCombinedView && selectedIds.size > 1 ? (
                <Text color="gray.500" maxW="md">
                  No shared retirement plans for the selected members yet.
                  Create one to combine their accounts.
                </Text>
              ) : (
                <>
                  <Text color="gray.500" maxW="md">
                    {localStorage.getItem("nest-egg-onboarding-goal") ===
                    "retirement"
                      ? "You said you want to plan for retirement — let's build your first scenario. See when you could stop working and what you need to save to get there."
                      : "Plan your retirement by modeling different scenarios with Monte Carlo simulation. See how different retirement ages, spending levels, and life events affect your financial future."}
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
                      <Tooltip
                        label="Create a combined retirement plan that merges all selected household members' accounts into one shared projection"
                        placement="top"
                      >
                        <Button
                          size="lg"
                          variant="outline"
                          colorScheme="blue"
                          leftIcon={<FiUsers />}
                          onClick={handleOpenMemberPicker}
                        >
                          Household Plan
                        </Button>
                      </Tooltip>
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

        {/* Member Picker Modal — must be in DOM for the Household Plan button */}
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
                    onChange={(val) => {
                      const mode = val as "just_me" | "select" | "all";
                      setMemberPickerMode(mode);
                      setNewScenarioName(
                        mode === "just_me"
                          ? "My Retirement Plan"
                          : "Household Retirement Plan",
                      );
                    }}
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
      </>
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
        {/* Preemptive birthdate prompt — shown when birthdate is missing so users
            understand upfront why scenario creation will fail */}
        {!hasBirthdate && (
          <Alert status="warning" borderRadius="lg" variant="subtle">
            <AlertIcon />
            <AlertDescription>
              Add your birthdate in{" "}
              <Button
                variant="link"
                colorScheme="orange"
                size="sm"
                onClick={() => navigate("/preferences")}
              >
                Preferences
              </Button>{" "}
              to enable retirement projections.
            </AlertDescription>
          </Alert>
        )}
        {/* Multi-member banner — clarify household vs individual plans */}
        {isCombinedView && selectedIds.size > 1 && (
          <Alert status="info" borderRadius="lg" variant="subtle">
            <AlertIcon />
            <AlertDescription>
              Viewing household retirement plans. Plans are saved per person but can include household members, joint income, and shared accounts. To create or edit a specific member's plan, select them individually in the view switcher above.
            </AlertDescription>
          </Alert>
        )}
        {/* Header */}
        <HStack justify="space-between" align="center" wrap="wrap" gap={2}>
          <Text fontSize="2xl" fontWeight="bold">
            Retirement Planner
            <HelpHint hint={helpContent.retirement.monteCarlo} />
          </Text>
          <HStack spacing={2}>
            {!readOnly && householdMembers.length >= 2 && (
              <Tooltip label="Create a new retirement plan with selected household members">
                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="purple"
                  leftIcon={<FiUsers />}
                  onClick={handleOpenMemberPicker}
                >
                  New Plan
                </Button>
              </Tooltip>
            )}
            {!readOnly && (
              <Tooltip label="Copy the current scenario as a starting point for a new one">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleDuplicate}
                  isLoading={duplicateMutation.isPending}
                  isDisabled={!selectedScenarioId}
                >
                  Duplicate
                </Button>
              </Tooltip>
            )}
            {results && (
              <Tooltip label="Download projection data as a spreadsheet">
                <Button size="sm" variant="outline" onClick={handleExportCsv}>
                  Export CSV
                </Button>
              </Tooltip>
            )}
            {scenarios && scenarios.length > 0 && (
              <Tooltip
                label={
                  scenarios.length < 2
                    ? "Create a second scenario to compare them side by side"
                    : "View all scenarios side by side"
                }
              >
                <Button
                  size="sm"
                  variant={showComparison ? "solid" : "outline"}
                  colorScheme="purple"
                  onClick={() =>
                    showComparison ? setShowComparison(false) : handleCompare()
                  }
                  isLoading={comparisonMutation.isPending}
                  isDisabled={scenarios.length < 2}
                >
                  {showComparison ? "Hide Comparison" : "Compare Scenarios"}
                </Button>
              </Tooltip>
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
            <Tooltip label="Update this plan to include the current household members and re-run the simulation">
              <Button
                size="sm"
                onClick={handleRefreshHousehold}
                isLoading={refreshHouseholdMutation.isPending}
              >
                Recalculate
              </Button>
            </Tooltip>
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
                      {/* Scenario type badge */}
                      {(() => {
                        const isEffectivelyAll =
                          s.include_all_members ||
                          (s.household_member_ids &&
                            householdMembers.length > 0 &&
                            s.household_member_ids.length >=
                              householdMembers.length &&
                            householdMembers.every((m) =>
                              s.household_member_ids!.includes(m.id),
                            ));
                        if (isEffectivelyAll) {
                          return (
                            <Tooltip label="All household members">
                              <Badge
                                colorScheme="purple"
                                variant="subtle"
                                fontSize="9px"
                                px={1}
                              >
                                <HStack spacing={0.5}>
                                  <FiUsers size={9} />
                                  <Text>All</Text>
                                </HStack>
                              </Badge>
                            </Tooltip>
                          );
                        }
                        if (
                          s.household_member_ids &&
                          s.household_member_ids.length > 1
                        ) {
                          return (
                            <Tooltip
                              label={`Shared: ${s.household_member_ids
                                .map((id) => {
                                  const m = householdMembers.find(
                                    (hm) => hm.id === id,
                                  );
                                  return (
                                    m?.display_name ??
                                    m?.first_name ??
                                    "Unknown"
                                  );
                                })
                                .join(", ")}`}
                            >
                              <Badge
                                colorScheme="blue"
                                variant="subtle"
                                fontSize="9px"
                                px={1}
                              >
                                <HStack spacing={0.5}>
                                  <FiUsers size={9} />
                                  <Text>Shared</Text>
                                </HStack>
                              </Badge>
                            </Tooltip>
                          );
                        }
                        return null;
                      })()}
                      {s.is_stale && (
                        <Tooltip label="Household members have changed since this scenario was last simulated. Re-run the simulation to update.">
                          <Badge
                            colorScheme="orange"
                            variant="subtle"
                            fontSize="9px"
                            px={1}
                          >
                            Stale
                          </Badge>
                        </Tooltip>
                      )}
                      <Text as="span">
                        {s.name}
                        {isCombinedView &&
                          (s.include_all_members ||
                            (s.household_member_ids &&
                              s.household_member_ids.length > 1)) &&
                          (() => {
                            const owner = householdMembers.find(
                              (m) => m.id === s.user_id,
                            );
                            const ownerName =
                              owner?.display_name ?? owner?.first_name;
                            return ownerName ? (
                              <Text
                                as="span"
                                ml={1}
                                fontSize="xs"
                                color="gray.400"
                                fontWeight="normal"
                              >
                                by {ownerName}
                              </Text>
                            ) : null;
                          })()}
                        {s.readiness_score !== null && (
                          <Text as="span" ml={1} fontSize="xs" color="gray.500">
                            ({s.readiness_score})
                          </Text>
                        )}
                      </Text>
                      {!readOnly && (
                        <>
                          <Tooltip label="Rename">
                            <IconButton
                              as="span"
                              role="button"
                              tabIndex={0}
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
                          </Tooltip>
                          {householdMembers.length >= 2 && (
                            <Tooltip label="Manage members">
                              <IconButton
                                as="span"
                                role="button"
                                tabIndex={0}
                                aria-label="Manage members"
                                icon={<FiUsers size={10} />}
                                size="xs"
                                variant="ghost"
                                minW="auto"
                                h="auto"
                                p={0.5}
                                fontSize="10px"
                                opacity={0.5}
                                _hover={{ opacity: 1, color: "blue.400" }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOpenMemberEditor(s.id);
                                }}
                              />
                            </Tooltip>
                          )}
                          {(s.include_all_members ||
                            (s.household_member_ids &&
                              s.household_member_ids.length > 1)) && (
                            <Tooltip label="Archive">
                              <IconButton
                                as="span"
                                role="button"
                                tabIndex={0}
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
                            </Tooltip>
                          )}
                          <Tooltip label="Delete">
                            <IconButton
                              as="span"
                              role="button"
                              tabIndex={0}
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
                          </Tooltip>
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

        {/* Life events empty state */}
        {scenario && scenario.life_events.length === 0 && (
          <Text fontSize="sm" color={mutedTextColor} textAlign="center">
            No life events added yet. Use &quot;+ Add Life Event&quot; to model major expenses like a home purchase, kids, or an inheritance.
          </Text>
        )}

        {/* Add Life Event Buttons */}
        {scenario && !readOnly && (
          <HStack spacing={2}>
            <Tooltip label="Add a major expense or income change like buying a home, having kids, or an inheritance">
              <Button
                size="sm"
                variant="outline"
                colorScheme="blue"
                onClick={presetPicker.onOpen}
              >
                + Add Life Event
                <HelpHint hint={helpContent.retirement.lifeEvents} />
              </Button>
            </Tooltip>
            <Tooltip label="Create a life event with fully custom parameters">
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
            </Tooltip>
          </HStack>
        )}

        {/* Run Simulation */}
        {scenario && (
          <VStack spacing={2} align="stretch">
            <Tooltip label="Run thousands of random market scenarios to estimate how your plan holds up">
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
            </Tooltip>
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
            {/* Social Security Estimator — shown at 55+ when planning is actionable */}
            {showSocialSecurity ? (
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
            ) : (
              <Tooltip label="Social Security planning becomes relevant around age 55. We'll show this section when you're closer to claiming age.">
                <Text fontSize="xs" color={mutedTextColor} textAlign="center" cursor="help">
                  Social Security estimator available at age {SS_SHOW_AGE}+
                </Text>
              </Tooltip>
            )}

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
                    <Tooltip label="Percentage of simulations where your money lasted through retirement">
                      <Text
                        color="gray.500"
                        cursor="help"
                        borderBottom="1px dashed"
                        borderColor="gray.400"
                      >
                        Success Rate
                      </Text>
                    </Tooltip>
                    <Text fontWeight="bold">
                      {results.success_rate.toFixed(1)}%
                    </Text>
                  </HStack>
                  {results.median_portfolio_at_retirement && (
                    <HStack justify="space-between">
                      <Tooltip label="Median projected portfolio value when you stop working">
                        <Text
                          color="gray.500"
                          cursor="help"
                          borderBottom="1px dashed"
                          borderColor="gray.400"
                        >
                          Portfolio at Retirement
                        </Text>
                      </Tooltip>
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
                      <Tooltip label="Median projected portfolio value at your life expectancy age">
                        <Text
                          color="gray.500"
                          cursor="help"
                          borderBottom="1px dashed"
                          borderColor="gray.400"
                        >
                          Portfolio at End
                        </Text>
                      </Tooltip>
                      <Text fontWeight="bold">
                        $
                        {(results.median_portfolio_at_end / 1000000).toFixed(2)}
                        M
                      </Text>
                    </HStack>
                  )}
                  {results.median_depletion_age && (
                    <HStack justify="space-between">
                      <Tooltip label="In the worst-case scenarios, this is the age at which your portfolio runs out">
                        <Text
                          color="red.400"
                          cursor="help"
                          borderBottom="1px dashed"
                          borderColor="red.300"
                        >
                          Median Depletion Age
                        </Text>
                      </Tooltip>
                      <Text fontWeight="bold" color="red.400">
                        {results.median_depletion_age}
                      </Text>
                    </HStack>
                  )}
                  {results.estimated_pia && (
                    <HStack justify="space-between">
                      <Tooltip label="Estimated Social Security Primary Insurance Amount based on your income">
                        <Text
                          color="gray.500"
                          cursor="help"
                          borderBottom="1px dashed"
                          borderColor="gray.400"
                        >
                          Estimated SS (PIA)
                        </Text>
                      </Tooltip>
                      <Text fontWeight="bold">
                        ${results.estimated_pia.toFixed(0)}/mo
                      </Text>
                    </HStack>
                  )}
                  <HStack justify="space-between">
                    <Tooltip label="Number of random market scenarios tested to estimate your outcomes">
                      <Text
                        color="gray.500"
                        cursor="help"
                        borderBottom="1px dashed"
                        borderColor="gray.400"
                      >
                        Simulations Run
                      </Text>
                    </Tooltip>
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
        onCustomEvent={() => {
          setEditingEvent(null);
          eventEditor.onOpen();
        }}
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
                  onChange={(val) => {
                    const mode = val as "just_me" | "select" | "all";
                    setMemberPickerMode(mode);
                    setNewScenarioName(
                      mode === "just_me"
                        ? "My Retirement Plan"
                        : "Household Retirement Plan",
                    );
                  }}
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

      {/* Edit Members Modal */}
      <Modal isOpen={memberEditor.isOpen} onClose={memberEditor.onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Manage Plan Members</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Box>
                <Text fontSize="sm" fontWeight="medium" mb={2}>
                  Who is this plan for?
                </Text>
                <RadioGroup
                  value={editMemberMode}
                  onChange={(val) =>
                    setEditMemberMode(val as "just_me" | "select" | "all")
                  }
                >
                  <VStack align="start" spacing={2}>
                    <Radio value="just_me">Just me</Radio>
                    <Radio value="all">All household members</Radio>
                    <Radio value="select">Select specific members</Radio>
                  </VStack>
                </RadioGroup>
              </Box>

              {editMemberMode === "select" && (
                <VStack align="stretch" spacing={2} pl={6}>
                  {householdMembers.map((m) => (
                    <Checkbox
                      key={m.id}
                      isChecked={editMemberIds.has(m.id)}
                      onChange={(e) => {
                        const next = new Set(editMemberIds);
                        if (e.target.checked) {
                          next.add(m.id);
                        } else {
                          next.delete(m.id);
                        }
                        setEditMemberIds(next);
                      }}
                    >
                      {m.display_name || m.first_name || m.email}
                    </Checkbox>
                  ))}
                  {editMemberIds.size < 2 && (
                    <Text fontSize="xs" color="orange.400">
                      Select at least 2 members for a multi-person plan.
                    </Text>
                  )}
                </VStack>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={memberEditor.onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleSaveMemberEdit}
              isLoading={updateMutation.isPending}
              isDisabled={editMemberMode === "select" && editMemberIds.size < 2}
            >
              Save
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
}
