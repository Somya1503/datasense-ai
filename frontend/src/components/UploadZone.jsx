import { useRef, useState } from "react";
import { UploadCloud, Download } from "lucide-react";
import { SAMPLE_CSV } from "../utils/format";
import { downloadFile } from "../utils/download";

const FEATURES = [
  ["Data quality", "Missing values, duplicate rows and column types"],
  ["Statistics", "Descriptive statistics for numeric columns, value counts for categories"],
  ["Relationships", "Pearson correlations between numeric columns"],
  ["Outliers", "IQR-based detection with the normal range per column"],
];

export default function UploadZone({ onFile }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const pick = (fileList) => {
    const file = fileList && fileList[0];
    if (file) onFile(file);
    if (inputRef.current) inputRef.current.value = ""; // allow re-selecting same file
  };

  const openPicker = () => inputRef.current?.click();

  return (
    <section className="upload-wrap">
      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files); }}
        onClick={openPicker}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openPicker(); } }}
      >
        <span className="drop-icon"><UploadCloud size={30} /></span>
        <h2>Drag and drop a CSV file here</h2>
        <p className="muted">or click to browse your computer. CSV only, up to 10 MB.</p>
        <span className="btn btn-primary">Select file</span>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          hidden
          onChange={(e) => pick(e.target.files)}
        />
      </div>

      <div className="feature-grid">
        {FEATURES.map(([name, text]) => (
          <div key={name} className="card feature">
            <strong>{name}</strong>
            <p className="muted">{text}</p>
          </div>
        ))}
      </div>

      <div className="card hint">
        <p className="muted">
          <strong>No dataset handy?</strong> Download a small sample containing missing
          values, a duplicate row and an outlier, then upload it here.
        </p>
        <button
          className="btn"
          onClick={() => downloadFile("sample_students.csv", SAMPLE_CSV, "text/csv")}
        >
          <Download size={16} /> Download sample CSV
        </button>
      </div>
    </section>
  );
}