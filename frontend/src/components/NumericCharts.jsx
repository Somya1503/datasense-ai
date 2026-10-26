import { useState } from "react";
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { BarChart3 } from "lucide-react";
import Section from "./Section";
import { formatNumber } from "../utils/format";

const STAT_COLUMNS = [
  ["count", "Count"], ["mean", "Mean"], ["std", "Std dev"], ["min", "Min"],
  ["q25", "Q25"], ["median", "Median"], ["q75", "Q75"], ["max", "Max"],
];

export default function NumericCharts({ stats }) {
  const names = Object.keys(stats || {});
  const [selected, setSelected] = useState(names[0] || "");
  const active = names.includes(selected) ? selected : names[0];

  const picker = names.length > 0 && (
    <label className="picker">
      <span className="muted">Column</span>
      <select className="select" value={active} onChange={(e) => setSelected(e.target.value)}>
        {names.map((n) => <option key={n}>{n}</option>)}
      </select>
    </label>
  );

  return (
    <Section
      id="numeric"
      title="Numeric Analysis"
      subtitle="Descriptive statistics for every numeric column"
      icon={BarChart3}
      right={picker}
    >
      {names.length === 0 ? (
        <div className="empty-small">This dataset has no numeric columns.</div>
      ) : (
        <>
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Column</th>
                  {STAT_COLUMNS.map(([, label]) => <th key={label} className="num">{label}</th>)}
                </tr>
              </thead>
              <tbody>
                {names.map((n) => (
                  <tr key={n} className={n === active ? "row-active" : ""}>
                    <td className="strong">{n}</td>
                    {STAT_COLUMNS.map(([key]) => (
                      <td key={key} className="num">{formatNumber(stats[n][key])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3>Five-number summary: {active}</h3>
          <NumericBody stat={stats[active]} />
        </>
      )}
    </Section>
  );
}

function NumericBody({ stat }) {
  if (stat.count === 0) {
    return <div className="empty-small">This column has no valid numeric values.</div>;
  }
  const data = [
    { label: "Min", value: stat.min },
    { label: "Q25", value: stat.q25 },
    { label: "Median", value: stat.median },
    { label: "Mean", value: stat.mean },
    { label: "Q75", value: stat.q75 },
    { label: "Max", value: stat.max },
  ];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 20, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#d6cdb9" />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
        <YAxis tickFormatter={formatNumber} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v) => [formatNumber(v), "Value"]} />
        <Bar dataKey="value" radius={[0, 0, 0, 0]} maxBarSize={56}>
          {data.map((d) => (
            <Cell key={d.label} fill={d.label === "Mean" ? "#b4492b" : "#1d1b18"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}