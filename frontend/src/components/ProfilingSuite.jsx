import { useState } from "react";
import { Table, ShieldCheck } from "lucide-react";
import Section from "./Section";
import QualityMetrics from "./QualityMetrics";
import ProfileTable from "./ProfileTable";
import ColumnDetail from "./ColumnDetail";
import FindingsPanel from "./FindingsPanel";

// Renders two report sections ("Data profiling" and "Quality findings") that
// share one piece of state: which column is selected. Uses only the existing
// /analyze response; no extra request is made.
export default function ProfilingSuite({ analysis }) {
  const [selected, setSelected] = useState(null);

  const profiles = analysis.column_profiles;
  const summary = analysis.quality_summary;
  const findings = analysis.quality_findings || [];
  const available = Array.isArray(profiles) && profiles.length > 0 && summary;

  if (!available) {
    const reason = analysis.profiling_error
      || "This response contains no profiling data. If you just updated the project, restart the backend (uvicorn) so the new analyzer is loaded.";
    return (
      <>
        <Section id="profiling" title="Data Profiling" subtitle="Per-column statistics and types" icon={Table}>
          <div className="alert error" role="alert"><div className="alert-body"><strong>Profiling unavailable</strong><p>{reason}</p></div></div>
        </Section>
        <Section id="findings" title="Quality Findings" subtitle="Evidence-based issues and next steps" icon={ShieldCheck}>
          <div className="empty-small">Findings are produced together with profiling, so none are available.</div>
        </Section>
      </>
    );
  }

  const active = profiles.find((p) => p.name === selected) ?? profiles[0];
  const related = findings.filter((f) => f.affected_columns.includes(active.name));

  // From the findings panel: select the column, then bring its profile into view.
  const jumpToColumn = (name) => {
    setSelected(name);
    document.getElementById("profile-detail")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <>
      <Section
        id="profiling"
        title="Data Profiling"
        subtitle="Types, completeness and distribution for every column, computed from your file"
        icon={Table}
      >
        <QualityMetrics summary={summary} />
        <h3>Column overview</h3>
        <ProfileTable profiles={profiles} activeName={active.name} onSelect={setSelected} />
        <div id="profile-detail" className="pf-detail-wrap">
          <ColumnDetail profile={active} findings={related} />
        </div>
      </Section>

      <Section
        id="findings"
        title="Quality Findings"
        subtitle="Each finding lists its evidence and a suggested next step. Nothing is changed automatically."
        icon={ShieldCheck}
      >
        <FindingsPanel findings={findings} counts={summary.finding_counts} onSelectColumn={jumpToColumn} />
      </Section>
    </>
  );
}
