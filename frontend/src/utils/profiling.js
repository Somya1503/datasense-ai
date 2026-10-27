import { formatNumber, formatPercent } from "./format";

// Display helpers for the column_profiles / quality_findings API fields.
// Nothing here computes statistics; it only sorts, filters and formats
// values that the backend already calculated.

export const TYPE_ORDER = { numeric: 0, categorical: 1, datetime: 2, other: 3 };

export const SEVERITY_ORDER = ["critical", "warning", "info"];
export const SEVERITY_LABEL = { critical: "Critical", warning: "Warning", info: "Info" };
export const CONFIDENCE_LABEL = { confirmed: "Confirmed", needs_review: "Needs review" };

const DETAIL_LABEL = {
  integer: "integer",
  decimal: "decimal",
  text: "text",
  boolean: "boolean",
  boolean_like: "yes/no text",
  datetime64: "datetime",
  date_like_text: "date-like text",
  identifier_like: "identifier-like",
  all_missing: "all missing",
  no_finite_values: "no finite values",
};

export function detailLabel(profile) {
  return DETAIL_LABEL[profile.type_detail] || profile.type_detail;
}

export function humanize(key) {
  const spaced = String(key).replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export const SORT_KEYS = ["name", "type", "missing", "unique"];

function compare(a, b, key) {
  switch (key) {
    case "type":
      return (TYPE_ORDER[a.analytical_type] ?? 9) - (TYPE_ORDER[b.analytical_type] ?? 9)
        || String(a.name).localeCompare(String(b.name));
    case "missing":
      return a.missing_percent - b.missing_percent;
    case "unique":
      return a.unique_count - b.unique_count;
    default:
      return String(a.name).localeCompare(String(b.name), undefined, { numeric: true });
  }
}

// key === null keeps the original column order from the file.
export function sortProfiles(profiles, key, direction) {
  if (!key) return profiles;
  const sign = direction === "desc" ? -1 : 1;
  return [...profiles].sort((a, b) => sign * compare(a, b, key));
}

export function filterProfiles(profiles, query, type) {
  const q = query.trim().toLowerCase();
  return profiles.filter(
    (p) =>
      (type === "all" || p.analytical_type === type) &&
      (q === "" || String(p.name).toLowerCase().includes(q))
  );
}

// One-line summary shown in the "at a glance" column.
export function highlight(profile) {
  if (profile.is_all_missing) return "No values";
  if (profile.numeric) {
    const n = profile.numeric;
    return `mean ${formatNumber(n.mean)} · median ${formatNumber(n.median)}`;
  }
  if (profile.categorical) {
    const top = profile.categorical.top_values[0];
    return top ? `top: ${String(top.value)} (${formatPercent(top.percent)})` : "—";
  }
  if (profile.datetime) {
    const d = profile.datetime;
    return d.earliest && d.latest
      ? `${d.earliest.slice(0, 10)} to ${d.latest.slice(0, 10)}`
      : "date range not shown";
  }
  return detailLabel(profile);
}

export function formatEvidenceValue(key, value) {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.length ? value.map(String).join("; ") : "—";
  if (typeof value === "number") {
    return /percent/.test(key) ? formatPercent(value) : formatNumber(value);
  }
  if (typeof value === "boolean") return value ? "yes" : "no";
  return String(value);
}
