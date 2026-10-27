import { formatNumber, formatPercent } from "../utils/format";
import { humanize } from "../utils/profiling";

// Transparent, count-based metrics. Each one states its denominator.
// Deliberately no composite "quality score".
export default function QualityMetrics({ summary }) {
  const t = summary.type_counts;
  const f = summary.finding_counts;

  const items = [
    {
      label: "Completeness",
      value: formatPercent(summary.completeness_percent),
      basis: `${formatNumber(summary.total_cells - summary.missing_cells)} of ${formatNumber(summary.total_cells)} cells filled`,
      tone: "sage",
    },
    {
      label: "Complete rows",
      value: formatNumber(summary.complete_rows),
      basis: `${formatPercent(summary.complete_rows_percent)} of ${formatNumber(summary.rows)} rows have no gaps`,
    },
    {
      label: "Duplicate rows",
      value: formatNumber(summary.duplicate_rows),
      basis: `${formatPercent(summary.duplicate_percent)} of rows are repeats of an earlier row`,
      tone: summary.duplicate_rows > 0 ? "ochre" : "",
    },
    {
      label: "Columns with gaps",
      value: `${formatNumber(summary.columns_with_missing)} / ${formatNumber(summary.columns)}`,
      basis: `${formatNumber(summary.columns_all_missing)} entirely empty · ${formatNumber(summary.constant_columns)} constant`,
    },
    {
      label: "Column types",
      value: `${t.numeric} · ${t.categorical} · ${t.datetime} · ${t.other}`,
      basis: "numeric · categorical · datetime · other",
    },
    {
      label: "Findings",
      value: formatNumber(f.total),
      basis: `${f.critical} critical · ${f.warning} warning · ${f.info} info`,
      tone: f.critical > 0 ? "terracotta" : "",
    },
  ];

  return (
    <div className="pf-metrics-wrap">
      <dl className="pf-metrics" aria-label="Quality metrics">
        {items.map((m) => (
          <div key={m.label} className={`pf-metric ${m.tone || ""}`}>
            <dt>{m.label}</dt>
            <dd className="pf-metric-value">{m.value}</dd>
            <dd className="pf-metric-basis">{m.basis}</dd>
          </div>
        ))}
      </dl>
      <details className="pf-details">
        <summary>How these metrics and rules are defined</summary>
        <dl className="pf-defs">
          {Object.entries(summary.definitions).map(([k, v]) => (
            <div key={k}>
              <dt>{humanize(k)}</dt>
              <dd>{v}</dd>
            </div>
          ))}
          {Object.entries(summary.rules.severity).map(([k, v]) => (
            <div key={`sev-${k}`}>
              <dt>Severity: {k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
          {Object.entries(summary.rules.confidence).map(([k, v]) => (
            <div key={`conf-${k}`}>
              <dt>Confidence: {humanize(k)}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      </details>
    </div>
  );
}
