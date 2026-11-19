import { useEffect, useState } from "react";
import { Routes, Route, Link, useParams } from "react-router-dom";
import { api, upload, download } from "../../api";
import { useAuth } from "../../App";
import { Shell } from "../Dashboard";
import { LocationPicker } from "../../components/LocationPicker";
import { useLoad, Loading, Msg, useAct, Tag, lab, dt, Table, Confirm, useRefs } from "../../ui";
import { Notifications, Account } from "./Common";

const NAV: [string, string, boolean?][] = [["", "Aperçu", true], ["/organisation", "Mon établissement"], ["/listes", "Listes transmises"], ["/candidats", "Candidats transmis"], ["/statistiques", "Statistiques"], ["/notifications", "Notifications"], ["/compte", "Mon compte"]];

function Banner({ org }: { org: any }) {
  if (org.status === "validated") return null;
  return <p className="warn banner"><b>{lab(org.status)} — </b>{org.status === "pending" ? "Votre établissement est en cours d'examen : vous pourrez transmettre des listes dès sa validation par AgriConnect." : (org.status_reason || "Contactez l'administration.")}</p>;
}

function Overview() {
  const { data, err } = useLoad<any>("/institution/me");
  if (!data) return <Loading err={err} data={data} />;
  return (<><h3>{data.org.name}</h3><Banner org={data.org} />
    <div className="cols"><div className="card stat"><b>{data.lists}</b><span>Liste(s) transmise(s)</span></div>
      <div className="card stat"><b>{data.transmitted_this_year}{data.annual_quota !== null ? " / " + data.annual_quota : ""}</b><span>Candidats transmis cette année{data.annual_quota !== null ? " (quota convenu)" : ""}</span></div></div>
    <div className="card"><b>Comment ça marche</b><ol><li>Vous transmettez la liste de vos diplômés (CSV ou Excel).</li><li>AgriConnect contrôle et valide les informations.</li><li>L'administration crée les comptes et envoie les invitations aux diplômés.</li><li>Les diplômés activent leur compte et complètent leur profil.</li></ol>
      <p className="mut">Vous restez responsable de l'exactitude des informations académiques transmises. L'utilisation de la plateforme est gratuite pour les établissements partenaires.</p></div></>);
}

function Org() {
  const { data, err, reload } = useLoad<any>("/institution/me"); const [f, setF] = useState<any>(null); const a = useAct();
  useEffect(() => { if (data?.org) setF({ ...data.org }); }, [data]);
  if (!data || !f) return <Loading err={err} data={data} />;
  const set = (k: string, v: any) => setF({ ...f, [k]: v });
  return (<><h3>Mon établissement</h3><Banner org={data.org} />
    <form className="card form wide" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/institution/org", "PUT", { name: f.name, description: f.description, sector: f.sector, city: f.city, country: "Bénin", website: f.website, phone: f.phone, registration_no: f.registration_no }); reload(); }, "Informations enregistrées."); }}>
      <Msg ok={a.ok} err={a.err} />
      <label>Nom de l'établissement<input required value={f.name} onChange={(e) => set("name", e.target.value)} /></label>
      <label>Description et filières<textarea rows={4} value={f.description} onChange={(e) => set("description", e.target.value)} /></label>
      <LocationPicker value={f.city} onChange={(v) => set("city", v)} />
      <label>Agrément / référence officielle<input value={f.registration_no} onChange={(e) => set("registration_no", e.target.value)} /></label>
      <label>Téléphone<input type="tel" value={f.phone ?? ""} onChange={(e) => set("phone", e.target.value)} /></label>
      <label>Site web<input type="url" placeholder="https://…" value={f.website ?? ""} onChange={(e) => set("website", e.target.value)} /></label>
      <button className="btn" disabled={a.busy}>Enregistrer</button></form></>);
}

function Lists() {
  const { data, err, reload } = useLoad<any[]>("/institution/lists"); const a = useAct(); const [f, setF] = useState({ title: "", academic_year: "" }); const [file, setFile] = useState<File | null>(null);
  if (!data) return <Loading err={err} data={data} />;
  const send = (e: React.FormEvent) => { e.preventDefault(); if (!file) return; const fd = new FormData(); fd.append("title", f.title); fd.append("academic_year", f.academic_year); fd.append("file", file);
    a.run(async () => { await upload("/institution/lists", fd); setF({ title: "", academic_year: "" }); setFile(null); reload(); }, "Liste transmise : AgriConnect va l'examiner."); };
  return (<><h3>Listes transmises</h3>
    <form className="card form wide" onSubmit={send}><Msg ok={a.ok} err={a.err} /><b>Transmettre une nouvelle liste</b>
      <label>Intitulé<input required minLength={2} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Ex. : Promotion 2026 — Licence professionnelle" /></label>
      <label>Année académique<input value={f.academic_year} onChange={(e) => setF({ ...f, academic_year: e.target.value })} placeholder="2025-2026" /></label>
      <label>Fichier CSV ou Excel (.xlsx), 1 000 lignes max.<input type="file" required accept=".csv,.xlsx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
      <p className="mut">Colonnes : nom_complet, email, telephone, diplome (intitulé exact), niveau, specialite, annee_obtention, mention, pays. <button type="button" className="link" onClick={() => download("/institution/lists/template.csv", "modele_liste_agriconnect.csv")}>Télécharger le modèle</button></p>
      <button className="btn" disabled={a.busy || !file}>Transmettre la liste</button></form>
    <Table head={["Liste", "Année", "Lignes", "À corriger", "Rejetées", "Comptes créés", "Statut", ""]} empty="Aucune liste transmise."
      rows={data.map((l) => [l.title, l.academic_year, l.counts.total, l.counts.invalid, l.counts.rejected, l.counts.account_created, <Tag s={l.status} />, <Link className="link" to={`/tableau-de-bord/listes/${l.id}`}>Ouvrir</Link>])} /></>);
}

function ListDetail() {
  const { id } = useParams(); const { data, err, reload } = useLoad<any>(`/institution/lists/${id}`); const refs = useRefs(); const a = useAct(); const [edit, setEdit] = useState<any>(null);
  if (!data) return <Loading err={err} data={data} />;
  const save = (e: React.FormEvent) => { e.preventDefault(); const { id: rid, ...body } = edit; a.run(async () => { await api(`/institution/lists/${id}/rows${rid ? "/" + rid : ""}`, rid ? "PUT" : "POST", { ...body, year: body.year ? Number(body.year) : null }); setEdit(null); reload(); }, "Ligne enregistrée."); };
  const blank = { full_name: "", email: "", phone: "", degree_title: "", level_code: "", specialty: "", year: "", honors: "", country: "Bénin" };
  return (<><Link to="/tableau-de-bord/listes">← Listes</Link><h3>{data.title} <Tag s={data.status} /></h3>
    {data.note && <p className="warn">Note de l'administration : {data.note}</p>}<Msg ok={a.ok} err={a.err} />
    <p className="mut">Les lignes à corriger ou rejetées peuvent être modifiées ; une ligne validée ne l'est plus (contactez AgriConnect). Un établissement ne peut pas créer de comptes : seule l'administration le fait après validation.</p>
    <button className="btn ghost" onClick={() => setEdit(blank)}>Ajouter une ligne</button>
    {edit && <form className="card form wide" onSubmit={save}>
      <label>Nom complet<input required value={edit.full_name} onChange={(e) => setEdit({ ...edit, full_name: e.target.value })} /></label>
      <label>Email<input type="email" required value={edit.email} onChange={(e) => setEdit({ ...edit, email: e.target.value })} /></label>
      <label>Intitulé exact du diplôme<input required value={edit.degree_title} onChange={(e) => setEdit({ ...edit, degree_title: e.target.value })} /></label>
      <label>Niveau<select required value={edit.level_code} onChange={(e) => setEdit({ ...edit, level_code: e.target.value })}><option value="">—</option>{refs?.levels.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</select></label>
      <label>Spécialité<input value={edit.specialty} onChange={(e) => setEdit({ ...edit, specialty: e.target.value })} /></label>
      <label>Année<input type="number" value={edit.year ?? ""} onChange={(e) => setEdit({ ...edit, year: e.target.value })} /></label>
      <label>Mention<input value={edit.honors} onChange={(e) => setEdit({ ...edit, honors: e.target.value })} /></label>
      <button className="btn">Enregistrer</button> <button type="button" className="link" onClick={() => setEdit(null)}>Annuler</button></form>}
    <Table head={["#", "Nom", "Email", "Diplôme", "Niveau", "Année", "Statut", "Message", ""]} empty="Aucune ligne."
      rows={data.rows.map((r: any) => [r.line_no, r.full_name, r.email, r.degree_title, r.level_code, r.year ?? "", <Tag s={r.status} />, r.message,
        ["invalid", "rejected", "pending"].includes(r.status) ? <><button className="link" onClick={() => setEdit({ ...r, year: r.year ?? "" })}>Corriger</button>
          <Confirm text="Supprimer cette ligne ?" onYes={() => a.run(async () => { await api(`/institution/lists/${id}/rows/${r.id}`, "DELETE"); reload(); }, "Supprimée.")}>Supprimer</Confirm></> : ""])} /></>);
}

function Candidates() {
  const { data, err } = useLoad<any[]>("/institution/candidates");
  if (!data) return <Loading err={err} data={data} />;
  return (<><h3>Candidats transmis</h3><p className="mut">Suivi du traitement et de l'activation. Les profils individuels ne sont pas communiqués à l'établissement.</p>
    <Table head={["Nom", "Email", "Diplôme", "Liste", "Traitement", "Compte"]} empty="Aucun candidat transmis."
      rows={data.map((r) => [r.full_name, r.email, r.degree_title, r.list_title, <Tag s={r.status} />, r.account_status ? <Tag s={r.account_status} /> : "—"])} /></>);
}

function Stats() {
  const { data, err } = useLoad<any>("/institution/stats");
  if (!data) return <Loading err={err} data={data} />;
  const Box = ({ title, o }: { title: string; o: Record<string, number> }) => <div className="card"><b>{title}</b>{Object.keys(o).length === 0 ? <p className="mut">—</p> : <ul>{Object.entries(o).map(([k, v]) => <li key={k}>{lab(k)} : {v}</li>)}</ul>}</div>;
  return (<><h3>Statistiques</h3><div className="cols"><div className="card stat"><b>{data.total_transmitted}</b><span>Candidats transmis</span></div><div className="card stat"><b>{data.accounts_created}</b><span>Comptes créés</span></div>
    <div className="card stat"><b>{data.accounts_activated}</b><span>Comptes activés{data.activation_rate !== null ? ` (${data.activation_rate} %)` : ""}</span></div><div className="card stat"><b>{data.profiles_available_now}</b><span>Diplômés disponibles</span></div></div>
    <div className="cols"><Box title="Par statut de traitement" o={data.by_status} /><Box title="Par niveau" o={data.by_level} /><Box title="Par année d'obtention" o={data.by_year} /></div><p className="mut">{data.note}</p></>);
}

export default function Institution() {
  const { user } = useAuth();
  return (<Shell title={user!.org?.name ?? "Espace établissement"} items={NAV}><Routes>
    <Route index element={<Overview />} /><Route path="organisation" element={<Org />} /><Route path="listes" element={<Lists />} /><Route path="listes/:id" element={<ListDetail />} />
    <Route path="candidats" element={<Candidates />} /><Route path="statistiques" element={<Stats />} /><Route path="notifications" element={<Notifications />} /><Route path="compte" element={<Account />} />
    <Route path="*" element={<p>Page introuvable.</p>} /></Routes></Shell>);
}
