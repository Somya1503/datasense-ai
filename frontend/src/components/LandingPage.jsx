import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  FileSpreadsheet,
  ScanLine,
  Search,
  ShieldCheck,
  Upload,
} from "lucide-react";

const features = [
  { icon: ShieldCheck, title: "Data quality", text: "Locate missing values, exact duplicate records and placeholder values before they affect your work." },
  { icon: BarChart3, title: "Statistical summaries", text: "Read descriptive statistics and category distributions without leaving the report." },
  { icon: ScanLine, title: "Column profiling", text: "Understand data types, uniqueness, completeness and identifier-like fields column by column." },
  { icon: Search, title: "Outlier detection", text: "Review potential outliers using clear, IQR-based thresholds and evidence." },
];

const steps = [
  { icon: Upload, title: "Upload a CSV", text: "Bring a CSV up to 10 MB into a private analysis session." },
  { icon: FileSpreadsheet, title: "Inspect the profile", text: "See the shape, types, distributions and descriptive statistics of your dataset." },
  { icon: CheckCircle2, title: "Review the findings", text: "Follow quality evidence, explore relationships and export the resulting report." },
];

function Wordmark() {
  return (
    <span className="landing-wordmark" aria-label="DataSense AI">
      Data<em>Sense</em><small>EDITORIAL DATA LAB</small>
    </span>
  );
}

function ReportPreview() {
  return (
    <div className="report-preview" aria-label="Illustration of a DataSense AI analysis report">
      <div className="preview-topline"><span>DATASET ANALYSIS REPORT</span><span className="preview-live">● API ONLINE</span></div>
      <div className="preview-title">Customer orders, Q4</div>
      <div className="preview-ledger" aria-hidden="true">
        <div><span>ROWS</span><strong>2,418</strong></div>
        <div><span>COLUMNS</span><strong>12</strong></div>
        <div><span>MISSING</span><strong>3.4%</strong></div>
      </div>
      <div className="preview-body">
        <div className="preview-panel preview-quality">
          <span className="preview-label">DATA QUALITY</span>
          <div className="preview-bars"><i /><i /><i /><i /></div>
          <p>4 columns reviewed</p>
        </div>
        <div className="preview-panel preview-findings">
          <span className="preview-label">QUALITY FINDINGS</span>
          <div className="preview-finding"><b /> Missing value placeholder</div>
          <div className="preview-finding"><b /> Identifier-like numeric field</div>
        </div>
      </div>
      <div className="preview-table" aria-hidden="true">
        <span>column</span><span>type</span><span>missing</span><span>distinct</span>
        <span>region</span><span>text</span><span>0%</span><span>28</span>
        <span>order value</span><span>decimal</span><span>2.1%</span><span>2,366</span>
      </div>
    </div>
  );
}

export default function LandingPage({ onOpenWorkspace }) {
  return (
    <div className="landing-page">
      <header className="landing-header">
        <a className="landing-brand" href="#top"><Wordmark /></a>
        <nav className="landing-nav" aria-label="Primary navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#capabilities">Capabilities</a>
        </nav>
        <button className="btn btn-primary landing-workspace" onClick={onOpenWorkspace}>
          Open Workspace <ArrowRight size={16} aria-hidden="true" />
        </button>
      </header>

      <main id="top">
        <section className="landing-hero" aria-labelledby="landing-title">
          <div className="hero-copy">
            <p className="eyebrow">A clearer view of your data</p>
            <h1 id="landing-title">Turn raw CSVs into clear insights.</h1>
            <p className="hero-intro">DataSense AI helps you profile datasets, discover data-quality issues, explore statistics and understand the relationships in your CSVs.</p>
            <div className="landing-actions">
              <button className="btn btn-primary landing-primary" onClick={onOpenWorkspace}>
                Start Analyzing <ArrowRight size={17} aria-hidden="true" />
              </button>
              <a className="landing-text-link" href="#capabilities">Explore Capabilities <ArrowRight size={15} aria-hidden="true" /></a>
            </div>
            <p className="hero-note">CSV analysis up to 10 MB · Nothing is changed automatically</p>
          </div>
          <ReportPreview />
        </section>

        <section className="landing-section capabilities" id="capabilities" aria-labelledby="capabilities-title">
          <div className="section-intro">
            <p className="eyebrow">A practical research desk</p>
            <h2 id="capabilities-title">Start with the details that shape every analysis.</h2>
          </div>
          <div className="landing-feature-grid">
            {features.map(({ icon: Icon, title, text }) => (
              <article className="landing-feature" key={title}>
                <Icon size={22} strokeWidth={1.7} aria-hidden="true" />
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section how-it-works" id="how-it-works" aria-labelledby="how-title">
          <div className="section-intro">
            <p className="eyebrow">A simple reading workflow</p>
            <h2 id="how-title">A report that meets your dataset where it is.</h2>
          </div>
          <ol className="landing-steps">
            {steps.map(({ icon: Icon, title, text }, index) => (
              <li key={title}>
                <span className="step-number">{String(index + 1).padStart(2, "0")}</span>
                <Icon size={23} strokeWidth={1.6} aria-hidden="true" />
                <div><h3>{title}</h3><p>{text}</p></div>
              </li>
            ))}
          </ol>
          <p className="upload-limit"><FileSpreadsheet size={17} aria-hidden="true" /> CSV uploads are limited to 10 MB.</p>
        </section>

        <section className="landing-closing" aria-labelledby="closing-title">
          <p className="eyebrow">Ready when your dataset is</p>
          <h2 id="closing-title">Bring one CSV. Leave with a clearer picture.</h2>
          <p>Open the workspace to profile your data and review the evidence in one editorial report.</p>
          <button className="btn btn-primary landing-primary" onClick={onOpenWorkspace}>
            Start Analyzing <ArrowRight size={17} aria-hidden="true" />
          </button>
        </section>
      </main>

      <footer className="landing-footer"><Wordmark /><span>CSV profiling · pandas + FastAPI</span></footer>
    </div>
  );
}
