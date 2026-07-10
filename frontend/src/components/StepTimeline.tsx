import type { StepEvent } from "../types";

const NODE_LABELS: Record<string, string> = {
  plan: "Plan",
  search: "Search",
  fetch: "Read",
  reflect: "Reflect",
  synthesize: "Write",
  critic: "Verify",
};

const PHASE_ICON: Record<string, string> = {
  start: "◆",
  progress: "•",
  complete: "✓",
};

export function StepTimeline({ steps, running }: { steps: StepEvent[]; running: boolean }) {
  if (steps.length === 0 && !running) return null;

  return (
    <ol className="timeline">
      {steps.map((step, i) => (
        <li key={i} className={`timeline-item node-${step.node} phase-${step.phase}`}>
          <span className="timeline-icon">{PHASE_ICON[step.phase] ?? "•"}</span>
          <div className="timeline-body">
            <span className="timeline-node">{NODE_LABELS[step.node] ?? step.node}</span>
            <span className="timeline-msg">{step.message}</span>
            {typeof step.tokens === "number" && step.tokens > 0 && (
              <span className="timeline-tokens">{step.tokens} tok</span>
            )}
          </div>
        </li>
      ))}
      {running && (
        <li className="timeline-item running">
          <span className="timeline-icon spinner">◐</span>
          <div className="timeline-body">
            <span className="timeline-msg muted">working…</span>
          </div>
        </li>
      )}
    </ol>
  );
}
