import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { ShieldCheck, AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import Section from "./Section";
import { formatNumber, formatPercent, shorten } from "../utils/format";

const HIGH_MISSING = 20; // percent; columns at or above this are flagged

function listNames(cols, max = 5) {
  const names = cols.slice(0, max).map((c) => c.name).join(", ");
  return cols.length > max ? `${names} and ${cols.length - max} more` : names;
}

// Findings are derived only from the API response; nothing is assumed.
function buildFindings(columns, summary) {
  const findings = [];

  if (summary.duplicate_rows > 0) {
    findings.push({
      level: "warning",
      title: `${formatNumber(summary.duplicate_rows)} duplicate rows (${formatPercent(summary.duplicate_percent)})`,
      text: "Exact duplicate records were found. Review whether they should be removed.",
    });
  }

  const high = columns.filter((c) => c.missing_percent >= HIGH_MISSING);
  if (high.length > 0) {
    findings.push({
      level: "warning",
      title: `${high.length} column${high.length === 1 ? "" : "s"} with ${HIGH_MISSING}% or more missing values`,
      text: listNames(high),
    });
  }

  const some = columns.filter((c) => c.missing_count > 0 && c.missing_percent < HIGH_MISSING);
  if (some.length > 0) {
    findings.push({
      level: "info",
      title: `${some.length} column${some.length === 1 ? "" : "s"} with some missing values`,
      text: listNames(some),
    });
  }

  const constant = columns.filter((c) => c.unique_count === 1);
  if (constant.length > 0) {
    findings.push({
      level: "info",
      title: `${constant.length} column${constant.length === 1 ? "" : "s"} with a single unique value`,
      text: `${listNames(constant)}. Constant columns carry little analytical information.`,
    });
  }

  if (findings.length === 0) {
    findings.push({
      level: "success",
      title: "No data quality issues detected",
      text: "No missing values, duplicate rows or constant columns were found.",
    });
  }
  return findings;
}

const ICONS = { warning: AlertTriangle, info: Info, success: CheckCircle2 };

export default function DataQuality({ columns, summary }) {
  const findings = buildFindings(columns, summary);

  const withMissing = columns
    .filter((c) => c.missing_count > 0)
    .sort((a, b) => b.missing_percent - a.missing_percent)
    .slice(0, 15)
    .map((c) => ({ name: shorten(c.name), percent: c.missing_percent, count: c.missing_count }));

  return (
    <Section
      id="quality"
      title="Data Quality"
      subtitle="Completeness, duplicates and column types"
      icon={ShieldCheck}
    >
      <div className="findings">
        {findings.map((f, i) => {
          const Icon = ICONS[f.level];
          return (
            <div key={i} className={`finding ${f.level}`}>
              <Icon size={18} />
              <div>
                <strong>{f.title}</strong>
                <p>{f.text}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="two-col">
        <div>
          <h3>Missing values by column</h3>
          {withMissing.length === 0 ? (
            <div className="empty-small">No missing values found.</div>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(180, withMissing.length * 38)}>
              <BarChart data={withMissing} layout="vertical" margin={{ left: 4, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
                <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v, _n, p) => [`${v}% (${p.payload.count} cells)`, "Missing"]} />
                <Bar dataKey="percent" radius={[0, 3, 3, 0]} barSize={16}>
                  {withMissing.map((d) => (
                    <Cell key={d.name} fill={d.percent >= HIGH_MISSING ? "#b45309" : "#2563eb"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          <p className="muted legend-note">Amber bars: {HIGH_MISSING}% or more missing.</p>
        </div>

        <div>
          <h3>Column details</h3>
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Column</th><th>Type</th><th>Dtype</th>
                  <th className="num">Missing</th><th className="num">Unique</th>
                </tr>
              </thead>
              <tbody>
                {columns.map((c) => (
                  <tr key={c.name}>
                    <td className="strong">{c.name}</td>
                    <td><span className={`badge ${c.kind}`}>{c.kind}</span></td>
                    <td className="muted">{c.dtype}</td>
                    <td className="num">
                      {formatNumber(c.missing_count)} ({formatPercent(c.missing_percent)})
                    </td>
                    <td className="num">{formatNumber(c.unique_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Section>
  );
}