import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../App";
import { CommuneSelect } from "../components/LocationPicker";
import { TYPES, useRefs } from "../ui";

export function DegreeReq({ o }: { o: any }) {
  const d = o.degree;
  return (<p className="req"><b>Diplôme requis :</b> {d.level.label} <span className="tag mid">{d.mandatory ? "obligatoire" : "souhaité"}</span>
    {o.specialty && <> · <b>Spécialité :</b> {o.specialty.name}{o.specialty_required ? " (exigée)" : ""}</>}
    {o.experience.min_years > 0 && <> · <b>Expérience :</b> {o.experience.min_years} an(s) min.{o.experience.mandatory ? " (obligatoire)" : ""}</>}
    {d.accepted_titles.length > 0 && <> · Intitulés acceptés : {d.accepted_titles.join(", ")}</>}
    {o.required_skills.length > 0 && <><br /><b>Compétences obligatoires :</b> {o.required_skills.join(", ")}</>}
    {o.desired_skills.length > 0 && <> · <b>Souhaitées :</b> {o.desired_skills.join(", ")}</>}</p>);
}

export default function Opportunities() {
  const { user } = useAuth(); const refs = useRefs();
  const [q, setQ] = useState(""); const [type, setType] = useState(""); const [location, setLocation] = useState(""); const [level, setLevel] = useState(""); const [page, setPage] = useState(1);
  const [data, setData] = useState<any>(null); const [err, setErr] = useState(""); const [msg, setMsg] = useState("");
  const isGrad = user?.role === "graduate";
  const base = isGrad ? "/graduate/offers" : "/opportunities";
  const load = () => api(`${base}?page=${page}&q=${encodeURIComponent(q)}&type=${type}&location=${encodeURIComponent(location)}${!isGrad && level ? "&level_id=" + level : ""}`).then(setData).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, [page, type, location, level, isGrad]);
  const apply = async (id: number) => {
    const cover = prompt("Message de motivation (facultatif) :");
    if (cover === null) return;
    try { await api(`/graduate/offers/${id}/apply`, "POST", { cover_letter: cover }); setMsg("Candidature envoyée. Suivez-la dans « Mes candidatures »."); load(); } catch (e: any) { setMsg(e.message); }
  };
  return (<>
    <h2>Opportunités</h2>
    <form className="filters" onSubmit={(e) => { e.preventDefault(); setPage(1); load(); }}>
      <input placeholder="Mot-clé" value={q} onChange={(e) => setQ(e.target.value)} />
      <CommuneSelect value={location} onChange={(v) => { setLocation(v); setPage(1); }} />
      <select value={type} onChange={(e) => { setType(e.target.value); setPage(1); }}><option value="">Tous types</option>{Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
      {!isGrad && <select value={level} onChange={(e) => { setLevel(e.target.value); setPage(1); }}><option value="">Tous niveaux de diplôme</option>{refs?.levels.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}</select>}
      <button className="btn">Rechercher</button>
    </form>
    {isGrad && <p className="mut">Si vous avez activé le matching dans « Profil et visibilité », votre score de correspondance est calculé et expliqué critère par critère. Vous pouvez consulter les offres et candidater même si vous refusez le matching.</p>}
    {msg && <p className="ok">{msg}</p>}{err && <p className="err">{err}</p>}
    {!data ? <p>Chargement…</p> : data.items.length === 0 ? <div className="empty">Aucune opportunité ne correspond à votre recherche.</div> :
      <div className="list">{data.items.map((o: any) => (
        <div className="card" key={o.id}>
          <b>{o.title}</b> <span className="tag mid">{TYPES[o.type]}</span>{o.contract_type && <span className="tag mid">{o.contract_type}</span>}
          <span>{o.org.name}{o.org.verified ? " ✓" : ""} · {o.location || "—"}{o.duration ? ` · ${o.duration}` : ""}{o.deadline ? ` · avant le ${o.deadline}` : ""}</span>
          {o.salary && <div className="salary-pill"><b>Rémunération</b><span>{o.salary.type === "fixed" ? `${o.salary.min?.toLocaleString("fr-FR")} FCFA` : o.salary.type === "range" ? `${o.salary.min?.toLocaleString("fr-FR")} – ${o.salary.max?.toLocaleString("fr-FR")} FCFA` : o.salary.type === "unpaid" ? "Non rémunéré" : "À négocier"}{o.salary.type !== "unpaid" && o.salary.type !== "negotiable" ? ` / ${({month:"mois",day:"jour",hour:"heure",project:"mission"} as any)[o.salary.period]}` : ""}</span></div>}
          <DegreeReq o={o} />
          <p>{o.description}</p>
          <p><b>Atouts et avantages :</b> {o.benefits || "Non précisés par l'entreprise"}</p>
          {isGrad && o.my_match && <details><summary>Ma correspondance : {o.my_match.score}/100</summary>
            <ul className="mlist">{o.my_match.criteria.map((c: any) => <li key={c.key}><b>{c.label}</b> — {c.detail}</li>)}</ul></details>}
          {isGrad && (o.applied ? <span className="tag good">Déjà candidaté</span> : <button className="btn" onClick={() => apply(o.id)}>Candidater</button>)}
          {!user && <Link className="link" to="/connexion">Connectez-vous pour candidater</Link>}
        </div>))}</div>}
    {data && <div className="pager"><button disabled={page <= 1} onClick={() => setPage(page - 1)}>Précédent</button> Page {page} · {data.total} résultat(s) <button disabled={page * data.size >= data.total} onClick={() => setPage(page + 1)}>Suivant</button></div>}
  </>);
}
