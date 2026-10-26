import { Database, Columns3, AlertCircle, Copy } from "lucide-react";
import { formatNumber, formatPercent } from "../utils/format";

export default function SummaryCards({ summary, meta }) {
  const totalCells = summary.rows * summary.columns;
  const missingPct = totalCells ? (summary.total_missing_cells / totalCells) * 100 : 0;

  const cards = [
    {
      label: "Total rows", value: summary.rows, icon: Database,
      note: "Records in the dataset",
    },
    {
      label: "Total columns", value: summary.columns, icon: Columns3,
      note: `${summary.numeric_columns} numeric · ${summary.categorical_columns} categorical`,
    },
    {
      label: "Missing cells", value: summary.total_missing_cells, icon: AlertCircle,
      note: `${formatPercent(missingPct)} of all cells`,
      flag: summary.total_missing_cells > 0,
    },
    {
      label: "Duplicate rows", value: summary.duplicate_rows, icon: Copy,
      note: `${formatPercent(summary.duplicate_percent)} of rows`,
      flag: summary.duplicate_rows > 0,
    },
  ];

  return (
    <div id="overview">
      <div className="cards">
        {cards.map(({ label, value, icon: Icon, note, flag }) => (
          <div key={label} className="card kpi">
            <div className="kpi-top">
              <span className="kpi-label">{label}</span>
              <span className={`kpi-icon ${flag ? "warn" : ""}`}><Icon size={18} /></span>
            </div>
            <div className="kpi-value">{formatNumber(value)}</div>
            <div className="kpi-note">{note}</div>
          </div>
        ))}
      </div>
      {meta && (
        <p className="muted meta-line">
          Detected encoding: {meta.encoding} · Delimiter:{" "}
          {meta.delimiter === "\t" ? "tab" : `"${meta.delimiter}"`}
        </p>
      )}
    </div>
  );
}