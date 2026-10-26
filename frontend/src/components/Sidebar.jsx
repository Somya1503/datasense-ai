import { useState } from "react";

const NAV = [
  { id: "overview", label: "Overview" },
  { id: "quality", label: "Data quality" },
  { id: "numeric", label: "Numeric analysis" },
  { id: "categorical", label: "Categorical analysis" },
  { id: "correlations", label: "Correlations" },
  { id: "outliers", label: "Outliers" },
  { id: "preview", label: "Data preview" },
];

export default function Sidebar({ hasResults, onReset }) {
  const [active, setActive] = useState("overview");

  const go = (id) => {
    setActive(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <aside className="sidebar">
      <div className="wordmark">
        <div className="wordmark-name">Data<em>Sense</em></div>
        <div className="wordmark-sub">Editorial Data Lab</div>
        <p className="wordmark-line">A research desk for CSV data: profile, test and read a dataset in one report.</p>
      </div>

      <button className="new-btn" onClick={() => { setActive("overview"); onReset(); }}>
        <span aria-hidden="true">+</span> New dataset
      </button>

      <nav className="toc" aria-label="Report contents">
        <div className="toc-label">Contents</div>
        {NAV.map(({ id, label }, i) => (
          <button
            key={id}
            className={`toc-item ${hasResults && active === id ? "active" : ""}`}
            disabled={!hasResults}
            onClick={() => go(id)}
          >
            <span className="toc-no">{String(i + 1).padStart(2, "0")}</span>
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-foot">Vol. 1 · pandas + FastAPI</div>
    </aside>
  );
}