export function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (typeof value !== "number") return String(value);
  if (Number.isInteger(value)) return value.toLocaleString();
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
}

export function shorten(text, max = 18) {
  const s = String(text);
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

export const SAMPLE_CSV = `name,age,score,city,passed
Asha,21,88.5,Bengaluru,yes
Ravi,22,92,Mumbai,yes
Meena,,75,Delhi,no
Karan,23,,Mumbai,no
Ravi,22,92,Mumbai,yes
Sita,22,81,Bengaluru,yes
John,24,300,Delhi,yes
Priya,21,79,,no
Arjun,23,85,Mumbai,yes
Neha,22,90,Delhi,yes
`;