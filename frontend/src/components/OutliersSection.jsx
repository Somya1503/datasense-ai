import { AlertTriangle, CheckCircle2 } from "lucide-react";
import Section from "./Section";
import { formatNumber, formatPercent } from "../utils/format";

export default function OutliersSection({ outliers }) {
  const entries = Object.entries(outliers || {});
  const flagged = entries.filter(([, o]) => o.count > 0).sort((a, b) => b[1].count - a[1].count);
  const skipped = entries.filter(([, o]) => o.count === 0 && o.note);
  const totalOutliers = flagged.reduce((sum, [, o]) => sum + o.count, 0);

  return (
    <Section
      id="outliers"
      title="Outlier Analysis"
      subtitle="Values outside 1.5 × IQR beyond the first and third quartiles"
      icon={AlertTriangle}
    >
      {entries.length === 0 ? (
        <div className="empty-small">No numeric columns to check for outliers.</div>
      ) : flagged.length === 0 ? (
        <div className="finding success">
          <CheckCircle2 size={18} />
          <div>
            <strong>No outliers detected</strong>
            <p>None of the {entries.length} numeric column(s) has values outside the IQR bounds.</p>
          </div>
        </div>
      ) : (
        <>
          <div className="finding warning">
            <AlertTriangle size={18} />
            <div>
              <strong>
                {formatNumber(totalOutliers)} potential outlier value{totalOutliers === 1 ? "" : "s"} in{" "}
                {flagged.length} column{flagged.length === 1 ? "" : "s"}
              </strong>
              <p>Potential outliers are not necessarily errors. Review them in context.</p>
            </div>
          </div>
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Column</th>
                  <th className="num">Outliers</th>
                  <th className="num">Share</th>
                  <th className="num">Lower bound</th>
                  <th className="num">Upper bound</th>
                  <th>Most extreme values</th>
                </tr>
              </thead>
              <tbody>
                {flagged.map(([name, o]) => (
                  <tr key={name}>
                    <td className="strong">{name}</td>
                    <td className="num">{formatNumber(o.count)}</td>
                    <td className="num">{formatPercent(o.percent)}</td>
                    <td className="num">{formatNumber(o.lower_bound)}</td>
                    <td className="num">{formatNumber(o.upper_bound)}</td>
                    <td>
                      <div className="chips">
                        {o.sample_values.map((v, i) => (
                          <span key={i} className="chip danger">{formatNumber(v)}</span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {skipped.length > 0 && (
        <div className="notes">
          {skipped.map(([name, o]) => (
            <p key={name} className="muted"><strong>{name}:</strong> {o.note}</p>
          ))}
        </div>
      )}
    </Section>
  );
}