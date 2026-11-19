import { useEffect, useState } from "react";
import { api } from "../api";

type Geo = { countries: string[]; departments: { name: string; communes: string[] }[] };
let cache: Promise<Geo> | null = null;
function useGeo() {
  const [geo, setGeo] = useState<Geo | null>(null);
  useEffect(() => { cache = cache ?? api("/geo"); cache.then(setGeo).catch(() => { cache = null; }); }, []);
  return geo;
}

const Options = ({ geo }: { geo: Geo | null }) => (
  <>{geo?.departments.map((d) => <optgroup key={d.name} label={`Département : ${d.name}`}>{d.communes.map((c) => <option key={c} value={c}>{c}</option>)}</optgroup>)}</>
);

/** Pays (Bénin uniquement) + commune parmi les 77 communes. */
export function LocationPicker({ value, onChange, label = "Commune" }: { value: string; onChange: (v: string) => void; label?: string }) {
  const geo = useGeo();
  return (
    <>
      <label>Pays<select value="Bénin" disabled><option>Bénin</option></select></label>
      <label>{label}<select value={value} onChange={(e) => onChange(e.target.value)}><option value="">— Choisir une commune —</option><Options geo={geo} /></select></label>
    </>
  );
}

/** Version compacte pour les filtres de recherche. */
export function CommuneSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const geo = useGeo();
  return <select value={value} onChange={(e) => onChange(e.target.value)} aria-label="Commune"><option value="">Toutes les communes (Bénin)</option><Options geo={geo} /></select>;
}
