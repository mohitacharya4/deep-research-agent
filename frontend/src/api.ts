import type { ReportPayload, StepEvent } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export interface ResearchHandlers {
  onStep: (event: StepEvent) => void;
  onReport: (report: ReportPayload) => void;
  onError: (message: string) => void;
  onDone: () => void;
}

/**
 * Open an SSE connection to the research endpoint and dispatch typed events.
 * Returns the EventSource so callers can close it to cancel a run.
 */
export function startResearch(
  question: string,
  maxIterations: number | null,
  handlers: ResearchHandlers,
): EventSource {
  const params = new URLSearchParams({ question });
  if (maxIterations) params.set("max_iterations", String(maxIterations));

  const source = new EventSource(`${API_BASE}/research?${params.toString()}`);
  let finished = false;

  source.addEventListener("step", (ev) => {
    handlers.onStep(JSON.parse((ev as MessageEvent).data) as StepEvent);
  });

  source.addEventListener("report", (ev) => {
    handlers.onReport(JSON.parse((ev as MessageEvent).data) as ReportPayload);
  });

  source.addEventListener("done", () => {
    finished = true;
    handlers.onDone();
    source.close();
  });

  // Fires for both our named "error" event (has data) and native transport errors.
  source.addEventListener("error", (ev) => {
    const message = (ev as MessageEvent).data;
    if (message) {
      handlers.onError((JSON.parse(message) as { message: string }).message);
    } else if (!finished) {
      handlers.onError("Connection to the research server was lost.");
    }
    source.close();
  });

  return source;
}
