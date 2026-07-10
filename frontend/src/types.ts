export type Phase = "start" | "progress" | "complete";

export interface StepEvent {
  node: string;
  phase: Phase;
  message: string;
  data?: Record<string, unknown>;
  tokens?: number | null;
  ts: number;
}

export interface Source {
  index: number;
  title: string;
  url: string;
}

export interface ReportPayload {
  question: string;
  report: string;
  sources: Source[];
  unsupported_claims: string[];
  total_tokens: number;
  iterations: number;
}
