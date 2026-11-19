import { useState } from "react";
import { Routes, Route, Link } from "react-router-dom";
import { api, upload, download } from "../../api";
import { Shell } from "../Dashboard";
import { LocationPicker } from "../../components/LocationPicker";
import { useLoad, Loading, Msg, useAct, Tag, lab, dt, dtt, LevelSelect, SpecialtySelect, Confirm, L } from "../../ui";
import Opportunities from "../Opportunities";
import { Notifications, Account } from "./Common";

const NAV: [string, string, boolean?][] = [["", "Aperçu", true], ["/profil", "Profil et visibilité"], ["/formation", "Formation et diplômes"], ["/parcours", "Expériences et compétences"],
  ["/documents", "CV"], ["/offres", "Offres pour moi"], ["/matching", "Mes correspondances"], ["/candidatures", "Mes candidatures"], ["/evaluations", "Évaluations"], ["/notifications", "Notifications"], ["/compte", "Mon compte"]];

function Overview() {
  const { data: p, err } = useLoad<any>("/graduate/profile");
  const { data: apps } = useLoad<any[]>("/graduate/applications");
  if (!p) return <Loading err={err} data={p} />;
  const r = p.reputation;
  return (<><h3>Bienvenue {p.full_name}</h3>
    <div className="cols">
      <div className="card stat"><b>{p.completeness} %</b><span>Profil complété</span><div className="bar"><i style={{ width: p.completeness + "%" }} /></div></div>
      <div className="card stat"><b>{r.score}/100</b><span>Réputation {r.provisional ? "(provisoire)" : ""}</span></div>
      <div className="card stat"><b>{p.experience.category}</b><span>{p.experience.years} an(s) d'expérience</span></div>
      <div className="card stat"><b>{apps?.length ?? 0}</b><span>Candidature(s)</span></div></div>
    <p className="mut">{r.note} Le niveau de diplôme n'entre pas dans le score de réputation : il est affiché séparément.</p>
    {p.completeness < 100 && <div className="card"><b>Pour être mieux repéré :</b> complétez votre titre, votre présentation, vos expériences, vos compétences, vos réalisations et ajoutez votre CV.</div>}
    <div className="card"><b>Visibilité :</b> {p.visible ? "votre profil peut être trouvé par les entreprises abonnées (sans nom ni coordonnées avant consultation)." : "votre profil n'est pas visible des entreprises."}</div>
    <div className="card cv-summary"><div><b>Mon CV</b><p className="mut">{p.has_cv ? `Document enregistré : ${p.cv_name}` : "Aucun CV déposé pour le moment."}</p></div><Link className="btn ghost" to="/tableau-de-bord/documents">{p.has_cv ? "Gérer mon CV" : "Ajouter mon CV"}</Link></div></>);
}

function Profile() {
  const { data, err, reload } = useLoad<any>("/graduate/profile"); const [f, setF] = useState<any>(null); const a = useAct();
  if (data && !f) setF(data);
  if (!f) return <Loading err={err} data={data} />;
  const save = (e: React.FormEvent) => { e.preventDefault(); a.run(async () => { await api("/graduate/profile", "PUT", { headline: f.headline, bio: f.bio, location: f.location, phone: f.phone, availability: f.availability,
    available_from: f.available_from || null, visible: f.visible, show_contact: f.show_contact, show_cv: f.show_cv, matching_opt_in: f.matching_opt_in }); reload(); }, "Profil enregistré."); };
  const set = (k: string, v: any) => setF({ ...f, [k]: v });
  return (<><h3>Mon profil</h3><form className="card form wide" onSubmit={save}><Msg ok={a.ok} err={a.err} />
    <label>Titre professionnel<input value={f.headline} onChange={(e) => set("headline", e.target.value)} /></label>
    <label>Présentation<textarea rows={4} value={f.bio} onChange={(e) => set("bio", e.target.value)} /></label>
    <LocationPicker value={f.location} onChange={(v) => set("location", v)} />
    <label>Téléphone<input value={f.phone} onChange={(e) => set("phone", e.target.value)} /></label>
    <label>Disponibilité<select value={f.availability} onChange={(e) => set("availability", e.target.value)}>
      {["available", "employed_open", "temporary_mission", "unavailable"].map((k) => <option key={k} value={k}>{L[k]}</option>)}</select></label>
    {f.availability === "temporary_mission" && <label>Disponible à partir du<input type="date" value={f.available_from || ""} onChange={(e) => set("available_from", e.target.value)} /></label>}
    <fieldset><legend>Visibilité (vous gardez le contrôle)</legend>
      <label className="check"><input type="checkbox" checked={f.visible} onChange={(e) => set("visible", e.target.checked)} /> Mon profil peut être trouvé par les entreprises abonnées</label>
      <label className="check"><input type="checkbox" checked={f.show_contact} onChange={(e) => set("show_contact", e.target.checked)} /> Mes coordonnées sont visibles (formule Business uniquement)</label>
      <label className="check"><input type="checkbox" checked={f.show_cv} onChange={(e) => set("show_cv", e.target.checked)} /> Mon CV est téléchargeable (formule Business, après consultation du profil)</label>
      <label className="check consent"><input type="checkbox" checked={f.matching_opt_in} onChange={(e) => set("matching_opt_in", e.target.checked)} /> J’accepte que mon profil soit évalué par le moteur de correspondance pour recevoir des opportunités adaptées.</label></fieldset>
    <p className="mut">Le consentement au matching est facultatif et indépendant de la visibilité du profil. Vous pouvez le retirer à tout moment sans perdre la possibilité de consulter les offres ou de candidater manuellement.</p>
    <p className="mut">Dernière mise à jour de la disponibilité : {dt(data.availability_updated_at)}. Les candidatures que vous envoyez donnent toujours accès à votre nom, votre email et votre CV à l'entreprise concernée.</p>
    <button className="btn" disabled={a.busy}>Enregistrer</button></form></>);
}

function Training() {
  const { data, err, reload } = useLoad<any>("/graduate/profile"); const a = useAct();
  const empty = { title: "", level_id: "", specialty_id: null as any, institution_name: "", year: "", honors: "" };
  const [f, setF] = useState<any>(empty);
  if (!data) return <Loading err={err} data={data} />;
  const add = (e: React.FormEvent) => { e.preventDefault(); a.run(async () => { await api("/graduate/degrees", "POST", { ...f, level_id: Number(f.level_id), year: f.year ? Number(f.year) : null }); setF(empty); reload(); }, "Diplôme ajouté : il sera vérifié par l'administration."); };
  return (<><h3>Formation et diplômes</h3>
    <p className="mut">Chaque diplôme est enregistré avec son intitulé exact. Un DEAT n'est jamais assimilé automatiquement à une Licence. Les diplômes transmis par votre établissement sont vérifiés et non modifiables ; ceux que vous ajoutez sont « déclarés » jusqu'à vérification.</p>
    {data.degrees.map((d: any) => (<div className="card" key={d.id}><b>{d.title}</b> <Tag s={d.status} />
      <span>{d.level.label}{d.specialty ? " · " + d.specialty : ""}{d.institution_name ? " · " + d.institution_name : ""}{d.year ? " · " + d.year : ""}{d.honors ? " · " + d.honors : ""}</span>
      {d.source === "institution" ? <small className="mut">Transmis par l'établissement</small> : d.status !== "verified" && <Confirm text="Supprimer ce diplôme ?" onYes={() => a.run(async () => { await api(`/graduate/degrees/${d.id}`, "DELETE"); reload(); }, "Supprimé.")}>Supprimer</Confirm>}</div>))}
    <h4>Ajouter un diplôme</h4><form className="card form wide" onSubmit={add}><Msg ok={a.ok} err={a.err} />
      <label>Intitulé exact (comme sur le document)<input required minLength={3} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></label>
      <LevelSelect required value={f.level_id} onChange={(v) => setF({ ...f, level_id: v })} />
      <SpecialtySelect value={f.specialty_id} onChange={(v) => setF({ ...f, specialty_id: v })} />
      <label>Établissement<input value={f.institution_name} onChange={(e) => setF({ ...f, institution_name: e.target.value })} /></label>
      <label>Année d'obtention<input type="number" min={1950} max={2100} value={f.year} onChange={(e) => setF({ ...f, year: e.target.value })} /></label>
      <label>Mention<input value={f.honors} onChange={(e) => setF({ ...f, honors: e.target.value })} /></label>
      <button className="btn" disabled={a.busy}>Ajouter</button></form></>);
}

function Career() {
  const { data, err, reload } = useLoad<any>("/graduate/profile"); const a = useAct();
  const e0 = { kind: "job", organization: "", role: "", sector: "", start_date: "", end_date: "", description: "" };
  const [e, setE] = useState<any>(e0); const [skill, setSkill] = useState(""); const [ach, setAch] = useState({ title: "", description: "", year: "" });
  if (!data) return <Loading err={err} data={data} />;
  return (<><h3>Expériences, compétences et réalisations</h3><Msg ok={a.ok} err={a.err} />
    <h4>Expériences</h4>
    {data.experiences.map((x: any) => <div className="card" key={x.id}><b>{x.role}</b> — {x.organization} <Tag s={x.status} /><span>{lab(x.kind)} · {dt(x.start_date)} → {x.end_date ? dt(x.end_date) : "en cours"}</span>{x.description && <p>{x.description}</p>}
      <Confirm text="Supprimer cette expérience ?" onYes={() => a.run(async () => { await api(`/graduate/experiences/${x.id}`, "DELETE"); reload(); }, "Supprimée.")}>Supprimer</Confirm></div>)}
    <form className="card form wide" onSubmit={(ev) => { ev.preventDefault(); a.run(async () => { await api("/graduate/experiences", "POST", { ...e, end_date: e.end_date || null }); setE(e0); reload(); }, "Expérience ajoutée (à vérifier par l'administration)."); }}>
      <label>Nature<select value={e.kind} onChange={(x) => setE({ ...e, kind: x.target.value })}><option value="job">Emploi</option><option value="internship">Stage</option><option value="apprenticeship">Alternance</option><option value="mission">Mission</option></select></label>
      <label>Organisation<input required value={e.organization} onChange={(x) => setE({ ...e, organization: x.target.value })} /></label>
      <label>Fonction<input required value={e.role} onChange={(x) => setE({ ...e, role: x.target.value })} /></label>
      <label>Début<input type="date" required value={e.start_date} onChange={(x) => setE({ ...e, start_date: x.target.value })} /></label>
      <label>Fin (vide = en cours)<input type="date" value={e.end_date} onChange={(x) => setE({ ...e, end_date: x.target.value })} /></label>
      <label>Responsabilités et résultats<textarea rows={3} value={e.description} onChange={(x) => setE({ ...e, description: x.target.value })} /></label>
      <button className="btn" disabled={a.busy}>Ajouter l'expérience</button></form>
    <h4>Compétences</h4><div className="chips">{data.skills.map((s: any) => <span className="chip" key={s.id}>{s.name}{s.verified ? " ✓" : ""} <button className="x" aria-label={"Retirer " + s.name} onClick={() => a.run(async () => { await api(`/graduate/skills/${s.id}`, "DELETE"); reload(); }, "Retirée.")}>×</button></span>)}</div>
    <form className="filters" onSubmit={(ev) => { ev.preventDefault(); a.run(async () => { await api("/graduate/skills", "POST", { name: skill }); setSkill(""); reload(); }, "Compétence ajoutée."); }}>
      <input required minLength={2} placeholder="Ex. : irrigation goutte-à-goutte" value={skill} onChange={(x) => setSkill(x.target.value)} /><button className="btn">Ajouter</button></form>
    <p className="mut">✓ = compétence vérifiée par l'administration.</p>
    <h4>Projets et réalisations</h4>
    {data.achievements.map((x: any) => <div className="card" key={x.id}><b>{x.title}</b>{x.year ? ` (${x.year})` : ""}<p>{x.description}</p>
      <Confirm text="Supprimer ?" onYes={() => a.run(async () => { await api(`/graduate/achievements/${x.id}`, "DELETE"); reload(); }, "Supprimée.")}>Supprimer</Confirm></div>)}
    <form className="card form wide" onSubmit={(ev) => { ev.preventDefault(); a.run(async () => { await api("/graduate/achievements", "POST", { ...ach, year: ach.year ? Number(ach.year) : null }); setAch({ title: "", description: "", year: "" }); reload(); }, "Réalisation ajoutée."); }}>
      <label>Titre<input required value={ach.title} onChange={(x) => setAch({ ...ach, title: x.target.value })} /></label>
      <label>Description<textarea rows={2} value={ach.description} onChange={(x) => setAch({ ...ach, description: x.target.value })} /></label>
      <label>Année<input type="number" value={ach.year} onChange={(x) => setAch({ ...ach, year: x.target.value })} /></label>
      <button className="btn">Ajouter</button></form></>);
}

function Documents() {
  const { data, err, reload } = useLoad<any>("/graduate/profile"); const a = useAct();
  if (!data) return <Loading err={err} data={data} />;
  return (<><h3>Mon CV</h3><Msg ok={a.ok} err={a.err} />
    <div className="card">{data.has_cv ? <><b>{data.cv_name}</b> <button className="link" onClick={() => a.run(() => download("/graduate/cv", data.cv_name), "Téléchargé.")}>Télécharger</button>
      <Confirm text="Supprimer le CV ?" onYes={() => a.run(async () => { await api("/graduate/cv", "DELETE"); reload(); }, "CV supprimé.")}>Supprimer</Confirm></> : <span>Aucun CV déposé.</span>}</div>
    <div className="card form"><label>Déposer un CV (PDF ou DOCX, 5 Mo max.)<input type="file" accept=".pdf,.docx" onChange={(e) => { const file = e.target.files?.[0]; if (!file) return; const fd = new FormData(); fd.append("file", file);
      a.run(async () => { await upload("/graduate/cv", fd); reload(); }, "CV enregistré."); e.target.value = ""; }} /></label>
      <p className="mut">Le fichier est contrôlé (type et contenu), stocké hors du site public et accessible uniquement aux personnes autorisées.</p></div></>);
}

function Evaluations() {
  const { data, err, reload } = useLoad<any>("/graduate/evaluations"); const { data: cols } = useLoad<any[]>("/graduate/collaborations"); const a = useAct();
  const [resp, setResp] = useState<Record<number, string>>({});
  if (!data) return <Loading err={err} data={data} />;
  const DIM: [string, string][] = [["technical", "Technique"], ["deadlines", "Délais"], ["adaptability", "Adaptabilité"], ["professionalism", "Professionnalisme"], ["teamwork", "Esprit d'équipe"], ["results", "Résultats"]];
  return (<><h3>Évaluations et recommandations reçues</h3><Msg ok={a.ok} err={a.err} />
    <p className="mut">Seules des collaborations vérifiées donnent lieu à une évaluation. Vous pouvez répondre ou contester une évaluation inexacte, abusive ou sans collaboration réelle : l'administration l'examine (elle est écartée du calcul pendant l'examen).</p>
    {data.evaluations.length === 0 ? <div className="empty">Aucune évaluation pour le moment.</div> : data.evaluations.map((e: any) => (
      <div className="card" key={e.id}><b>{e.company}</b> — {e.mission} <Tag s={e.status} /> <span>Moyenne {e.average}/5 · {dt(e.created_at)}</span>
        <small>{DIM.map(([k, l]) => `${l} ${e[k]}`).join(" · ")}</small>{e.comment && <p>« {e.comment} »</p>}{e.response && <p><b>Votre réponse :</b> {e.response}</p>}
        {!e.response && <div className="filters"><input placeholder="Votre réponse" value={resp[e.id] || ""} onChange={(x) => setResp({ ...resp, [e.id]: x.target.value })} />
          <button className="btn ghost" onClick={() => a.run(async () => { await api(`/graduate/evaluations/${e.id}/respond`, "POST", { response: resp[e.id] || "" }); reload(); }, "Réponse publiée.")}>Répondre</button></div>}
        {e.status === "published" && <button className="link" onClick={() => { const reason = prompt("Motif de la contestation (10 caractères min.) :"); if (reason) a.run(async () => { await api(`/graduate/evaluations/${e.id}/contest`, "POST", { kind: "evaluation", target_id: e.id, reason }); reload(); }, "Contestation transmise à l'administration."); }}>Contester</button>}</div>))}
    <h4>Recommandations</h4>{data.recommendations.length === 0 ? <div className="empty">Aucune recommandation.</div> : data.recommendations.map((r: any) => <div className="card" key={r.id}><b>{r.company}</b><p>{r.text}</p><small>{dt(r.created_at)} — visible de l'entreprise auprès de laquelle vous candidatez.</small></div>)}
    <h4>Mes collaborations</h4>{cols && (cols.length === 0 ? <div className="empty">Aucune collaboration.</div> : cols.map((c) => <div className="card" key={c.id}><b>{c.title}</b> — {c.company} <Tag s={c.status} /><span>{dt(c.start_date)} → {c.end_date ? dt(c.end_date) : "en cours"}</span></div>))}</>);
}

function Matching() {
  const { data, err } = useLoad<any[]>("/graduate/matching");
  if (!data) return <Loading err={err} data={data} />;
  return <><h3>Mes correspondances</h3><p className="mut">Classement indicatif calculé après validation des offres. Votre rang et vos critères vous sont personnels : les profils des autres candidats ne sont jamais révélés.</p>
    {data.length === 0 ? <div className="empty">Aucune correspondance enregistrée. Vérifiez votre consentement dans « Profil et visibilité » et complétez vos informations professionnelles.</div> : data.map((m) => <div className="card" key={m.id}><b>{m.title}</b><div className="kpis"><div><small>Votre score</small><b>{m.score}/100</b></div><div><small>Votre rang indicatif</small><b>{m.rank} / {m.total}</b></div><div><small>Calculé le</small><b>{dt(m.created_at)}</b></div></div><details><summary>Comprendre ma correspondance</summary><ul className="mlist">{m.criteria.map((c: any) => <li key={c.key}><b>{c.label}</b> — {c.detail}</li>)}</ul></details><Link className="link" to="/tableau-de-bord/offres">Consulter les offres</Link></div>)}</>;
}

function Applications() {
  const { data, err, reload } = useLoad<any[]>("/graduate/applications"); const a = useAct();
  if (!data) return <Loading err={err} data={data} />;
  return (<><h3>Mes candidatures</h3><Msg ok={a.ok} err={a.err} />
    {data.length === 0 ? <div className="empty">Aucune candidature pour le moment.</div> : data.map((x) => (
      <div className="card" key={x.id}><b>{x.opportunity.title}</b> · {x.opportunity.org} <Tag s={x.status} />
        <span>Diplôme requis : {x.opportunity.degree_level} · déposée le {dt(x.created_at)}</span>
        <ol className="timeline">{x.history.map((h: any, i: number) => <li key={i}><b>{lab(h.status)}</b> <small>{dtt(h.created_at)}</small>{h.comment && <span> — {h.comment}</span>}</li>)}</ol>
        {!["accepted", "rejected", "withdrawn"].includes(x.status) && <Confirm text="Retirer cette candidature ?" onYes={() => a.run(async () => { await api(`/graduate/applications/${x.id}/withdraw`, "POST"); reload(); }, "Candidature retirée.")}>Retirer</Confirm>}</div>))}</>);
}

export default function Graduate() {
  return (<Shell title="Espace diplômé" items={NAV}><Routes>
    <Route index element={<Overview />} /><Route path="profil" element={<Profile />} /><Route path="formation" element={<Training />} /><Route path="parcours" element={<Career />} />
    <Route path="documents" element={<Documents />} /><Route path="offres" element={<Opportunities />} /><Route path="matching" element={<Matching />} /><Route path="candidatures" element={<Applications />} />
    <Route path="evaluations" element={<Evaluations />} /><Route path="notifications" element={<Notifications />} /><Route path="compte" element={<Account />} />
    <Route path="*" element={<p>Page introuvable.</p>} /></Routes></Shell>);
}
