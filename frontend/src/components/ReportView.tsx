import Markdown from "react-markdown";
import type { ReportPayload } from "../types";

export function ReportView({ report }: { report: ReportPayload }) {
  return (
    <article className="report">
      <div className="report-meta">
        <span>{report.sources.length} sources</span>
        <span>{report.iterations} iteration(s)</span>
        <span>{report.total_tokens.toLocaleString()} tokens</span>
      </div>

      {report.unsupported_claims.length > 0 && (
        <div className="report-warnings">
          <strong>Citation checks:</strong>
          <ul>
            {report.unsupported_claims.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="report-body">
        <Markdown
          components={{
            a: ({ href, children }) => (
              <a href={href} target="_blank" rel="noreferrer noopener">
                {children}
              </a>
            ),
          }}
        >
          {report.report}
        </Markdown>
      </div>
    </article>
  );
}
