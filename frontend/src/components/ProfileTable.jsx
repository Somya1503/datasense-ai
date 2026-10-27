import { useState } from "react";
import { Search } from "lucide-react";
import { formatNumber, formatPercent } from "../utils/format";
import {
  detailLabel, filterProfiles, highlight, sortProfiles,
} from "../utils/profiling";

const COLUMNS = [
  { key: "name", label: "Column" },
  { key: "type", label: "Type" },
  { key: "missing", label: "Missing" },
  { key: "unique", label: "Distinct" },
  { key: null, label: "At a glance" },
];

// Searchable, sortable overview of every column profile.
export default function ProfileTable({ profiles, activeName, onSelect }) {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [sortKey, setSortKey] = useState(null); // null = original file order
  const [direction, setDirection] = useState("asc");

  const rows = sortProfiles(filterProfiles(profiles, query, typeFilter), sortKey, direction);

  // Click cycles: ascending -> descending -> original order.
  const toggleSort = (key) => {
    if (sortKey !== key) { setSortKey(key); setDirection("asc"); }
    else if (direction === "asc") setDirection("desc");
    else { setSortKey(null); setDirection("asc"); }
  };

  const ariaSort = (key) =>
    sortKey === key ? (direction === "asc" ? "ascending" : "descending") : "none";

  return (
    <div>
      <div className="pf-toolbar">
        <label className="pf-search">
          <span className="pf-label">Search columns</span>
          <span className="pf-search-box">
            <Search size={15} aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type part of a column name"
            />
          </span>
        </label>
        <label className="picker">
          <span className="pf-label">Type</span>
          <select className="select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="all">All types</option>
            <option value="numeric">Numeric</option>
            <option value="categorical">Categorical</option>
            <option value="datetime">Datetime</option>
            <option value="other">Other</option>
          </select>
        </label>
        <p className="muted pf-count" aria-live="polite">
          Showing {rows.length} of {profiles.length} columns
        </p>
      </div>

      <div className="table-scroll pf-table-scroll" tabIndex={0} role="region" aria-label="Column profiles, scrollable">
        <table className="table pf-table">
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th key={c.label} aria-sort={c.key ? ariaSort(c.key) : undefined}>
                  {c.key ? (
                    <button type="button" className="pf-sort" onClick={() => toggleSort(c.key)}>
                      {c.label}
                      <span aria-hidden="true" className="pf-sort-mark">
                        {sortKey === c.key ? (direction === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </button>
                  ) : (
                    c.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="muted">No columns match your search or filter.</td>
              </tr>
            )}
            {rows.map((p) => (
              <tr key={p.name} className={p.name === activeName ? "row-active" : ""}>
                <td>
                  <button
                    type="button"
                    className="pf-col-btn"
                    aria-current={p.name === activeName ? "true" : undefined}
                    onClick={() => onSelect(p.name)}
                    title="Show this column's full profile below"
                  >
                    {p.name}
                  </button>
                </td>
                <td>
                  <span className={`badge ${p.analytical_type}`}>{p.analytical_type}</span>{" "}
                  <span className="muted">{detailLabel(p)}</span>
                </td>
                <td>
                  <span className="pf-miss">
                    <span className="pf-bar" aria-hidden="true">
                      <span style={{ width: `${Math.min(p.missing_percent, 100)}%` }} />
                    </span>
                    <span className="num">
                      {formatNumber(p.missing_count)} ({formatPercent(p.missing_percent)})
                    </span>
                  </span>
                </td>
                <td className="num">
                  {formatNumber(p.unique_count)}
                  {p.unique_percent === null ? "" : ` (${formatPercent(p.unique_percent)})`}
                </td>
                <td className="muted">{highlight(p)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted legend-note">
        Missing % is of all rows. Distinct % is of non-missing values. Click a column name for its full profile.
      </p>
    </div>
  );
}
