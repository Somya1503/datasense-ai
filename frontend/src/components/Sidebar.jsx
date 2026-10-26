import { useState } from "react";
import {
  BarChart3, LayoutDashboard, ShieldCheck, Tags,
  Link2, AlertTriangle, Table, Upload,
} from "lucide-react";

const NAV = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "quality", label: "Data Quality", icon: ShieldCheck },
  { id: "numeric", label: "Numeric Analysis", icon: BarChart3 },
  { id: "categorical", label: "Categorical Analysis", icon: Tags },
  { id: "correlations", label: "Correlations", icon: Link2 },
  { id: "outliers", label: "Outliers", icon: AlertTriangle },
  { id: "preview", label: "Data Preview", icon: Table },
];

export default function Sidebar({ hasResults, onReset }) {
  const [active, setActive] = useState("overview");

  const go = (id) => {
    setActive(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <aside className="sidebar">
      <div className="logo">
        <span className="logo-mark"><BarChart3 size={20} /></span>
        <div>
          <div className="logo-name">DataSense AI</div>
          <div className="logo-sub">Intelligent CSV Analyzer</div>
        </div>
      </div>

      <nav className="nav" aria-label="Main navigation">
        <div className="nav-label">Workspace</div>
        <button className="nav-item" onClick={() => { setActive("overview"); onReset(); }}>
          <Upload size={17} /> <span>New dataset</span>
        </button>

        <div className="nav-label">Report</div>
        {NAV.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`nav-item ${hasResults && active === id ? "active" : ""}`}
            disabled={!hasResults}
            onClick={() => go(id)}
          >
            <Icon size={17} /> <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-foot">DataSense AI · v0.1</div>
    </aside>
  );
}