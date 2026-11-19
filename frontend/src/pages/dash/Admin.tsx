import { useState } from "react";
import { Routes, Route, Link, useParams } from "react-router-dom";
import { api, saveText } from "../../api";
import { Shell } from "../Dashboard";
import { useLoad, Loading, Msg, useAct, Tag, lab, dt, dtt, xof, Table, Confirm } from "../../ui";
import { Notifications, Account } from "./Common";

const NAV: [string, string, boolean?][] = [["", "Aperçu", true], ["/organisations", "Entreprises et établissements"], ["/listes", "Listes des établissements"], ["/utilisateurs", "Utilisateurs"],
  ["/verifications", "Vérifications"], ["/referentiels", "Diplômes et spécialités"], ["/moderation", "Offres et signalements"], ["/abonnements", "Abonnements et paiements"],
  ["/parametres", "Paramètres"], ["/journal", "Journal et messages"], ["/notifications", "Notifications"], ["/compte", "Mon compte"]];
const localLink = (raw: string) => { try { const u = new URL(raw, window.location.origin); return `${window.location.origin}${u.pathname}${u.search}`; } catch { return raw; } };

function Overview() {
  const { data: d, err } = useLoad<any>("/admin/dashboard");
  if (!d) return <Loading err={err} data={d} />;
  const T = d.todo;
  const todo: [string, number, string][] = [["Dossiers d'organisations à examiner", T.orgs_pending, "/organisations"], ["Listes à traiter", T.lists_to_review, "/listes"], ["Diplômes à vérifier", T.degrees_to_verify, "/verifications"],
    ["Collaborations à vérifier", T.collaborations_pending, "/verifications"], ["Signalements ouverts", T.reports_open, "/moderation"], ["Paiements en attente", T.payments_pending, "/abonnements"]];
  const Dist = ({ title, o }: { title: string; o: Record<string, number> }) => <div className="card"><b>{title}</b>{Object.keys(o).length === 0 ? <p className="mut">—</p> : <ul>{Object.entries(o).map(([k, v]) => <li key={k}>{lab(k)} : {v}</li>)}</ul>}</div>;
  return (<><h3>Tableau de bord</h3>
    <div className="cols">{todo.map(([l, n, to]) => <Link key={l} to={"/tableau-de-bord" + to} className={"card stat " + (n ? "unread" : "")}><b>{n}</b><span>{l}</span></Link>)}</div>
    <div className="cols"><div className="card stat"><b>{d.users.graduate}</b><span>Diplômés</span></div><div className="card stat"><b>{d.users.company}</b><span>Entreprises</span></div><div className="card stat"><b>{d.users.institution}</b><span>Établissements</span></div>
      <div className="card stat"><b>{d.offers_published}</b><span>Offres publiées</span></div><div className="card stat"><b>{d.applications}</b><span>Candidatures</span></div><div className="card stat"><b>{d.active_subscriptions}</b><span>Abonnements actifs</span></div></div>
    <div className="cols"><div className="card stat"><b>{xof(d.revenue_xof_live)}</b><span>Encaissements réels</span></div><div className="card stat"><b>{xof(d.revenue_xof_demo)}</b><span>Encaissements internes</span></div></div>
    <div className="cols"><Dist title="Comptes diplômés" o={d.graduates_by_status} /><Dist title="Entreprises" o={d.orgs_by_status.company} /><Dist title="Établissements" o={d.orgs_by_status.institution} /><Dist title="Listes" o={d.lists_by_status} /><Dist title="Abonnements par formule" o={d.subscriptions_by_plan} /></div>
    <p className="mut">Mode de paiement : <b>{d.payment_mode}</b> · Envoi de courriels : <b>{d.smtp_enabled ? "configuré" : "non configuré (les invitations s'affichent à l'écran)"}</b></p></>);
}

function Orgs() {
  const [kind, setKind] = useState(""); const [status, setStatus] = useState("");
  const { data, err, reload } = useLoad<any[]>(`/admin/orgs?kind=${kind}&status=${status}`); const a = useAct();
  const act = (o: any, st: string) => { let reason = ""; if (st === "rejected" || st === "suspended") { reason = prompt("Motif (visible de l'organisation) :") || ""; if (!reason) return; }
    let quota: number | undefined; if (st === "validated" && o.kind === "institution") { const q = prompt("Quota annuel de talents convenu (vide = aucun) :", o.annual_quota ?? ""); if (q === null) return; quota = q === "" ? undefined : Number(q); }
    a.run(async () => { await api(`/admin/orgs/${o.id}/status`, "POST", { status: st, reason, annual_quota: quota ?? null }); reload(); }, "Statut mis à jour : l'organisation est notifiée."); };
  return (<><h3>Entreprises et établissements</h3><Msg ok={a.ok} err={a.err} />
    <div className="filters"><select value={kind} onChange={(e) => setKind(e.target.value)}><option value="">Tous types</option><option value="company">Entreprises</option><option value="institution">Établissements</option></select>
      <select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Tous statuts</option>{["pending", "validated", "rejected", "suspended"].map((s) => <option key={s} value={s}>{lab(s)}</option>)}</select></div>
    <Loading err={err} data={data} />
    {data && (data.length === 0 ? <div className="empty">Aucune organisation.</div> : data.map((o) => (
      <div className="card" key={o.id}><b>{o.name}</b> <Tag s={o.status} /> <span>{lab(o.kind)} · {o.city || "—"} · {o.sector || "—"} · IFU/RCCM : {o.registration_no || "—"}{o.annual_quota !== null ? ` · quota ${o.annual_quota}` : ""}</span>
        <span>Contact : {o.owner.full_name} ({o.owner.email}) · inscrit le {dt(o.created_at)}</span>{o.description && <p>{o.description}</p>}{o.status_reason && <small>Motif : {o.status_reason}</small>}
        {o.status !== "validated" && <button className="link" onClick={() => act(o, "validated")}>Valider</button>}{o.status === "pending" && <button className="link" onClick={() => act(o, "rejected")}>Rejeter</button>}
        {o.status === "validated" && <button className="link" onClick={() => act(o, "suspended")}>Suspendre</button>}{o.status === "validated" && o.kind === "institution" && <button className="link" onClick={() => act(o, "validated")}>Modifier le quota</button>}</div>)))}</>);
}

function Lists() {
  const [status, setStatus] = useState(""); const { data, err } = useLoad<any[]>(`/admin/lists?status=${status}`);
  return (<><h3>Listes transmises par les établissements</h3>
    <div className="filters"><select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Tous statuts</option>{["received", "in_review", "validated", "partially_validated", "rejected"].map((s) => <option key={s} value={s}>{lab(s)}</option>)}</select></div>
    <Loading err={err} data={data} />
    {data && <Table head={["Établissement", "Liste", "Reçue le", "Lignes", "En attente", "À corriger", "Validées", "Comptes", "Statut", ""]} empty="Aucune liste."
      rows={data.map((l) => [l.institution.name, l.title, dt(l.created_at), l.counts.total, l.counts.pending, l.counts.invalid, l.counts.validated, l.counts.account_created, <Tag s={l.status} />, <Link className="link" to={`/tableau-de-bord/listes/${l.id}`}>Examiner</Link>])} />}</>);
}

function csvCell(v: any) { return `"${String(v ?? "").replace(/"/g, '""')}"`; }

function ListReview() {
  const { id } = useParams(); const { data, err, reload } = useLoad<any>(`/admin/lists/${id}`); const a = useAct(); const [inv, setInv] = useState<any>(null);
  if (!data) return <Loading err={err} data={data} />;
  const run = (fn: () => Promise<any>, ok: string) => a.run(async () => { const r = await fn(); reload(); return r; }, ok);
  const create = (force = false) => a.run(async () => { const r = await api(`/admin/lists/${id}/create-accounts${force ? "?force=true" : ""}`, "POST"); setInv(r); reload(); return r; }, "Comptes créés. Copiez ou exportez les liens d'invitation maintenant.");
  const exportCsv = () => saveText(`invitations_liste_${id}.csv`, "nom;email;lien_activation;courriel_envoye\n" + inv.invitations.map((i: any) => [i.full_name, i.email, i.link ?? "", i.mail_sent ? "oui" : "non"].map(csvCell).join(";")).join("\n"));
  const c = data.counts;
  return (<><Link to="/tableau-de-bord/listes">← Listes</Link><h3>{data.title} <Tag s={data.status} /></h3>
    <p>Établissement : <b>{data.institution.name}</b> <Tag s={data.institution.status} /> · quota annuel : {data.institution.annual_quota ?? "non défini"} · {c.total} ligne(s) : {c.pending} en attente, {c.invalid} à corriger, {c.validated} validée(s), {c.rejected} rejetée(s), {c.account_created} compte(s) créé(s)</p>
    <Msg ok={a.ok} err={a.err} />
    {a.err.includes("Quota") && <button className="link" onClick={() => create(true)}>Créer quand même (dépassement de quota assumé)</button>}
    <div className="filters"><button className="btn ghost" onClick={() => run(() => api(`/admin/lists/${id}/validate-all`, "POST"), "Lignes sans erreur validées.")}>Valider toutes les lignes sans erreur</button>
      <button className="btn" disabled={c.validated === 0} onClick={() => create()}>Créer les comptes des lignes validées ({c.validated})</button>
      <button className="link" onClick={() => { const r = prompt("Motif du rejet des lignes restantes :"); if (r) run(() => api(`/admin/lists/${id}/reject`, "POST", { reason: r }), "Lignes restantes rejetées."); }}>Rejeter les lignes restantes</button></div>
    {inv && <div className="card unread"><b>{inv.created} compte(s) créé(s)</b> — {inv.warning} <small>Valables {inv.valid_days} jours. Courriel : {inv.smtp_enabled ? "envoi tenté" : "non configuré : transmettez les liens vous-même"}.</small>
      <div className="filters"><button className="btn ghost" onClick={exportCsv}>Exporter les invitations (CSV)</button></div>
      <Table head={["Nom", "Email", "Lien d'activation", "Courriel"]} rows={inv.invitations.map((i: any) => [i.full_name, i.email, i.link ? <><input readOnly value={localLink(i.link)} onFocus={(e) => e.target.select()} /><a className="link" href={localLink(i.link)} target="_blank" rel="noreferrer">Ouvrir</a></> : "—", i.mail_sent ? "envoyé" : i.mail_info])} /></div>}
    <Table head={["#", "Nom", "Email", "Diplôme exact", "Niveau", "Spécialité", "Année", "Statut", "Message", ""]} empty="Aucune ligne."
      rows={data.rows.map((r: any) => [r.line_no, r.full_name, r.email, r.degree_title, r.level_code, r.specialty, r.year ?? "", <Tag s={r.status} />, r.message,
        r.status === "account_created" ? (r.activated ? "Compte activé" : "Activation en attente") : <>
          {r.status !== "validated" && <button className="link" onClick={() => run(() => api(`/admin/lists/${id}/rows/${r.id}/validate`, "POST"), "Ligne validée.")}>Valider</button>}
          <button className="link" onClick={() => { const m = prompt("Motif du rejet :"); if (m) run(() => api(`/admin/lists/${id}/rows/${r.id}/reject`, "POST", { reason: m }), "Ligne rejetée."); }}>Rejeter</button></>])} /></>);
}

function Users() {
  const [role, setRole] = useState(""); const [status, setStatus] = useState(""); const [q, setQ] = useState(""); const { data, err, reload } = useLoad<any>(`/admin/users?role=${role}&status=${status}&q=${encodeURIComponent(q)}`);
  const a = useAct(); const [link, setLink] = useState<any>(null); const [f, setF] = useState({ full_name: "", email: "", degree_title: "", level_id: "", specialty_text: "", year: "" }); const { data: levels } = useLoad<any[]>("/admin/levels");
  const { data: insts } = useLoad<any[]>("/admin/orgs?kind=institution&status=validated"); const [inst, setInst] = useState("");
  const create = (e: React.FormEvent) => { e.preventDefault(); a.run(async () => { const r = await api("/admin/graduates", "POST", { ...f, level_id: Number(f.level_id), year: f.year ? Number(f.year) : null, institution_id: inst ? Number(inst) : null }); setLink(r); reload(); }, "Compte créé (hors liste, tracé dans le journal)."); };
  return (<><h3>Utilisateurs</h3><Msg ok={a.ok} err={a.err} />
    <div className="filters"><input placeholder="Nom ou email" value={q} onChange={(e) => setQ(e.target.value)} />
      <select value={role} onChange={(e) => setRole(e.target.value)}><option value="">Tous rôles</option>{["graduate", "company", "institution", "admin"].map((s) => <option key={s} value={s}>{lab(s)}</option>)}</select>
      <select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Tous statuts</option>{["active", "pending_activation", "suspended"].map((s) => <option key={s} value={s}>{lab(s)}</option>)}</select></div>
    {link && <div className="card unread"><b>Invitation pour {link.user?.email ?? link.email}</b><input readOnly value={localLink(link.link)} onFocus={(e) => e.target.select()} /><a className="link" href={localLink(link.link)} target="_blank" rel="noreferrer">Ouvrir le lien d’activation</a><small>Copiez ce lien ou ouvrez-le immédiatement. Courriel : {link.mail_sent ? "envoyé" : link.mail_info}</small></div>}
    <Loading err={err} data={data} />
    {data && <Table head={["Nom", "Email", "Rôle", "Statut", "Créé le", "Dernière connexion", ""]} empty="Aucun utilisateur."
      rows={data.items.map((u: any) => [u.full_name, u.email, lab(u.role), <Tag s={u.status} />, dt(u.created_at), dtt(u.last_login), u.role === "admin" ? "" : <>
        {u.status === "suspended" ? <button className="link" onClick={() => a.run(async () => { await api(`/admin/users/${u.id}/status`, "POST", { status: "active" }); reload(); }, "Compte réactivé.")}>Réactiver</button>
          : <Confirm text="Suspendre ce compte ?" onYes={() => a.run(async () => { await api(`/admin/users/${u.id}/status`, "POST", { status: "suspended" }); reload(); }, "Compte suspendu.")}>Suspendre</Confirm>}
        {u.status === "pending_activation" && <button className="link" onClick={() => a.run(async () => { setLink(await api(`/admin/users/${u.id}/invitation`, "POST")); }, "Nouvelle invitation générée.")}>Réémettre l'invitation</button>}</>])} />}
    <details><summary>Créer manuellement un compte candidat (cas exceptionnel, hors liste)</summary><form className="card form wide" onSubmit={create}>
      <label>Nom complet<input required value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></label><label>Email<input type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
      <label>Intitulé exact du diplôme<input required value={f.degree_title} onChange={(e) => setF({ ...f, degree_title: e.target.value })} /></label>
      <label>Niveau<select required value={f.level_id} onChange={(e) => setF({ ...f, level_id: e.target.value })}><option value="">—</option>{levels?.filter((l) => l.active).map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}</select></label>
      <label>Spécialité<input value={f.specialty_text} onChange={(e) => setF({ ...f, specialty_text: e.target.value })} /></label><label>Année<input type="number" value={f.year} onChange={(e) => setF({ ...f, year: e.target.value })} /></label>
      <label>Établissement d'origine<select value={inst} onChange={(e) => setInst(e.target.value)}><option value="">— Aucun —</option>{insts?.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
      <button className="btn">Créer le compte</button></form></details></>);
}

function Verifications() {
  const { data, err, reload } = useLoad<any>("/admin/verifications"); const { data: cols, reload: rc } = useLoad<any[]>("/admin/collaborations?status=pending"); const a = useAct();
  if (!data) return <Loading err={err} data={data} />;
  const v = (path: string, body: any, msg: string) => a.run(async () => { await api(path, "POST", body); reload(); rc(); }, msg);
  return (<><h3>Vérifications</h3><Msg ok={a.ok} err={a.err} /><p className="mut">Contrôlez les justificatifs avant de vérifier : le statut « vérifié » est affiché aux entreprises.</p>
    <h4>Diplômes à vérifier</h4><Table head={["Talent", "Intitulé exact", "Niveau", "Année", "Établissement", "Origine", "Statut", ""]} empty="Rien à vérifier." rows={data.degrees.map((d: any) => [d.graduate, d.title, d.level, d.year ?? "", d.institution_name, d.source === "institution" ? "établissement" : "talent", <Tag s={d.status} />,
      <><button className="link" onClick={() => v(`/admin/verify/degree/${d.id}`, { status: "verified" }, "Diplôme vérifié.")}>Vérifier</button><button className="link" onClick={() => v(`/admin/verify/degree/${d.id}`, { status: "to_complete" }, "Demande de complément envoyée.")}>À compléter</button><button className="link" onClick={() => v(`/admin/verify/degree/${d.id}`, { status: "rejected" }, "Diplôme rejeté.")}>Rejeter</button></>])} />
    <h4>Expériences déclarées</h4><Table head={["Talent", "Fonction", "Organisation", "Nature", "Période", ""]} empty="Rien à vérifier." rows={data.experiences.map((e: any) => [e.graduate, e.role, e.organization, lab(e.kind), `${dt(e.start_date)} → ${e.end_date ? dt(e.end_date) : "en cours"}`,
      <><button className="link" onClick={() => v(`/admin/verify/experience/${e.id}`, { status: "verified" }, "Expérience vérifiée.")}>Vérifier</button><button className="link" onClick={() => v(`/admin/verify/experience/${e.id}`, { status: "rejected" }, "Expérience rejetée.")}>Rejeter</button></>])} />
    <h4>Compétences déclarées</h4><Table head={["Talent", "Compétence", ""]} empty="Rien à vérifier." rows={data.skills.map((s: any) => [s.graduate, s.name, <button className="link" onClick={() => v(`/admin/verify/skill/${s.id}`, {}, "Compétence vérifiée.")}>Marquer vérifiée</button>])} />
    <h4>Collaborations à vérifier (condition préalable à toute évaluation)</h4><Table head={["Entreprise", "Talent", "Intitulé", "Période", ""]} empty="Aucune collaboration en attente."
      rows={(cols ?? []).map((c) => [c.company, c.graduate, c.title, `${dt(c.start_date)} → ${c.end_date ? dt(c.end_date) : "en cours"}`, <><button className="link" onClick={() => v(`/admin/collaborations/${c.id}/verify`, { approve: true }, "Collaboration vérifiée.")}>Confirmer</button><button className="link" onClick={() => v(`/admin/collaborations/${c.id}/verify`, { approve: false }, "Collaboration refusée.")}>Refuser</button></>])} /></>);
}

function Taxonomy() {
  const { data: lv, reload: rl } = useLoad<any[]>("/admin/levels"); const { data: sp, reload: rs } = useLoad<any[]>("/admin/specialties"); const a = useAct();
  const [l, setL] = useState({ code: "", label: "", family: "", rank: 1 }); const [s, setS] = useState({ name: "", domain: "" });
  if (!lv || !sp) return <Loading data={null} />;
  return (<><h3>Niveaux de diplôme et spécialités</h3><Msg ok={a.ok} err={a.err} />
    <p className="mut">Le « rang » ordonne les cycles pour les comparaisons de niveau (ex. Licence = 3, Master et ingénieur = 4). Aucune équivalence académique officielle n'est présumée : les équivalences se déclarent offre par offre.</p>
    <Table head={["Code", "Libellé", "Famille", "Rang", "Actif", ""]} rows={lv.map((x) => [x.code, x.label, x.family, x.rank, x.active ? "oui" : "non",
      <><button className="link" onClick={() => { const label = prompt("Libellé :", x.label); if (label) a.run(async () => { await api(`/admin/levels/${x.id}`, "PUT", { ...x, label }); rl(); }, "Modifié."); }}>Renommer</button>
        <button className="link" onClick={() => a.run(async () => { await api(`/admin/levels/${x.id}`, "PUT", { ...x, active: !x.active }); rl(); }, "Modifié.")}>{x.active ? "Désactiver" : "Activer"}</button></>])} />
    <form className="filters" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/admin/levels", "POST", { ...l, rank: Number(l.rank) }); setL({ code: "", label: "", family: "", rank: 1 }); rl(); }, "Niveau ajouté."); }}>
      <input required placeholder="CODE" pattern="[A-Z0-9_]+" value={l.code} onChange={(e) => setL({ ...l, code: e.target.value.toUpperCase() })} /><input required placeholder="Libellé" value={l.label} onChange={(e) => setL({ ...l, label: e.target.value })} />
      <input placeholder="Famille" value={l.family} onChange={(e) => setL({ ...l, family: e.target.value })} /><input type="number" min={1} max={20} value={l.rank} onChange={(e) => setL({ ...l, rank: Number(e.target.value) })} /><button className="btn">Ajouter un niveau</button></form>
    <Table head={["Spécialité", "Domaine", "Actif", ""]} rows={sp.map((x) => [x.name, x.domain, x.active ? "oui" : "non", <button className="link" onClick={() => a.run(async () => { await api(`/admin/specialties/${x.id}`, "PUT", { ...x, active: !x.active }); rs(); }, "Modifié.")}>{x.active ? "Désactiver" : "Activer"}</button>])} />
    <form className="filters" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/admin/specialties", "POST", s); setS({ name: "", domain: "" }); rs(); }, "Spécialité ajoutée."); }}>
      <input required placeholder="Nom de la spécialité" value={s.name} onChange={(e) => setS({ ...s, name: e.target.value })} /><input placeholder="Domaine" value={s.domain} onChange={(e) => setS({ ...s, domain: e.target.value })} /><button className="btn">Ajouter une spécialité</button></form></>);
}

function Moderation() {
  const { data: offers, reload: ro } = useLoad<any[]>("/admin/offers"); const { data: reps, reload: rr } = useLoad<any[]>("/admin/reports"); const a = useAct();
  return (<><h3>Offres et signalements</h3><Msg ok={a.ok} err={a.err} />
    <h4>Signalements et contestations</h4><Loading data={reps} />
    {reps && (reps.length === 0 ? <div className="empty">Aucun signalement.</div> : reps.map((r) => (
      <div className="card" key={r.id}><b>{lab(r.kind)}</b> <Tag s={r.status} /> <span>{r.target}</span><p>Motif ({r.reporter.full_name}, {lab(r.reporter.role)}) : {r.reason}</p>{r.resolution && <small>Décision : {r.resolution}</small>}
        {r.status === "open" && <><button className="link" onClick={() => a.run(async () => { await api(`/admin/reports/${r.id}/resolve`, "POST", { action: "hide" }); rr(); ro(); }, "Contenu retiré.")}>Retirer le contenu</button>
          <button className="link" onClick={() => a.run(async () => { await api(`/admin/reports/${r.id}/resolve`, "POST", { action: "keep" }); rr(); }, "Contenu maintenu.")}>Maintenir</button></>}</div>)))}
    <h4>File de validation des offres</h4><Loading data={offers} />
    {offers && <>
      <div className="kpis"><div><small>À examiner</small><b>{offers.filter((o) => o.status === "pending_review").length}</b></div><div><small>Publiées</small><b>{offers.filter((o) => o.status === "published").length}</b></div><div><small>Corrections demandées</small><b>{offers.filter((o) => o.status === "changes_requested").length}</b></div></div>
      {offers.filter((o) => o.status === "pending_review").map((o) => <article className="card review-card" key={o.id}><div className="row-h"><b>{o.title}</b><Tag s={o.status} /></div><p>{o.org.name} · {o.location || "Lieu non précisé"} · {lab(o.type)}</p><p><b>Rémunération :</b> {o.salary?.type === "fixed" ? `${o.salary.min?.toLocaleString("fr-FR")} FCFA` : o.salary?.type === "range" ? `${o.salary.min?.toLocaleString("fr-FR")} – ${o.salary.max?.toLocaleString("fr-FR")} FCFA` : o.salary?.type === "unpaid" ? "Non rémunéré" : "À négocier"}</p><p><b>Diplôme requis :</b> {o.degree.level.label} {o.degree.mandatory ? "(obligatoire)" : "(souhaité)"}</p><p>{o.description}</p><p><b>Atouts et avantages :</b> {o.benefits || "Non précisés"}</p><p><b>Compétences obligatoires :</b> {o.required_skills.join(", ") || "Non précisées"}</p>
        <div className="filters"><button className="btn" onClick={() => a.run(async () => { await api(`/admin/offers/${o.id}/review`, "POST", { action: "approve" }); ro(); }, "Offre approuvée et publiée ; matching déclenché.")}>Approuver et publier</button><button className="btn ghost" onClick={() => { const reason = prompt("Corrections à apporter (motif obligatoire) :"); if (reason) a.run(async () => { await api(`/admin/offers/${o.id}/review`, "POST", { action: "request_changes", reason }); ro(); }, "Demande de correction envoyée."); }}>Demander des corrections</button><button className="link" onClick={() => { const reason = prompt("Motif du rejet :"); if (reason) a.run(async () => { await api(`/admin/offers/${o.id}/review`, "POST", { action: "reject", reason }); ro(); }, "Offre rejetée."); }}>Rejeter</button></div></article>)}
      <h4>Toutes les offres</h4><Table head={["Offre", "Entreprise", "Diplôme requis", "Statut", "Modération", "Action"]} empty="Aucune offre." rows={offers.map((o) => [o.title, o.org.name, o.degree.level.label + (o.degree.mandatory ? " (oblig.)" : " (souhaité)"), <Tag s={o.status} />, <Tag s={o.moderation === "ok" ? "ok" : "suspended"} label={o.moderation === "ok" ? "Conforme" : "Suspendue"} />,
      <button className="link" onClick={() => { const reason = o.moderation === "ok" ? prompt("Motif de suspension :") : ""; if (reason === null) return; a.run(async () => { await api(`/admin/offers/${o.id}/moderation`, "POST", { moderation: o.moderation === "ok" ? "suspended" : "ok", reason }); ro(); }, "Modération enregistrée."); }}>{o.moderation === "ok" ? "Suspendre" : "Rétablir"}</button>])} />
    </>}</>);
}

function PlanForm({ p, onDone }: { p?: any; onDone: () => void }) {
  const a = useAct(); const [f, setF] = useState<any>(p ?? { code: "", name: "", description: "", price_xof: 0, duration_days: 30, max_active_offers: 5, profile_views_per_month: 20, can_search: true, can_advanced_filters: false, can_see_matching: false, can_see_contacts: false, active: true, sort: 9 });
  const n = (v: string) => (v === "" ? null : Number(v)); const set = (k: string, v: any) => setF({ ...f, [k]: v });
  return (<form className="card form wide" onSubmit={(e) => { e.preventDefault(); a.run(async () => { const body = { ...f, price_xof: Number(f.price_xof), duration_days: Number(f.duration_days), sort: Number(f.sort) }; if (p) await api(`/admin/plans/${p.id}`, "PUT", body); else await api("/admin/plans", "POST", body); onDone(); }, "Formule enregistrée : les droits s'appliquent immédiatement."); }}>
    <Msg ok={a.ok} err={a.err} /><label>Code<input required pattern="[a-z0-9_-]+" value={f.code} onChange={(e) => set("code", e.target.value)} /></label><label>Nom<input required value={f.name} onChange={(e) => set("name", e.target.value)} /></label>
    <label>Description<input value={f.description} onChange={(e) => set("description", e.target.value)} /></label>
    <label>Durée (jours)<input type="number" min={1} value={f.duration_days} onChange={(e) => set("duration_days", e.target.value)} /></label>
    <label>Offres publiées simultanées (vide = illimité)<input type="number" min={0} value={f.max_active_offers ?? ""} onChange={(e) => set("max_active_offers", n(e.target.value))} /></label>
    <label>Profils consultables / mois (vide = illimité)<input type="number" min={0} value={f.profile_views_per_month ?? ""} onChange={(e) => set("profile_views_per_month", n(e.target.value))} /></label>
    {([["can_search", "Recherche de talents"], ["can_advanced_filters", "Filtres avancés"], ["can_see_matching", "Correspondance et recommandations"], ["can_see_contacts", "Coordonnées et CV"], ["active", "Formule proposée"]] as [string, string][]).map(([k, l]) => <label className="check" key={k}><input type="checkbox" checked={f[k]} onChange={(e) => set(k, e.target.checked)} /> {l}</label>)}
    <label>Ordre d'affichage<input type="number" value={f.sort} onChange={(e) => set("sort", e.target.value)} /></label><button className="btn">Enregistrer</button></form>);
}

function Billing() {
  const { data: plans, reload: rp } = useLoad<any[]>("/admin/plans"); const { data: subs, reload: rs } = useLoad<any[]>("/admin/subscriptions"); const { data: pays, reload: ry } = useLoad<any[]>("/admin/payments");
  const { data: invs } = useLoad<any[]>("/admin/invoices"); const { data: cos } = useLoad<any[]>("/admin/orgs?kind=company&status=validated"); const a = useAct();
  const [edit, setEdit] = useState<any>(undefined); const [g, setG] = useState({ org_id: "", plan_code: "", months: 1, reason: "" });
  return (<><h3>Abonnements et paiements</h3><Msg ok={a.ok} err={a.err} />
    <h4>Formules (configurables)</h4><Loading data={plans} />
    {plans && <Table head={["Formule", "Durée", "Offres", "Profils/mois", "Recherche", "Filtres", "Correspondance", "Coordonnées", "Active", ""]} rows={plans.map((p) => [p.name, p.duration_days + " j", p.max_active_offers ?? "∞", p.profile_views_per_month ?? "∞", p.can_search ? "✔" : "—", p.can_advanced_filters ? "✔" : "—", p.can_see_matching ? "✔" : "—", p.can_see_contacts ? "✔" : "—", p.active ? "oui" : "non", <button className="link" onClick={() => setEdit(p)}>Modifier</button>])} />}
    <button className="btn ghost" onClick={() => setEdit(edit === null ? undefined : null)}>{edit === null ? "Fermer" : "Nouvelle formule"}</button>
    {edit !== undefined && <PlanForm key={edit?.id ?? "new"} p={edit ?? undefined} onDone={() => { setEdit(undefined); rp(); }} />}
    <h4>Octroyer un abonnement manuellement</h4><form className="filters" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/admin/subscriptions/grant", "POST", { ...g, org_id: Number(g.org_id), months: Number(g.months) }); rs(); ry(); }, "Abonnement octroyé (facture à 0 FCFA, tracé dans le journal)."); }}>
      <select required value={g.org_id} onChange={(e) => setG({ ...g, org_id: e.target.value })}><option value="">Entreprise…</option>{cos?.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select>
      <select required value={g.plan_code} onChange={(e) => setG({ ...g, plan_code: e.target.value })}><option value="">Formule…</option>{plans?.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}</select>
      <input type="number" min={1} max={12} value={g.months} onChange={(e) => setG({ ...g, months: Number(e.target.value) })} /><input required placeholder="Motif" value={g.reason} onChange={(e) => setG({ ...g, reason: e.target.value })} /><button className="btn">Octroyer</button></form>
    <h4>Abonnements</h4>{subs && <Table head={["Entreprise", "Formule", "Période", "Statut", ""]} empty="Aucun abonnement." rows={subs.map((s) => [s.org.name, s.plan, `${dt(s.start_date)} → ${dt(s.end_date)}`, <Tag s={s.status} />, s.status === "active" ? <Confirm text="Annuler cet abonnement ?" onYes={() => a.run(async () => { await api(`/admin/subscriptions/${s.id}/cancel`, "POST"); rs(); }, "Abonnement annulé.")}>Annuler</Confirm> : ""])} />}
    <h4>Paiements et transactions</h4>{pays && <Table head={["Référence", "Entreprise", "Facture", "Traitement", "Montant", "Statut", "Date", ""]} empty="Aucun paiement." rows={pays.map((p) => [p.reference, p.org.name, p.invoice_number, p.mode === "demo" ? "Interne" : p.provider, xof(p.amount_xof), <Tag s={p.status} />, dt(p.paid_at || p.created_at),
      p.status === "pending" ? <Confirm text="Confirmez-vous avoir reçu ce règlement hors plateforme ? (non vérifié automatiquement)" onYes={() => a.run(async () => { await api(`/admin/payments/${p.reference}/mark-paid`, "POST"); ry(); rs(); }, "Paiement rapproché manuellement.")}>Marquer reçu</Confirm> : ""])} />}
    <h4>Factures</h4>{invs && <Table head={["N°", "Description", "Montant", "Statut", "Émise le"]} empty="Aucune facture." rows={invs.map((i) => [i.number, i.description, xof(i.amount_xof), <Tag s={i.status} />, dt(i.issued_at)])} />}</>);
}

function Settings() {
  const { data, err, reload } = useLoad<any>("/admin/settings"); const a = useAct(); const [w, setW] = useState<any>(null); const [s, setS] = useState<any>(null);
  if (data && !w) { setW(data.matching_weights); setS({ contact_email: data.contact_email, support_phone: data.support_phone, terms_version: data.terms_version }); }
  if (!w || !s) return <Loading err={err} data={data} />;
  const LAB: Record<string, string> = { degree: "Niveau de diplôme", specialty: "Spécialité", skills: "Compétences", experience: "Expérience", location: "Localisation", availability: "Disponibilité" };
  return (<><h3>Paramètres</h3><Msg ok={a.ok} err={a.err} />
    <h4>Règles du score de correspondance</h4><p className="mut">Pondérations relatives (les critères non exigés par une offre sont ignorés puis le score est normalisé). Chaque changement est tracé dans le journal. Le score de réputation reste distinct et n'en dépend pas.</p>
    <form className="card form wide" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/admin/settings/matching-weights", "PUT", Object.fromEntries(Object.keys(LAB).map((k) => [k, Number(w[k])]))); reload(); }, "Pondérations enregistrées."); }}>
      {Object.entries(LAB).map(([k, l]) => <label key={k}>{l} (défaut {data.default_weights[k]})<input type="number" min={0} max={100} value={w[k]} onChange={(e) => setW({ ...w, [k]: e.target.value })} /></label>)}<button className="btn">Enregistrer les pondérations</button></form>
    <h4>Plateforme</h4><form className="card form wide" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/admin/settings", "PUT", s); reload(); }, "Paramètres enregistrés."); }}>
      <label>Email de contact<input value={s.contact_email} onChange={(e) => setS({ ...s, contact_email: e.target.value })} /></label><label>Téléphone du support<input value={s.support_phone} onChange={(e) => setS({ ...s, support_phone: e.target.value })} /></label>
      <label>Version des conditions d'utilisation<input value={s.terms_version} onChange={(e) => setS({ ...s, terms_version: e.target.value })} /></label><button className="btn">Enregistrer</button></form>
    <div className="card"><b>Configuration serveur (lecture seule, fichier .env)</b><p>Paiements : <b>{data.payment_mode}</b> / fournisseur <b>{data.payment_provider}</b> · Courriel : <b>{data.smtp_enabled ? "SMTP configuré" : "non configuré"}</b></p></div></>);
}

function Journal() {
  const { data: log } = useLoad<any[]>("/admin/audit"); const { data: msgs } = useLoad<any[]>("/admin/contacts");
  return (<><h3>Messages de contact</h3>{msgs && (msgs.length === 0 ? <div className="empty">Aucun message.</div> : msgs.map((m) => <div className="card" key={m.id}><b>{m.name}</b> ({m.email}) <small>{dtt(m.created_at)}</small><p>{m.message}</p></div>))}
    <h3>Journal d'activité</h3>{log && <Table head={["Date", "Acteur", "Action", "Détail"]} empty="Journal vide." rows={log.map((l) => [dtt(l.created_at), l.actor_id ?? "—", l.action, l.detail])} />}</>);
}

export default function Admin() {
  return (<Shell title="Administration" items={NAV}><Routes>
    <Route index element={<Overview />} /><Route path="organisations" element={<Orgs />} /><Route path="listes" element={<Lists />} /><Route path="listes/:id" element={<ListReview />} />
    <Route path="utilisateurs" element={<Users />} /><Route path="verifications" element={<Verifications />} /><Route path="referentiels" element={<Taxonomy />} /><Route path="moderation" element={<Moderation />} />
    <Route path="abonnements" element={<Billing />} /><Route path="parametres" element={<Settings />} /><Route path="journal" element={<Journal />} /><Route path="notifications" element={<Notifications />} />
    <Route path="compte" element={<Account />} /><Route path="*" element={<p>Page introuvable.</p>} /></Routes></Shell>);
}
