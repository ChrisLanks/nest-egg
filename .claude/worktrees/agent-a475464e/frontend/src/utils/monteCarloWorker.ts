/**
 * Web Worker for Monte Carlo simulations.
 *
 * Offloads heavy simulation math to a background thread so the UI
 * stays responsive during parameter changes and slider drags.
 */

import {
  type SimulationParams,
  type SimulationSummary,
  runMonteCarloSimulation,
} from "./monteCarloSimulation";

export interface WorkerRequest {
  id: number;
  scenarios: SimulationParams[];
}

export interface WorkerResponse {
  id: number;
  results: SimulationSummary[];
}

self.onmessage = (e: MessageEvent<WorkerRequest>) => {
  const { id, scenarios } = e.data;
  const results = scenarios.map((params) => runMonteCarloSimulation(params));
  self.postMessage({ id, results } satisfies WorkerResponse);
};
