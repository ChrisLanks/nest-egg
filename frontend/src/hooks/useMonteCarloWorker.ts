/**
 * React hook that runs Monte Carlo simulations in a Web Worker.
 *
 * Falls back to synchronous main-thread execution if workers are
 * unavailable (SSR, old browsers, test environments).
 */

import { useEffect, useMemo, useRef, useState } from "react";

import type {
  SimulationParams,
  SimulationSummary,
} from "../utils/monteCarloSimulation";
import { runMonteCarloSimulation } from "../utils/monteCarloSimulation";
import type { WorkerRequest, WorkerResponse } from "../utils/monteCarloWorker";

const EMPTY: SimulationSummary[] = [];

export function useMonteCarloWorker(scenarios: SimulationParams[]): {
  results: SimulationSummary[];
  computing: boolean;
} {
  const [results, setResults] = useState<SimulationSummary[]>(EMPTY);
  const [computing, setComputing] = useState(false);
  const workerRef = useRef<Worker | null>(null);
  const requestIdRef = useRef(0);

  // Initialise worker once
  useEffect(() => {
    try {
      const worker = new Worker(
        new URL("../utils/monteCarloWorker.ts", import.meta.url),
        { type: "module" },
      );

      worker.onmessage = (e: MessageEvent<WorkerResponse>) => {
        const { id, results: workerResults } = e.data;
        if (id === requestIdRef.current) {
          setResults(workerResults);
          setComputing(false);
        }
      };

      worker.onerror = () => {
        workerRef.current = null;
      };

      workerRef.current = worker;
    } catch {
      workerRef.current = null;
    }

    return () => {
      workerRef.current?.terminate();
      workerRef.current = null;
    };
  }, []);

  // Stable key so the effect only re-fires when params actually change
  const scenariosKey = useMemo(() => JSON.stringify(scenarios), [scenarios]);

  // Dispatch simulation whenever scenarios change.
  // setState inside an effect is the correct pattern here: we're synchronising
  // with an external system (Web Worker / fallback computation).
  useEffect(() => {
    const params: SimulationParams[] = JSON.parse(scenariosKey);

    if (params.length === 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clearing results for empty input
      setResults(EMPTY);
      return;
    }

    const id = ++requestIdRef.current;

    if (workerRef.current) {
      setComputing(true);
      workerRef.current.postMessage({
        id,
        scenarios: params,
      } satisfies WorkerRequest);
    } else {
      // Synchronous fallback — no worker available
      setResults(params.map((p) => runMonteCarloSimulation(p)));
    }
  }, [scenariosKey]);

  return { results, computing };
}
