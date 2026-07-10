import { useState } from "react";

const EXAMPLES = [
  "What are the tradeoffs of RAG vs fine-tuning in 2025?",
  "How does LangGraph compare to plain LangChain for agents?",
  "What's the state of small local LLMs for tool calling?",
];

interface Props {
  running: boolean;
  onSubmit: (question: string) => void;
  onCancel: () => void;
}

export function QueryBar({ running, onSubmit, onCancel }: Props) {
  const [value, setValue] = useState("");

  const submit = (question: string) => {
    const q = question.trim();
    if (q.length >= 3 && !running) onSubmit(q);
  };

  return (
    <div className="querybar">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
      >
        <input
          type="text"
          placeholder="Ask a research question…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={running}
        />
        {running ? (
          <button type="button" className="btn-cancel" onClick={onCancel}>
            Stop
          </button>
        ) : (
          <button type="submit" className="btn-go" disabled={value.trim().length < 3}>
            Research
          </button>
        )}
      </form>

      <div className="examples">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            className="chip"
            disabled={running}
            onClick={() => {
              setValue(ex);
              submit(ex);
            }}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
