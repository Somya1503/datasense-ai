import { Link2 } from "lucide-react";
import Section from "./Section";

function cellStyle(value) {
  if (value === null || value === undefined) return { background: "#f3f4f6", color: "#6b7280" };
  const alpha = Math.min(Math.abs(value), 1) * 0.9;
  const rgb = value >= 0 ? "37, 99, 235" : "217, 119, 6";
  return {
    background: `rgba(${rgb}, ${alpha})`,
    color: Math.abs(value) > 0.5 ? "#ffffff" : "#111827",
  };
}

function strength(r) {
  const a = Math.abs(r);
  const dir = r >= 0 ? "positive" : "negative";
  return `${a >= 0.9 ? "Very strong" : "Strong"} ${dir}`;
}

export default function CorrelationSection({ data }) {
  return (
    <Section
      id="correlations"
      title="Correlations"
      subtitle="Pearson correlation between numeric columns"
      icon={Link2}
    >
      {!data || !data.available ? (
        <div className="empty-small">
          {data?.reason || "Correlation data is not available for this dataset."}
        </div>
      ) : (
        <>
          <div className="table-scroll">
            <table className="heatmap">
              <thead>
                <tr>
                  <th />
                  {data.columns.map((c) => <th key={c} className="heat-col">{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.columns.map((rowName, i) => (
                  <tr key={rowName}>
                    <th className="heat-row">{rowName}</th>
                    {data.matrix[i].map((v, j) => (
                      <td
                        key={j}
                        style={cellStyle(v)}
                        title={`${rowName} vs ${data.columns[j]}: ${v === null ? "n/a" : v.toFixed(3)}`}
                      >
                        {v === null ? "—" : v.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="heat-legend">
            <span>-1</span>
            <span className="heat-bar" />
            <span>+1</span>
            <span className="muted">Orange = negative, blue = positive</span>
          </div>

          <h3>Strong relationships (|r| ≥ 0.7)</h3>
          {data.strong_pairs.length === 0 ? (
            <div className="empty-small">No strongly correlated pairs found.</div>
          ) : (
            <ul className="pair-list">
              {data.strong_pairs.map((p) => (
                <li key={`${p.column_a}-${p.column_b}`}>
                  <div>
                    <span className="strong">{p.column_a}</span>
                    <span className="muted"> ↔ </span>
                    <span className="strong">{p.column_b}</span>
                    <div className="muted">{strength(p.correlation)}</div>
                  </div>
                  <b className={p.correlation >= 0 ? "pos" : "neg"}>{p.correlation.toFixed(2)}</b>
                </li>
              ))}
            </ul>
          )}
          {data.truncated && (
            <p className="muted legend-note">
              Only the first columns are shown to keep the matrix readable.
            </p>
          )}
        </>
      )}
    </Section>
  );
}