import { ReactNode, useState } from "react";

/** Affiche une photographie locale ou un visuel local de secours. */
const DOCUMENTARY: Record<string, string> = {
  "about": "/images/about.jpg",
  "vision": "/images/vision.jpg",
  "graduates": "/images/graduates.jpg",
  "companies": "/images/companies.jpg",
  "schools": "/images/schools.jpg",
};
export function Photo({ name, alt, fallback }: { name: string; alt: string; fallback: ReactNode }) {
  const [remoteFailed, setRemoteFailed] = useState(false);
  const base = name.replace(/\.\w+$/, "");
  const remote = DOCUMENTARY[base];
  return (
    <div className="photo">
      {remote && !remoteFailed ? <img src={remote} alt={alt} loading="lazy" onError={() => setRemoteFailed(true)} /> : fallback}
    </div>
  );
}

const Sky = ({ id, a, b }: { id: string; a: string; b: string }) => (
  <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={a} /><stop offset="1" stopColor={b} /></linearGradient></defs>
);

export function FieldScene() {
  const rows = Array.from({ length: 9 }, (_, i) => i);
  return (
    <svg viewBox="0 0 800 560" role="img" aria-label="Champs cultivés au lever du soleil" preserveAspectRatio="xMidYMid slice">
      <Sky id="fs" a="#fef9c3" b="#bbf7d0" />
      <rect width="800" height="560" fill="url(#fs)" />
      <circle cx="610" cy="150" r="70" fill="#fde68a" opacity=".8" /><circle cx="610" cy="150" r="44" fill="#fbbf24" />
      <path d="M0 300 Q 150 230 300 290 T 600 270 T 800 300 V560 H0Z" fill="#86efac" />
      <path d="M0 340 Q 200 290 400 340 T 800 330 V560 H0Z" fill="#4ade80" />
      <path d="M0 400 Q 250 360 500 400 T 800 390 V560 H0Z" fill="#22c55e" />
      {rows.map((i) => <path key={i} d={`M${400 + (i - 4) * 14} 410 L${400 + (i - 4) * 120} 560`} stroke="#15803d" strokeWidth="5" opacity=".55" strokeLinecap="round" />)}
      {[0, 1, 2, 3, 4, 5].map((i) => <g key={i} transform={`translate(${90 + i * 120} ${430 + (i % 2) * 22})`}><path d="M0 40V4" stroke="#166534" strokeWidth="4" strokeLinecap="round" /><path d="M0 18c-16-2-22-12-22-22 14 0 22 8 22 22z" fill="#16a34a" /><path d="M0 8c16-2 22-12 22-22-14 0-22 8-22 22z" fill="#4ade80" /></g>)}
      <g transform="translate(120 250)"><rect x="0" y="22" width="56" height="40" fill="#fff" /><path d="M-8 24L28 -6l36 30z" fill="#b45309" /><rect x="22" y="38" width="12" height="24" fill="#92400e" /></g>
      <path d="M690 285v-60M690 255c-18 0-28-14-28-30 18 0 28 12 28 30zM690 240c18 0 28-14 28-30-18 0-28 12-28 30z" fill="#16a34a" stroke="#166534" strokeWidth="3" />
    </svg>
  );
}

function Person({ x, y, c }: { x: number; y: number; c: string }) {
  return <g transform={`translate(${x} ${y})`}><circle cx="0" cy="-34" r="16" fill="#fde2c8" /><path d="M-26 40q0-52 26-52t26 52z" fill={c} /></g>;
}

export function GraduateScene() {
  return (
    <svg viewBox="0 0 400 300" role="img" aria-label="Diplômé avec son profil">
      <Sky id="gs" a="#dcfce7" b="#f0fdf4" /><rect width="400" height="300" fill="url(#gs)" rx="20" />
      <circle cx="320" cy="70" r="40" fill="#bbf7d0" /><circle cx="70" cy="230" r="55" fill="#bbf7d0" opacity=".6" />
      <Person x={150} y={170} c="#16a34a" />
      <path d="M120 115l30-14 30 14-30 14z" fill="#0b1f17" /><path d="M136 124v14q14 8 28 0v-14" fill="none" stroke="#0b1f17" strokeWidth="3" /><path d="M180 115v18" stroke="#fbbf24" strokeWidth="3" />
      <g transform="translate(220 100)"><rect width="140" height="110" rx="14" fill="#fff" stroke="#bbf7d0" strokeWidth="2" /><circle cx="30" cy="30" r="14" fill="#86efac" /><rect x="52" y="20" width="70" height="8" rx="4" fill="#d1d5db" /><rect x="52" y="36" width="46" height="8" rx="4" fill="#e5e7eb" /><rect x="16" y="64" width="108" height="8" rx="4" fill="#dcfce7" /><rect x="16" y="64" width="78" height="8" rx="4" fill="#16a34a" /><rect x="16" y="84" width="26" height="14" rx="7" fill="#dcfce7" /><rect x="48" y="84" width="34" height="14" rx="7" fill="#bbf7d0" /></g>
    </svg>
  );
}

export function CompanyScene() {
  return (
    <svg viewBox="0 0 400 300" role="img" aria-label="Entreprise agricole et serre">
      <Sky id="cs" a="#fef9c3" b="#f0fdf4" /><rect width="400" height="300" fill="url(#cs)" rx="20" />
      <rect y="230" width="400" height="70" fill="#86efac" rx="0" />
      <g transform="translate(40 120)"><rect width="150" height="110" fill="#fff" stroke="#bbf7d0" strokeWidth="2" /><path d="M-10 0L75 -50l85 50z" fill="#16a34a" />{[0, 1, 2, 3].map((i) => <rect key={i} x={14 + i * 34} y="30" width="22" height="30" fill="#dcfce7" />)}<rect x="62" y="70" width="26" height="40" fill="#166534" /></g>
      <g transform="translate(230 130)"><path d="M0 100V40q50-60 100 0v60z" fill="#ecfccb" stroke="#65a30d" strokeWidth="3" />{[0, 1, 2, 3].map((i) => <g key={i} transform={`translate(${18 + i * 22} 100)`}><path d="M0 0V-34" stroke="#166534" strokeWidth="3" /><path d="M0-20c-10 0-14-8-14-14 8 0 14 6 14 14z" fill="#22c55e" /></g>)}</g>
      <g transform="translate(330 60)"><circle r="22" fill="#fbbf24" /><path d="M-8 0l6 6 12-12" stroke="#fff" strokeWidth="4" fill="none" strokeLinecap="round" /></g>
    </svg>
  );
}

export function SchoolScene() {
  return (
    <svg viewBox="0 0 400 300" role="img" aria-label="Établissement de formation">
      <Sky id="ss" a="#e0f2fe" b="#f0fdf4" /><rect width="400" height="300" fill="url(#ss)" rx="20" />
      <rect y="240" width="400" height="60" fill="#bbf7d0" />
      <g transform="translate(70 90)"><path d="M0 40L130 -10l130 50z" fill="#14532d" /><rect x="10" y="40" width="240" height="110" fill="#fff" stroke="#bbf7d0" strokeWidth="2" />{[0, 1, 2, 3, 4].map((i) => <rect key={i} x={30 + i * 42} y="55" width="14" height="70" fill="#dcfce7" />)}<rect x="112" y="100" width="36" height="50" fill="#16a34a" /><path d="M130 -10v-30" stroke="#14532d" strokeWidth="3" /><path d="M130-40h28v14h-28z" fill="#a3e635" /></g>
      <Person x={60} y={255} c="#16a34a" /><Person x={340} y={255} c="#65a30d" />
    </svg>
  );
}

export function VisionScene() {
  return (
    <svg viewBox="0 0 600 400" role="img" aria-label="Réseau d'acteurs de l'agriculture" preserveAspectRatio="xMidYMid slice">
      <Sky id="vs" a="#0b1f17" b="#14532d" /><rect width="600" height="400" fill="url(#vs)" />
      {[[300, 200, 70], [120, 90, 38], [480, 80, 38], [110, 310, 38], [490, 320, 38]].map(([x, y, r], i) => <g key={i}>{i > 0 && <line x1="300" y1="200" x2={x} y2={y} stroke="#a3e635" strokeWidth="2" strokeDasharray="6 8" />}<circle cx={x} cy={y} r={r} fill={i === 0 ? "#16a34a" : "#dcfce7"} /></g>)}
      <text x="300" y="206" textAnchor="middle" fill="#fff" fontSize="20" fontWeight="700">AgriConnect</text>
      {[["Diplômés", 120, 90], ["Entreprises", 480, 80], ["Écoles", 110, 310], ["Partenaires", 490, 320]].map(([e, x, y]: any) => <text key={e} x={x} y={y + 5} textAnchor="middle" fontSize="12" fontWeight="700" fill="#14532d">{e}</text>)}
    </svg>
  );
}
