import { useCallback, useRef, useState } from "react";
import { startResearch } from "./api";
import { QueryBar } from "./components/QueryBar";
import { ReportView } from "./components/ReportView";
import { StepTimeline } from "./components/StepTimeline";
import type { ReportPayload, StepEvent } from "./types";

export function App() {
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  const run = useCallback((question: string) => {
    setRunning(true);
    setSteps([]);
    setReport(null);
    setError(null);

    sourceRef.current = startResearch(question, null, {
      onStep: (event) => setSteps((prev) => [...prev, event]),
      onReport: (payload) => setReport(payload),
      onError: (message) => {
        setError(message);
        setRunning(false);
      },
      onDone: () => setRunning(false),
    });
  }, []);

  const cancel = useCallback(() => {
    sourceRef.current?.close();
    setRunning(false);
  }, []);

  return (
    <div className="app">
      <header className="header">
        <h1>Deep Research Agent</h1>
        <p className="subtitle">
          A local-first agent that plans, searches the web, reflects on gaps, and writes a cited
          report — streamed live.
        </p>
      </header>

      <QueryBar running={running} onSubmit={run} onCancel={cancel} />

      {error && <div className="error-banner">⚠ {error}</div>}

      <div className="content">
        <section className="panel timeline-panel">
          <h2>Agent trace</h2>
          <StepTimeline steps={steps} running={running} />
          {steps.length === 0 && !running && (
            <p className="muted">Ask a question to watch the agent work.</p>
          )}
        </section>

        <section className="panel report-panel">
          <h2>Report</h2>
          {report ? (
            <ReportView report={report} />
          ) : (
            <p className="muted">The cited report will appear here when the run completes.</p>
          )}
        </section>
      </div>
    </div>
  );
}
