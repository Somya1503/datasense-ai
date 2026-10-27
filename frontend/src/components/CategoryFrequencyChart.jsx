import {
  BarChart, Bar, LabelList, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { formatNumber, formatPercent, shorten } from "../utils/format";

// Frequency chart for one categorical profile. Percentages are shares of the
// column's NON-MISSING values; the backend already limits categories to the top N.
export default function CategoryFrequencyChart({ categorical }) {
  const data = categorical.top_values.map((v) => ({
    name: shorten(v.value, 20),
    full: String(v.value),
    count: v.count,
    percent: v.percent,
  }));

  return (
    <figure className="pf-figure">
      <ResponsiveContainer width="100%" height={Math.max(160, data.length * 34 + 30)}>
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 56, top: 4 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#d6cdb9" />
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(v, _n, p) => [`${formatNumber(v)} (${formatPercent(p.payload.percent)})`, "Count"]}
            labelFormatter={(_l, items) => (items && items[0] ? items[0].payload.full : "")}
          />
          <Bar dataKey="count" fill="#5f7a5c" barSize={16} isAnimationActive={false}>
            <LabelList dataKey="count" position="right" style={{ fontSize: 11 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <figcaption className="muted legend-note">
        Top {categorical.shown_count} categories; percentages are of non-missing values.
        {categorical.truncated
          ? ` ${formatNumber(categorical.other_count)} further values (${formatPercent(categorical.other_percent)}) belong to less frequent categories not shown.`
          : ""}
      </figcaption>
    </figure>
  );
}
