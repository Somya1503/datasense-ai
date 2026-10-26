import { Table } from "lucide-react";
import Section from "./Section";

export default function PreviewTable({ rows, columns }) {
  return (
    <Section
      id="preview"
      title="Data Preview"
      subtitle={`First ${rows?.length || 0} rows returned by the backend. Scroll horizontally for wide datasets.`}
      icon={Table}
    >
      {!rows || rows.length === 0 ? (
        <div className="empty-small">No preview rows available.</div>
      ) : (
        <div className="table-scroll preview-scroll">
          <table className="table">
            <thead>
              <tr>
                <th className="row-index">#</th>
                {columns.map((c) => <th key={c}>{c}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  <td className="row-index">{i + 1}</td>
                  {columns.map((c) => {
                    const v = row[c];
                    return v === null || v === undefined ? (
                      <td key={c} className="null-cell">null</td>
                    ) : (
                      <td key={c}>{String(v)}</td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}