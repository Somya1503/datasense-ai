import { useState } from "react";
import { AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import {
  CONFIDENCE_LABEL, SEVERITY_LABEL, SEVERITY_ORDER, formatEvidenceValue, humanize,
} from "../utils/profiling";

const ICONS = { critical: AlertTriangle, warning: AlertTriangle, info: Info };

function isScalar(v) {
  return ["string", "number", "boolean"].includes(typeof v);
}

// Renders whatever evidence the backend supplied: scalar facts as a list and
// per-column rows as a table. No values are invented or recomputed here.
function Evidence({ evidence, onSelectColumn }) {
  const { columns, columns_total: total, ...rest } = evidence;
  const scalars = Object.entries(rest).filter(([, v]) => isScalar(v));
  const keys = columns && columns.length ? Object.keys(columns[0]) : [];

  return (
    <div className="pf-evidence">
      {scalars.length > 0 && (
        <dl className="pf-evidence-list">
          {scalars.map(([k, v]) => (
            <div key={k}>
              <dt>{humanize(k)}</dt>
              <dd>{formatEvidenceValue(k, v)}</dd>
            </div>
          ))}
        </dl>
      )}
      {columns && columns.length > 0 && (
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Evidence table, scrollable">
          <table className="table pf-evidence-table">
            <thead>
              <tr>{keys.map((k) => <th key={k}>{k === "column" ? "Column" : humanize(k)}</th>)}</tr>
            </thead>
            <tbody>
              {columns.map((row, i) => (
                <tr key={i}>
                  {keys.map((k) => (
                    <td key={k} className={typeof row[k] === "number" ? "num" : "pf-wrap"}>
                      {k === "column" ? (
                        <button type="button" className="pf-col-btn" onClick={() => onSelectColumn(row[k])}>
                          {row[k]}
                        </button>
                      ) : (
                        formatEvidenceValue(k, row[k])
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {total > (columns ? columns.length : 0) && (
        <p className="muted">Showing the first {columns.length} of {total} affected columns.</p>
      )}
    </div>
  );
}

export default function FindingsPanel({ findings, counts, onSelectColumn }) {
  const [filter, setFilter] = useState("all");
  const shown = filter === "all" ? findings : findings.filter((f) => f.severity === filter);

  if (findings.length === 0) {
    return (
      <div className="finding success">
        <CheckCircle2 size={18} />
        <div>
          <strong>No findings under the current rules</strong>
          <p>
            No missing values, duplicates, constant columns, outliers or type/value inconsistencies matched the checks
            DataSense runs. This does not prove the data is correct, only that these checks found nothing.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="pf-filters" role="group" aria-label="Filter findings by severity">
        <button type="button" className="pf-chip" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>
          All ({counts.total})
        </button>
        {SEVERITY_ORDER.map((s) => (
          <button
            key={s}
            type="button"
            className={`pf-chip sev-${s}`}
            aria-pressed={filter === s}
            disabled={counts[s] === 0}
            onClick={() => setFilter(s)}
          >
            {SEVERITY_LABEL[s]} ({counts[s]})
          </button>
        ))}
      </div>

      <ol className="pf-findings">
        {shown.map((f) => {
          const Icon = ICONS[f.severity];
          return (
            <li key={f.id} className={`pf-finding sev-${f.severity}`}>
              <div className="pf-finding-head">
                <span className={`sev sev-${f.severity}`}><Icon size={14} aria-hidden="true" /> {SEVERITY_LABEL[f.severity]}</span>
                <span className={`conf conf-${f.confidence}`}>{CONFIDENCE_LABEL[f.confidence]}</span>
                <span className="pf-id">{f.id}</span>
              </div>
              <h3 className="pf-finding-title">{f.title}</h3>
              <p>{f.explanation}</p>

              {f.affected_columns.length > 0 && (
                <div className="chips pf-chips">
                  <span className="muted">Affected:</span>
                  {f.affected_columns.map((c) => (
                    <button type="button" key={c} className="pf-chip-link" onClick={() => onSelectColumn(c)}>{c}</button>
                  ))}
                  {f.affected_columns_total > f.affected_columns.length && (
                    <span className="muted">+{f.affected_columns_total - f.affected_columns.length} more</span>
                  )}
                </div>
              )}

              <details className="pf-details" open={f.severity !== "info"}>
                <summary>Evidence</summary>
                <Evidence evidence={f.evidence} onSelectColumn={onSelectColumn} />
              </details>

              <div className="pf-reco">
                <span className="pf-label">Suggested next step</span>
                <p>{f.recommendation}</p>
              </div>
            </li>
          );
        })}
      </ol>
      <p className="muted legend-note">
        Findings come from fixed rules applied to your data. &quot;Needs review&quot; means a person should judge it in context.
        DataSense does not change your file.
      </p>
    </div>
  );
}
