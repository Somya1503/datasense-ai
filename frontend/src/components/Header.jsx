import { Wifi, WifiOff, RefreshCw, FileText, Download } from "lucide-react";

export default function Header({ title, filename, backendOnline, onReset, onExport }) {
  let label = "Checking API";
  let cls = "checking";
  let Icon = Wifi;
  if (backendOnline === true) { label = "API online"; cls = "online"; }
  if (backendOnline === false) { label = "API offline"; cls = "offline"; Icon = WifiOff; }

  return (
    <header className="header">
      <div className="header-title">
        <h1>{title}</h1>
        {filename && (
          <p className="file-chip"><FileText size={14} /> {filename}</p>
        )}
      </div>
      <div className="header-actions">
        {onExport && (
          <button className="btn" onClick={onExport}>
            <Download size={16} /> Export JSON
          </button>
        )}
        {onReset && (
          <button className="btn btn-primary" onClick={onReset}>
            <RefreshCw size={16} /> Upload another file
          </button>
        )}
        <span className={`status-pill ${cls}`}>
          <Icon size={14} /> {label}
        </span>
      </div>
    </header>
  );
}