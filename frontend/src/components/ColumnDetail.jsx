import { formatNumber, formatPercent } from "../utils/format";
import { SEVERITY_LABEL, detailLabel } from "../utils/profiling";
import CategoryFrequencyChart from "./CategoryFrequencyChart";

// A statistic that is not defined renders as "undefined", never as 0 or blank,
// so missing, zero and undefined stay visually distinct.
function Stat({ label, value, note, format = formatNumber }) {
  const isUndefined = value === null || value === undefined;
  return (
    <div className="pf-stat">
      <dt>{label}</dt>
      <dd className={isUndefined ? "undef" : ""}>
        {isUndefined ? "undefined" : format(value)}
      </dd>
      {note && <dd className="pf-stat-note">{note}</dd>}
    </div>
  );
}

export default function ColumnDetail({ profile: p, findings }) {
  const n = p.numeric;
  const c = p.categorical;
  const flags = [];
  if (p.is_all_missing) flags.push("all values missing");
  if (p.is_constant) flags.push("constant");
  if (p.cardinality?.high_cardinality) flags.push("high cardinality");
  if (p.type_detail === "identifier_like") flags.push("identifier-like");

  return (
    <article className="pf-detail" aria-labelledby="pf-detail-title" aria-live="polite">
      <header className="pf-detail-head">
        <div>
          <span className="pf-label">Selected column</span>
          <h3 id="pf-detail-title" className="pf-detail-title">{p.name}</h3>
        </div>
        <div className="chips">
          <span className={`badge ${p.analytical_type}`}>{p.analytical_type}</span>
          <span className="chip">{detailLabel(p)}</span>
          <span className="chip">pandas dtype: {p.dtype}</span>
          {flags.map((f) => <span key={f} className="chip danger">{f}</span>)}
        </div>
      </header>
      <p className="muted pf-reason"><strong>Why this type:</strong> {p.type_reason}</p>

      <h4 className="pf-h4">Counts</h4>
      <dl className="pf-grid">
        <Stat label="Rows" value={p.row_count} />
        <Stat label="Non-missing" value={p.non_missing_count} />
        <Stat label="Missing" value={p.missing_count} note={`${formatPercent(p.missing_percent)} of all rows`} />
        <Stat
          label="Distinct values"
          value={p.unique_count}
          note={p.unique_percent === null ? "no values to compare" : `${formatPercent(p.unique_percent)} of non-missing`}
        />
        {p.cardinality && (
          <Stat label="Cardinality" value={p.cardinality.level} format={String}
            note={p.cardinality.all_values_unique ? "every value is different" : undefined} />
        )}
      </dl>

      {n && (
        <>
          <h4 className="pf-h4">Numeric statistics <span className="muted">(finite values only: {formatNumber(n.finite_count)})</span></h4>
          <dl className="pf-grid">
            <Stat label="Mean" value={n.mean} />
            <Stat label="Median" value={n.median} />
            <Stat label="Std deviation" value={n.std} note={n.std === null ? "needs at least 2 values" : undefined} />
            <Stat label="Minimum" value={n.min} />
            <Stat label="Maximum" value={n.max} />
            <Stat label="25th percentile" value={n.p25} />
            <Stat label="50th percentile" value={n.p50} />
            <Stat label="75th percentile" value={n.p75} />
            <Stat label="IQR" value={n.iqr} />
            <Stat label="Zero values" value={n.zero_count} note="distinct from missing" />
            <Stat label="Negative values" value={n.negative_count} />
            <Stat label="Infinite values" value={n.infinite_count} note="excluded from statistics" />
          </dl>
          <h4 className="pf-h4">Potential outliers <span className="muted">(IQR rule)</span></h4>
          <dl className="pf-grid">
            <Stat label="Outliers" value={n.outliers.count} />
            <Stat label="Share of finite values" value={n.outliers.percent} format={formatPercent} />
            <Stat label="Lower fence" value={n.outliers.lower_bound} />
            <Stat label="Upper fence" value={n.outliers.upper_bound} />
            <Stat label="Extreme (beyond 3×IQR)" value={n.outliers.extreme_count} />
          </dl>
          {n.outliers.sample_values.length > 0 && (
            <div className="chips pf-chips">
              <span className="muted">Most extreme:</span>
              {n.outliers.sample_values.map((v, i) => (
                <span key={i} className="chip danger">{formatNumber(v)}</span>
              ))}
            </div>
          )}
          {n.outliers.note && <p className="muted">{n.outliers.note}</p>}
        </>
      )}

      {c && (
        <>
          <h4 className="pf-h4">Categories</h4>
          <dl className="pf-grid">
            <Stat
              label={c.modes.length > 1 ? "Modes" : "Mode"}
              value={c.modes.length ? c.modes.map(String).join(", ") : null}
              format={String}
              note={c.mode_note || (c.mode_count ? `${formatNumber(c.mode_count)} occurrences each` : undefined)}
            />
            <Stat label="Categories shown" value={c.shown_count} />
          </dl>
          <CategoryFrequencyChart categorical={c} />
        </>
      )}

      {p.datetime && (
        <>
          <h4 className="pf-h4">Dates</h4>
          <dl className="pf-grid">
            <Stat label="Earliest" value={p.datetime.earliest} format={String}
              note={p.datetime.ambiguous_day_month ? "day/month order is ambiguous" : undefined} />
            <Stat label="Latest" value={p.datetime.latest} format={String} />
            <Stat label="Unparsed values" value={p.datetime.unparsed_count} />
          </dl>
        </>
      )}

      {!n && !c && !p.datetime && (
        <p className="muted pf-reason">
          No value statistics are shown for this column ({detailLabel(p)}), because they would not be meaningful.
        </p>
      )}

      {p.notes.length > 0 && (
        <ul className="pf-notes">
          {p.notes.map((note) => <li key={note}>{note}</li>)}
        </ul>
      )}

      <h4 className="pf-h4">Findings for this column</h4>
      {findings.length === 0 ? (
        <p className="muted">No quality findings mention this column.</p>
      ) : (
        <ul className="pf-related">
          {findings.map((f) => (
            <li key={f.id}>
              <span className={`sev sev-${f.severity}`}>{SEVERITY_LABEL[f.severity]}</span> {f.title}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
