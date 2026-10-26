import { RefreshCw, Download } from "lucide-react";

export default function Header({ title, filename, backendOnline, onReset, onExport }) {
  let label = "Checking API";
  let cls = "checking";
  if (backendOnline === true) { label = "API online"; cls = "online"; }
  if (backendOnline === false) { label = "API offline"; cls = "offline"; }

  return (
    <header className="masthead">
      <div className="masthead-bar">
        <span className="eyebrow">{filename ? title : "DataSense Research Lab"}</span>
        <div className="header-actions">
          <span className={`status-pill ${cls}`}>
            <span className="dot" aria-hidden="true" /> {label}
          </span>
          {onExport && (
            <button className="btn" onClick={onExport}>
              <Download size={15} /> Export JSON
            </button>
          )}
          {onReset && (
            <button className="btn btn-primary" onClick={onReset}>
              <RefreshCw size={15} /> Upload another file
            </button>
          )}
        </div>
      </div>
      <h1>{filename || title}</h1>
    </header>
  );
}