export default function Section({ id, title, subtitle, icon: Icon, right, children }) {
  return (
    <section id={id} className="card section">
      <div className="section-head">
        <div className="section-title">
          {Icon && <span className="section-icon"><Icon size={18} /></span>}
          <div>
            <h2>{title}</h2>
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}