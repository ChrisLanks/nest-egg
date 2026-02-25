/**
 * TanStack Query hooks for retirement planning API.
 */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../../../services/api';
import type {
  HealthcareCostEstimate,
  LifeEvent,
  LifeEventCreate,
  LifeEventPreset,
  QuickSimulationRequest,
  QuickSimulationResponse,
  RetirementAccountData,
  RetirementScenario,
  RetirementScenarioCreate,
  RetirementScenarioSummary,
  ScenarioComparisonItem,
  SimulationResult,
  SocialSecurityEstimate,
} from '../types/retirement';

const QUERY_KEY = 'retirement-scenarios';

export function useRetirementScenarios(userId?: string, enabled = true) {
  return useQuery<RetirementScenarioSummary[]>({
    queryKey: [QUERY_KEY, userId],
    queryFn: async () => {
      const params = userId ? { user_id: userId } : {};
      const { data } = await api.get<RetirementScenarioSummary[]>('/retirement/scenarios', { params });
      return data;
    },
    enabled,
  });
}

export function useRetirementScenario(scenarioId: string | null) {
  return useQuery<RetirementScenario>({
    queryKey: [QUERY_KEY, 'detail', scenarioId],
    queryFn: async () => {
      const { data } = await api.get<RetirementScenario>(`/retirement/scenarios/${scenarioId}`);
      return data;
    },
    enabled: !!scenarioId,
    placeholderData: keepPreviousData,
  });
}

export function useCreateScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (scenario: RetirementScenarioCreate) => {
      const { data } = await api.post<RetirementScenario>('/retirement/scenarios', scenario);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useCreateDefaultScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<RetirementScenario>('/retirement/scenarios/default');
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useUpdateScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<RetirementScenarioCreate> }) => {
      const { data } = await api.patch<RetirementScenario>(`/retirement/scenarios/${id}`, updates);
      return data;
    },
    onSuccess: (data, variables) => {
      // Immediately update the detail cache so the UI reflects changes without waiting for re-fetch
      queryClient.setQueryData([QUERY_KEY, 'detail', variables.id], data);
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useDeleteScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/retirement/scenarios/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useDuplicateScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, name }: { id: string; name?: string }) => {
      const params = name ? { name } : {};
      const { data } = await api.post<RetirementScenario>(
        `/retirement/scenarios/${id}/duplicate`,
        null,
        { params }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useRunSimulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (scenarioId: string) => {
      const { data } = await api.post<SimulationResult>(
        `/retirement/scenarios/${scenarioId}/simulate`
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useSimulationResults(scenarioId: string | null) {
  return useQuery<SimulationResult>({
    queryKey: [QUERY_KEY, 'results', scenarioId],
    queryFn: async () => {
      const { data } = await api.get<SimulationResult>(
        `/retirement/scenarios/${scenarioId}/results`
      );
      return data;
    },
    enabled: !!scenarioId,
    retry: false, // Don't retry 404s (no results yet)
    placeholderData: keepPreviousData,
  });
}

export function useQuickSimulate() {
  return useMutation({
    mutationFn: async (params: QuickSimulationRequest) => {
      const { data } = await api.post<QuickSimulationResponse>(
        '/retirement/quick-simulate',
        params
      );
      return data;
    },
  });
}

// --- Life Events ---

export function useAddLifeEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ scenarioId, event }: { scenarioId: string; event: LifeEventCreate }) => {
      const { data } = await api.post<LifeEvent>(
        `/retirement/scenarios/${scenarioId}/life-events`,
        event
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useAddLifeEventFromPreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      scenarioId,
      presetKey,
      startAge,
    }: {
      scenarioId: string;
      presetKey: string;
      startAge?: number;
    }) => {
      const { data } = await api.post<LifeEvent>(
        `/retirement/scenarios/${scenarioId}/life-events/from-preset`,
        { preset_key: presetKey, start_age: startAge }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useUpdateLifeEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ eventId, updates }: { eventId: string; updates: Partial<LifeEventCreate> }) => {
      const { data } = await api.patch<LifeEvent>(`/retirement/life-events/${eventId}`, updates);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useDeleteLifeEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (eventId: string) => {
      await api.delete(`/retirement/life-events/${eventId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

// --- Presets ---

export function useLifeEventPresets() {
  return useQuery<LifeEventPreset[]>({
    queryKey: [QUERY_KEY, 'presets'],
    queryFn: async () => {
      const { data } = await api.get<LifeEventPreset[]>('/retirement/life-event-presets');
      return data;
    },
    staleTime: 1000 * 60 * 60, // Presets don't change often
  });
}

// --- Social Security ---

export function useSocialSecurityEstimate(claimingAge: number = 67, overrideSalary?: number) {
  return useQuery<SocialSecurityEstimate>({
    queryKey: [QUERY_KEY, 'ss-estimate', claimingAge, overrideSalary],
    queryFn: async () => {
      const params: Record<string, number> = { claiming_age: claimingAge };
      if (overrideSalary !== undefined) params.override_salary = overrideSalary;
      const { data } = await api.get<SocialSecurityEstimate>(
        '/retirement/social-security-estimate',
        { params }
      );
      return data;
    },
  });
}

// --- Healthcare ---

export function useHealthcareEstimate(
  retirementIncome: number = 50000,
  medicalInflationRate: number = 6.0,
) {
  return useQuery<HealthcareCostEstimate>({
    queryKey: [QUERY_KEY, 'healthcare-estimate', retirementIncome, medicalInflationRate],
    queryFn: async () => {
      const { data } = await api.get<HealthcareCostEstimate>(
        '/retirement/healthcare-estimate',
        { params: { retirement_income: retirementIncome, medical_inflation_rate: medicalInflationRate } }
      );
      return data;
    },
  });
}

// --- Account Data ---

export function useRetirementAccountData(userId?: string) {
  return useQuery<RetirementAccountData>({
    queryKey: [QUERY_KEY, 'account-data', userId],
    queryFn: async () => {
      const params = userId ? { user_id: userId } : {};
      const { data } = await api.get<RetirementAccountData>('/retirement/account-data', { params });
      return data;
    },
  });
}

// --- Scenario Comparison ---

export function useScenarioComparison() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (scenarioIds: string[]) => {
      const { data } = await api.post<{ scenarios: ScenarioComparisonItem[] }>(
        '/retirement/compare',
        { scenario_ids: scenarioIds }
      );
      return data.scenarios;
    },
  });
}
