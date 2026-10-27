import { useCallback, useEffect, useState } from "react";
import { Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";
import { analyzeCsv, checkHealth } from "./api";
import { downloadFile } from "./utils/download";
import { formatNumber } from "./utils/format";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import UploadZone from "./components/UploadZone";
import SummaryCards from "./components/SummaryCards";
import DataQuality from "./components/DataQuality";
import ProfilingSuite from "./components/ProfilingSuite";
import NumericCharts from "./components/NumericCharts";
import CategoricalCharts from "./components/CategoricalCharts";
import CorrelationSection from "./components/CorrelationSection";
import OutliersSection from "./components/OutliersSection";
import PreviewTable from "./components/PreviewTable";

const MAX_BYTES = 10 * 1024 * 1024;

export default function Workspace() {
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [pendingName, setPendingName] = useState("");
  const [backendOnline, setBackendOnline] = useState(null); // null = checking

  useEffect(() => {
    let active = true;
    const run = async () => {
      const ok = await checkHealth();
      if (active) setBackendOnline(ok);
    };
    run();
    const timer = setInterval(run, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please choose a .csv file.");
      setStatus("error");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("That file is larger than 10 MB. Please choose a smaller CSV.");
      setStatus("error");
      return;
    }
    setPendingName(file.name);
    setStatus("loading");
    setError("");
    try {
      const data = await analyzeCsv(file);
      setResult(data);
      setStatus("success");
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }, []);

  const reset = () => {
    setStatus("idle");
    setResult(null);
    setError("");
    setPendingName("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const exportJson = () => {
    if (!result) return;
    const base = result.filename.replace(/\.csv$/i, "");
    downloadFile(`${base}-analysis.json`, JSON.stringify(result, null, 2), "application/json");
  };

  const analysis = result?.analysis;
  const showUpload = status === "idle" || status === "error";

  let title = "Upload dataset";
  let subtitle = null;
  if (status === "loading") { title = "Analyzing dataset"; subtitle = pendingName; }
  if (status === "success") { title = "Dataset analysis report"; subtitle = result.filename; }

  return (
    <div className="app">
      <Sidebar hasResults={status === "success"} onReset={reset} />
      <div className="main">
        <Header
          title={title}
          filename={subtitle}
          backendOnline={backendOnline}
          onReset={status === "success" ? reset : null}
          onExport={status === "success" ? exportJson : null}
        />
        <main className="content">
          {status === "error" && (
            <div className="alert error" role="alert">
              <AlertTriangle size={20} />
              <div className="alert-body">
                <strong>Analysis failed</strong>
                <p>{error}</p>
              </div>
              <button className="btn btn-sm" onClick={() => { setStatus("idle"); setError(""); }}>
                Dismiss
              </button>
            </div>
          )}

          {status === "loading" && (
            <div className="card loading-box" aria-live="polite">
              <Loader2 className="spin" size={32} />
              <strong>Analyzing {pendingName}</strong>
              <p className="muted">Computing statistics, column profiles, correlations and outliers…</p>
            </div>
          )}

          {showUpload && <UploadZone onFile={handleFile} />}

          {status === "success" && analysis && (
            <>
              <div className="alert ok" role="status">
                <CheckCircle2 size={20} />
                <div className="alert-body">
                  <strong>Analysis complete</strong>
                  <p>
                    {formatNumber(analysis.summary.rows)} rows and{" "}
                    {formatNumber(analysis.summary.columns)} columns processed from {result.filename}.
                  </p>
                </div>
              </div>
              <SummaryCards summary={analysis.summary} meta={analysis.meta} />
              <DataQuality
                columns={analysis.columns}
                summary={analysis.summary}
                hasBackendFindings={Array.isArray(analysis.quality_findings) && Boolean(analysis.quality_summary)}
              />
              <ProfilingSuite analysis={analysis} />
              <NumericCharts stats={analysis.numeric_stats} />
              <CategoricalCharts summary={analysis.categorical_summary} />
              <CorrelationSection data={analysis.correlations} />
              <OutliersSection outliers={analysis.outliers} />
              <PreviewTable
                rows={analysis.preview}
                columns={analysis.columns.map((c) => c.name)}
              />
            </>
          )}
        </main>
      </div>
    </div>
  );
}
