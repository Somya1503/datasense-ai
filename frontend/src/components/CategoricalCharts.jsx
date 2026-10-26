import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { Tags } from "lucide-react";
import Section from "./Section";
import { formatNumber, formatPercent, shorten } from "../utils/format";

export default function CategoricalCharts({ summary }) {
  const names = Object.keys(summary || {});
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

  const info = active ? summary[active] : null;
  const data = info
    ? info.top_values.map((v) => ({
        name: shorten(v.value), full: String(v.value), count: v.count, percent: v.percent,
      }))
    : [];

  return (
    <Section
      id="categorical"
      title="Categorical Analysis"
      subtitle="Most frequent values in text and boolean columns"
      icon={Tags}
      right={picker}
    >
      {!info ? (
        <div className="empty-small">This dataset has no categorical columns.</div>
      ) : data.length === 0 ? (
        <div className="empty-small">This column has no non-missing values.</div>
      ) : (
        <>
          <div className="two-col">
            <ResponsiveContainer width="100%" height={Math.max(220, data.length * 36)}>
              <BarChart data={data} layout="vertical" margin={{ left: 4, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#d6cdb9" />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v, _n, p) => [`${v} (${formatPercent(p.payload.percent)})`, "Count"]} />
                <Bar dataKey="count" fill="#5f7a5c" radius={[0, 0, 0, 0]} barSize={18} />
              </BarChart>
            </ResponsiveContainer>

            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr><th>Value</th><th className="num">Count</th><th className="num">Share</th></tr>
                </thead>
                <tbody>
                  {data.map((d) => (
                    <tr key={d.full}>
                      <td className="strong">{d.full}</td>
                      <td className="num">{formatNumber(d.count)}</td>
                      <td className="num">{formatPercent(d.percent)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <p className="muted legend-note">
            {formatNumber(info.unique_count)} unique values
            {info.truncated ? ` · showing the top ${data.length}` : ""}
          </p>
        </>
      )}
    </Section>
  );
}