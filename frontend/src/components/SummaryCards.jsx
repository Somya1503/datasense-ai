import { formatNumber, formatPercent } from "../utils/format";

export default function SummaryCards({ summary, meta }) {
  const totalCells = summary.rows * summary.columns;
  const missingPct = totalCells ? (summary.total_missing_cells / totalCells) * 100 : 0;

  const cards = [
    { label: "Rows", value: summary.rows, note: "Records in the dataset", cls: "lead" },
    {
      label: "Columns", value: summary.columns,
      note: `${summary.numeric_columns} numeric · ${summary.categorical_columns} categorical`,
      cls: "sage",
    },
    {
      label: "Missing cells", value: summary.total_missing_cells,
      note: `${formatPercent(missingPct)} of all cells`,
      cls: summary.total_missing_cells > 0 ? "terracotta" : "",
    },
    {
      label: "Duplicate rows", value: summary.duplicate_rows,
      note: `${formatPercent(summary.duplicate_percent)} of rows`,
      cls: summary.duplicate_rows > 0 ? "ochre" : "",
    },
  ];

  return (
    <div id="overview">
      <div className="cards">
        {cards.map(({ label, value, note, cls }) => (
          <div key={label} className={`kpi ${cls}`}>
            <div className="kpi-label">{label}</div>
            <div className="kpi-value">{formatNumber(value)}</div>
            <div className="kpi-note">{note}</div>
          </div>
        ))}
      </div>
      {meta && (
        <p className="meta-line">
          Encoding {meta.encoding} · Delimiter {meta.delimiter === "\t" ? "tab" : `"${meta.delimiter}"`}
        </p>
      )}
    </div>
  );
}