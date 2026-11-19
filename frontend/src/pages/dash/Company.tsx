import { useEffect, useState } from "react";
import { Routes, Route, Link, useParams } from "react-router-dom";
import { api, download } from "../../api";
import { useAuth } from "../../App";
import { Shell } from "../Dashboard";
import { LocationPicker, CommuneSelect } from "../../components/LocationPicker";
import { PlanCards } from "../Plans";
import { DegreeReq } from "../Opportunities";
import { useLoad, Loading, Msg, useAct, Tag, lab, dt, TYPES, LevelSelect, SpecialtySelect, MatchView, TalentCard, Confirm, Table, useRefs, L } from "../../ui";
import { Notifications, Account } from "./Common";

const NAV: [string, string, boolean?][] = [["", "Aperçu", true], ["/organisation", "Mon organisation"], ["/offres", "Mes offres"],
  ["/talents", "Rechercher des talents"], ["/collaborations", "Collaborations et évaluations"], ["/notifications", "Notifications"], ["/compte", "Mon compte"]];

function StatusBanner({ org }: { org: any }) {
  if (org.status === "validated") return null;
  const m: Record<string, string> = { pending: "Votre dossier est en cours d'examen par l'administration AgriConnect. Complétez « Mon organisation » pour accélérer la validation.",
    rejected: "Votre dossier a été rejeté : " + org.status_reason + ". Corrigez « Mon organisation » : il sera soumis à nouveau.", suspended: "Votre organisation est suspendue. " + org.status_reason };
  return <p className="warn banner"><b>{lab(org.status)} — </b>{m[org.status]}</p>;
}

function Usage({ e }: { e: any }) {
  const q = (u: any) => (u.limit === null ? `${u.used} / illimité` : `${u.used} / ${u.limit}`);
  return (<div className="cols">
    <div className="card stat"><b>{e.active ? e.plan.name : "Aucun"}</b><span>{e.active ? `Abonnement jusqu'au ${dt(e.end_date)}` : "Abonnement requis"}</span></div>
    <div className="card stat"><b>{q(e.offers)}</b><span>Offres publiées</span></div>
    <div className="card stat"><b>{e.active && e.can_search ? q(e.views) : "—"}</b><span>Profils consultés ce mois-ci</span></div></div>);
}

function Overview() {
  const { data: me, err } = useLoad<any>("/company/me");
  const { data: d } = useLoad<any>(me?.org.status === "validated" ? "/company/dashboard" : null);
  if (!me) return <Loading err={err} data={me} />;
  return (<><h3>{me.org.name}</h3><StatusBanner org={me.org} />
    {me.org.status === "validated" && d && <>
      <Usage e={d.entitlements} />
      <div className="cols"><div className="card stat"><b>{d.applications}</b><span>Candidatures reçues</span></div><div className="card stat"><b>{d.applications_new}</b><span>À traiter</span></div>
        <div className="card stat"><b>{d.offers_by_status.published || 0}</b><span>Offres publiées</span></div></div>
      {!d.entitlements.active && <div className="card"><b>Prochaine étape :</b> <Link to="/tableau-de-bord/abonnement">choisissez une formule</Link> pour publier vos offres et rechercher des talents.</div>}</>}</>);
}

function Org() {
  const { data, err, reload } = useLoad<any>("/company/me"); const [f, setF] = useState<any>(null); const a = useAct();
  useEffect(() => { if (data?.org) setF({ ...data.org }); }, [data]);
  if (!data || !f) return <Loading err={err} data={data} />;
  const set = (k: string, v: any) => setF({ ...f, [k]: v });
  return (<><h3>Mon organisation</h3><StatusBanner org={data.org} />
    <form className="card form wide" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/company/org", "PUT", { name: f.name, description: f.description, sector: f.sector, city: f.city, country: "Bénin", website: f.website, phone: f.phone, registration_no: f.registration_no }); reload(); }, "Informations enregistrées."); }}>
      <Msg ok={a.ok} err={a.err} />
      <label>Raison sociale<input required value={f.name} onChange={(e) => set("name", e.target.value)} /></label>
      <label>Secteur d'activité<input value={f.sector} onChange={(e) => set("sector", e.target.value)} /></label>
      <label>Description<textarea rows={4} value={f.description} onChange={(e) => set("description", e.target.value)} /></label>
      <LocationPicker value={f.city} onChange={(v) => set("city", v)} label="Commune du siège" />
      <label>IFU / RCCM<input value={f.registration_no} onChange={(e) => set("registration_no", e.target.value)} /></label>
      <label>Téléphone<input type="tel" value={f.phone ?? ""} onChange={(e) => set("phone", e.target.value)} /></label>
      <label>Site web<input type="url" placeholder="https://…" value={f.website ?? ""} onChange={(e) => set("website", e.target.value)} /></label>
      <button className="btn" disabled={a.busy}>{data.org.status === "rejected" ? "Corriger et soumettre à nouveau" : "Enregistrer"}</button></form></>);
}

function openInvoice(i: any) {
  const w = window.open("", "_blank"); if (!w) return;
  w.document.write(`<html><head><title>${i.number}</title><style>body{font-family:sans-serif;max-width:640px;margin:2rem auto}td,th{padding:.4rem;border-bottom:1px solid #ccc;text-align:left}</style></head><body>
    <h2>Facture ${i.number}</h2><p>Client : <b>${i.org.name}</b> ${i.org.registration_no ? "(IFU/RCCM " + i.org.registration_no + ")" : ""}<br/>Émise le ${dt(i.issued_at)} — statut : ${lab(i.status)}${i.paid_at ? " le " + dt(i.paid_at) : ""}</p>
    <table><tr><th>Désignation</th><th>État</th></tr><tr><td>${i.description}</td><td>${lab(i.status)}</td></tr></table>
    <p style="color:#666;font-size:.85rem">Mentions légales de l'émetteur (identité, IFU, TVA) à compléter avant toute exploitation commerciale.</p></body></html>`);
  w.document.close(); w.print();
}

function Billing() {
  const { data, err, reload } = useLoad<any>("/billing/overview"); const { data: pl } = useLoad<any>("/plans"); const a = useAct();
  const [months, setMonths] = useState(1); const [pending, setPending] = useState<any>(null);
  if (!data || !pl) return <Loading err={err} data={data} />;
  const e = data.entitlements;
  const buy = (p: any) => a.run(async () => { const r = await api("/billing/subscribe", "POST", { plan_code: p.code, months }); setPending(r); reload(); }, "Demande créée : réglez-la ci-dessous.");
  return (<><h3>Accès entreprise et facturation</h3><Msg ok={a.ok} err={a.err} />
    <Usage e={e} />
    {e.active && <p>Formule actuelle : <b>{e.plan.name}</b>, du {dt(e.start_date)} au {dt(e.end_date)}. Choisir la même formule la prolonge à la suite ; une autre formule démarre aujourd'hui (sans prorata).</p>}
    {pending && pending.payment.status === "pending" && <div className="card unread"><b>Règlement en attente</b> — facture {pending.invoice.number} (réf. {pending.payment.reference})<p className="mut">{pending.checkout.message}</p>
      {pending.checkout.mode === "demo" && <button className="btn" onClick={() => a.run(async () => { await api(`/billing/payments/${pending.payment.reference}/confirm-demo`, "POST"); setPending(null); reload(); }, "Règlement confirmé : accès activé.")}>Confirmer le règlement</button>}
      <button className="link" onClick={() => a.run(async () => { await api(`/billing/payments/${pending.payment.reference}/cancel`, "POST"); setPending(null); reload(); }, "Demande annulée.")}>Annuler</button></div>}
    <label className="inline">Durée <select value={months} onChange={(x) => setMonths(Number(x.target.value))}>{[1, 3, 6, 12].map((m) => <option key={m} value={m}>{m} mois</option>)}</select></label>
    <PlanCards plans={pl.plans} action={(p) => <button className="btn" disabled={a.busy} onClick={() => buy(p)}>{e.active && e.plan.code === p.code ? "Renouveler l’accès" : "Demander cet accès"}</button>} />
    {e.active && <label className="check"><input type="checkbox" checked={e.auto_renew} onChange={(x) => a.run(async () => { await api(`/billing/auto-renew/${x.target.checked}`, "POST"); reload(); }, "Préférence enregistrée.")} /> Me rappeler le renouvellement (indicateur : aucun prélèvement automatique n'est effectué)</label>}
    <h4>Factures</h4><Table head={["N°", "Description", "Statut", "Date", ""]} rows={data.invoices.map((i: any) => [i.number, i.description, <Tag s={i.status} />, dt(i.issued_at), <button className="link" onClick={() => openInvoice(i)}>Imprimer</button>])} empty="Aucune facture." />
    <h4>Paiements</h4><Table head={["Référence", "Traitement", "Statut", "Date"]} rows={data.payments.map((p: any) => [p.reference, p.mode === "demo" ? "En cours de configuration" : p.provider, <Tag s={p.status} />, dt(p.paid_at || p.created_at)])} empty="Aucun paiement." />
    <h4>Historique des abonnements</h4><Table head={["Formule", "Durée", "Période", "Statut"]} rows={data.subscriptions.map((s: any) => [s.plan, s.months + " mois", `${dt(s.start_date)} → ${dt(s.end_date)}`, <Tag s={s.status} />])} empty="Aucun abonnement." /></>);
}

const OFFER0 = { title: "", description: "", sector: "", type: "job", contract_type: "", duration: "", salary_type: "negotiable", salary_min: "", salary_max: "", salary_period: "month", salary_currency: "XOF", benefits: "", location: "", degree_level_id: "" as any, degree_mandatory: true, accepted_level_codes: [] as string[],
  accepted_titles: "", allow_higher: true, allow_lower_alt: false, specialty_id: null as any, specialty_required: false, min_experience_years: 0, experience_mandatory: false,
  required_skills: "", desired_skills: "", requirements: "", deadline: "", status: "draft" };
const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

function OfferForm({ initial, id, onDone }: { initial?: any; id?: number; onDone: () => void }) {
  const refs = useRefs(); const a = useAct(); const [f, setF] = useState<any>(initial ?? OFFER0);
  const set = (k: string, v: any) => setF({ ...f, [k]: v });
  const submit = (e: React.FormEvent) => { e.preventDefault();
    if (!f.degree_level_id || Number(f.degree_level_id) <= 0) { a.run(async () => { throw new Error("Choisissez le niveau de diplôme minimum requis."); }); return; }
    if (!refs?.levels?.length) { a.run(async () => { throw new Error("Les niveaux de diplôme ne sont pas encore chargés. Actualisez la page puis réessayez."); }); return; }
    const body = { ...f, degree_level_id: Number(f.degree_level_id), accepted_titles: csv(f.accepted_titles), required_skills: csv(f.required_skills), desired_skills: csv(f.desired_skills),
      min_experience_years: Number(f.min_experience_years) || 0, salary_min: f.salary_min === "" ? null : Number(f.salary_min), salary_max: f.salary_max === "" ? null : Number(f.salary_max), deadline: f.deadline || null, status: id ? "pending_review" : "draft" };
    a.run(async () => { if (id) await api(`/company/offers/${id}`, "PATCH", body); else await api("/company/offers", "POST", body); onDone(); }, id ? "Offre modifiée." : "Offre enregistrée."); };
  return (<form className="card form wide" onSubmit={submit}><Msg ok={a.ok} err={a.err} />
    <label>Intitulé du poste<input required minLength={3} value={f.title} onChange={(e) => set("title", e.target.value)} /></label>
    <label>Description<textarea required minLength={10} rows={4} value={f.description} onChange={(e) => set("description", e.target.value)} /></label>
    <label>Secteur d'activité<input value={f.sector} onChange={(e) => set("sector", e.target.value)} /></label>
    <label>Type<select value={f.type} onChange={(e) => set("type", e.target.value)}>{Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
    <label>Contrat<select value={f.contract_type} onChange={(e) => set("contract_type", e.target.value)}><option value="">—</option>{["CDI", "CDD", "stage", "alternance", "mission", "freelance"].map((c) => <option key={c}>{c}</option>)}</select></label>
    <label>Durée (si nécessaire)<input value={f.duration} onChange={(e) => set("duration", e.target.value)} placeholder="Ex. : 6 mois" /></label>
    <fieldset><legend>Rémunération et avantages</legend>
      <label>Modalité de rémunération<select value={f.salary_type} onChange={(e) => set("salary_type", e.target.value)}><option value="fixed">Montant fixe</option><option value="range">Fourchette salariale</option><option value="negotiable">À négocier</option><option value="unpaid">Non rémunéré</option></select></label>
      {! ["negotiable", "unpaid"].includes(f.salary_type) && <div className="cols"><label>{f.salary_type === "range" ? "Rémunération minimale (FCFA)" : "Salaire (FCFA)"}<input type="number" min="0" required value={f.salary_min} onChange={(e) => set("salary_min", e.target.value)} /></label>{f.salary_type === "range" && <label>Rémunération maximale (FCFA)<input type="number" min="0" required value={f.salary_max} onChange={(e) => set("salary_max", e.target.value)} /></label>}</div>}
      <label>Périodicité<select value={f.salary_period} onChange={(e) => set("salary_period", e.target.value)}><option value="month">Par mois</option><option value="day">Par jour</option><option value="hour">Par heure</option><option value="project">Par mission / projet</option></select></label>
      <label>Atouts et avantages<textarea rows={3} value={f.benefits} onChange={(e) => set("benefits", e.target.value)} placeholder="Transport, logement, assurance, restauration, primes, formation… ou Aucun avantage spécifique" /></label>
    </fieldset>
    <LocationPicker value={f.location} onChange={(v) => set("location", v)} label="Commune du poste" />
    <label>Date limite de candidature<input type="date" value={f.deadline || ""} onChange={(e) => set("deadline", e.target.value)} /></label>
    <fieldset><legend>Diplôme requis — défini par vous, jamais déduit du titre</legend>
      <LevelSelect required value={f.degree_level_id} onChange={(v) => set("degree_level_id", v)} label="Niveau de diplôme minimum requis" />
      <label>Caractère du diplôme<select value={f.degree_mandatory ? "1" : "0"} onChange={(e) => set("degree_mandatory", e.target.value === "1")}><option value="1">Obligatoire</option><option value="0">Souhaité</option></select></label>
      <label className="check"><input type="checkbox" checked={f.allow_higher} onChange={(e) => set("allow_higher", e.target.checked)} /> Un diplôme supérieur au minimum est accepté</label>
      <label className="check"><input type="checkbox" checked={f.allow_lower_alt} onChange={(e) => set("allow_lower_alt", e.target.checked)} /> Signaler comme alternative un diplôme inférieur (je l'autorise explicitement)</label>
      <div><small>Niveaux également acceptés (équivalences que vous reconnaissez)</small><div className="chips">{refs?.levels.map((l) => <label className="check chip" key={l.id}><input type="checkbox" checked={f.accepted_level_codes.includes(l.code)}
        onChange={(e) => set("accepted_level_codes", e.target.checked ? [...f.accepted_level_codes, l.code] : f.accepted_level_codes.filter((c: string) => c !== l.code))} /> {l.label}</label>)}</div></div>
      <label>Intitulés de diplômes acceptés (séparés par des virgules)<input value={f.accepted_titles} onChange={(e) => set("accepted_titles", e.target.value)} /></label>
      <SpecialtySelect value={f.specialty_id} onChange={(v) => set("specialty_id", v)} label="Spécialité / domaine de formation" empty="— Non exigée —" />
      <label className="check"><input type="checkbox" checked={f.specialty_required} onChange={(e) => set("specialty_required", e.target.checked)} /> Spécialité exigée</label></fieldset>
    <fieldset><legend>Expérience et compétences (critères distincts du diplôme)</legend>
      <label>Expérience minimale (années)<input type="number" min={0} step={0.5} value={f.min_experience_years} onChange={(e) => set("min_experience_years", e.target.value)} /></label>
      <label className="check"><input type="checkbox" checked={f.experience_mandatory} onChange={(e) => set("experience_mandatory", e.target.checked)} /> Expérience obligatoire</label>
      <label>Compétences obligatoires (virgules)<input value={f.required_skills} onChange={(e) => set("required_skills", e.target.value)} /></label>
      <label>Compétences souhaitées (virgules)<input value={f.desired_skills} onChange={(e) => set("desired_skills", e.target.value)} /></label>
      <label>Autres critères objectivement pertinents<textarea rows={2} value={f.requirements} onChange={(e) => set("requirements", e.target.value)} /></label></fieldset>
    <div className="notice-soft"><b>Publication contrôlée :</b> votre offre sera vérifiée par l’administration avant d’être visible par les candidats.</div>
    <button className="btn" disabled={a.busy}>{id ? "Enregistrer et soumettre à validation" : "Enregistrer le brouillon"}</button></form>);
}

function toForm(o: any) {
  return { title: o.title, description: o.description, sector: o.sector, type: o.type, contract_type: o.contract_type, duration: o.duration, salary_type: o.salary?.type ?? "negotiable", salary_min: o.salary?.min ?? "", salary_max: o.salary?.max ?? "", salary_period: o.salary?.period ?? "month", salary_currency: o.salary?.currency ?? "XOF", benefits: o.benefits ?? "", location: o.location, degree_level_id: o.degree.level.id,
    degree_mandatory: o.degree.mandatory, accepted_level_codes: o.degree.accepted_level_codes, accepted_titles: o.degree.accepted_titles.join(", "), allow_higher: o.degree.allow_higher,
    allow_lower_alt: o.degree.allow_lower_alt, specialty_id: o.specialty?.id ?? null, specialty_required: o.specialty_required, min_experience_years: o.experience.min_years,
    experience_mandatory: o.experience.mandatory, required_skills: o.required_skills.join(", "), desired_skills: o.desired_skills.join(", "), requirements: o.requirements, deadline: o.deadline || "", status: o.status === "archived" ? "draft" : o.status };
}

function Offers() {
  const { data, err, reload } = useLoad<any[]>("/company/offers"); const a = useAct(); const [form, setForm] = useState<null | { id?: number; initial?: any }>(null);
  if (!data) return <Loading err={err} data={data} />;
  const patch = (id: number, status: string, msg: string) => a.run(async () => { await api(`/company/offers/${id}`, "PATCH", { status }); reload(); }, msg);
  return (<><div className="row-h"><h3>Mes offres</h3><button className="btn" onClick={() => setForm(form ? null : {})}>{form ? "Fermer le formulaire" : "Nouvelle offre"}</button></div><Msg ok={a.ok} err={a.err} />
    {form && <OfferForm key={form.id ?? "new"} id={form.id} initial={form.initial} onDone={() => { setForm(null); reload(); }} />}
    {data.length === 0 ? <div className="empty">Aucune offre. Créez votre première offre : le niveau de diplôme requis est obligatoire.</div> : data.map((o) => (
      <div className="card" key={o.id}><b>{o.title}</b> <Tag s={o.status} />{o.moderation === "suspended" && <Tag s="suspended" label="Suspendue par l'administration" />}
        <span>{TYPES[o.type]} · {o.location || "—"} · {o.applications} candidature(s){o.deadline ? " · avant le " + dt(o.deadline) : ""}</span>{o.salary && <p className="mut">Rémunération : {o.salary.type === "fixed" ? `${o.salary.min?.toLocaleString("fr-FR")} FCFA` : o.salary.type === "range" ? `${o.salary.min?.toLocaleString("fr-FR")} – ${o.salary.max?.toLocaleString("fr-FR")} FCFA` : o.salary.type === "unpaid" ? "Non rémunéré" : "À négocier"}{o.salary.type !== "unpaid" && o.salary.type !== "negotiable" ? ` / ${({month:"mois",day:"jour",hour:"heure",project:"mission"} as any)[o.salary.period]}` : ""}</p>}{o.review_reason && <p className="warn">Retour de l’administration : {o.review_reason}</p>}<DegreeReq o={o} />
        <Link className="link" to={`/tableau-de-bord/offres/${o.id}/candidatures`}>Candidatures</Link><Link className="link" to={`/tableau-de-bord/offres/${o.id}/recommandations`}>Talents recommandés</Link>
        {o.status !== "archived" && <button className="link" onClick={() => setForm({ id: o.id, initial: toForm(o) })}>Modifier</button>}
        {["draft", "changes_requested", "paused"].includes(o.status) && <button className="link" onClick={() => patch(o.id, "pending_review", "Offre soumise à validation.")}>Soumettre à validation</button>}
        {o.status === "published" && <button className="link" onClick={() => patch(o.id, "paused", "Offre mise en pause.")}>Mettre en pause</button>}
        {o.status !== "archived" && <button className="link" onClick={() => patch(o.id, "archived", "Offre archivée.")}>Archiver</button>}</div>))}</>);
}

const NEXT: Record<string, string[]> = { submitted: ["received", "under_review", "rejected"], received: ["under_review", "rejected"], under_review: ["shortlisted", "rejected"], shortlisted: ["interview", "rejected"], interview: ["accepted", "rejected"] };

function Applicants() {
  const { id } = useParams(); const { data, err, reload } = useLoad<any[]>(`/company/offers/${id}/applications`); const a = useAct();
  const [open, setOpen] = useState<number | null>(null);
  if (!data) return <Loading err={err} data={data} />;
  return (<><Link to="/tableau-de-bord/offres">← Mes offres</Link><h3>Candidatures reçues</h3><Msg ok={a.ok} err={a.err} />
    {data.length === 0 ? <div className="empty">Aucune candidature.</div> : data.map((x) => (
      <TalentCard key={x.id} t={{ ...x.profile, match: x.match }}>
        <p><b>{x.graduate.full_name}</b> ({x.graduate.email}) <Tag s={x.status} /> — déposée le {dt(x.created_at)}</p>
        <p><b>Diplômes (intitulé exact et statut) :</b> {x.degrees.map((d: any) => <span key={d.id}>{d.title} <Tag s={d.status} /> </span>)}</p>
        {x.cover_letter && <p>« {x.cover_letter} »</p>}
        {x.match_locked && <p className="mut">{x.match_locked}</p>}
        {x.match && <><button className="link" onClick={() => setOpen(open === x.id ? null : x.id)}>{open === x.id ? "Masquer" : "Voir"} l'explication de la correspondance</button>{open === x.id && <MatchView m={x.match} />}</>}
        {x.recommendations.length > 0 && <div className="card"><b>Recommandations d'anciens employeurs</b>{x.recommendations.map((r: any) => <p key={r.id}><i>{r.company} :</i> {r.text}</p>)}</div>}
        {x.graduate.has_cv && <button className="link" onClick={() => a.run(() => download(`/company/applications/${x.id}/cv`, "cv-" + x.graduate.full_name), "Téléchargé.")}>Télécharger le CV</button>}
        {(NEXT[x.status] || []).map((s) => <button className="link" key={s} onClick={() => a.run(async () => { await api(`/company/applications/${x.id}/status`, "PATCH", { status: s }); reload(); }, "Statut mis à jour : le candidat est notifié.")}>→ {lab(s)}</button>)}
      </TalentCard>))}</>);
}

function Recos() {
  const { id } = useParams(); const { data, err } = useLoad<any>(`/company/offers/${id}/recommendations`); const [open, setOpen] = useState<number | null>(null);
  if (!data) return <Loading err={err} data={data} />;
  return (<><Link to="/tableau-de-bord/offres">← Mes offres</Link><h3>Talents recommandés pour « {data.offer.title} »</h3><p className="mut">{data.note}</p>
    {data.items.map((t: any) => <TalentCard key={t.id} t={t}><button className="link" onClick={() => setOpen(open === t.id ? null : t.id)}>Pourquoi ce profil ?</button>{open === t.id && <MatchView m={t.match} />}
      <Link className="link" to={`/tableau-de-bord/talents/${t.id}?offer=${id}`}>Ouvrir le profil (compte dans le quota)</Link></TalentCard>)}</>);
}

function Talents() {
  const { data: me } = useLoad<any>("/company/me"); const refs = useRefs(); const [q, setQ] = useState<any>({ q: "", level_id: "", location: "", specialty_id: "", skills: "", min_years: "", max_years: "", availability: "", offer_id: "" });
  const { data: offers } = useLoad<any[]>("/company/offers"); const [res, setRes] = useState<any>(null); const [selected, setSelected] = useState<number[]>([]); const a = useAct();
  const e = me?.entitlements;
  const search = (ev?: React.FormEvent) => { ev?.preventDefault(); const p = new URLSearchParams(); Object.entries(q).forEach(([k, v]) => v !== "" && p.set(k, String(v)));
    setSelected([]); a.run(async () => setRes(await api("/company/talents?" + p.toString())), "Recherche effectuée."); };
  const set = (k: string, v: any) => setQ({ ...q, [k]: v });
  const toggle = (id: number) => setSelected((ids) => ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);
  const select = () => a.run(async () => { const result = await api("/company/selections", "POST", { offer_id: Number(q.offer_id), graduate_ids: selected }); setSelected([]); return result; }, `${selected.length} profil(s) sélectionné(s) et notifié(s).`);
  if (!me) return <Loading data={me} />;
  if (!e.active || !e.can_search) return (<><h3>Rechercher des talents</h3><div className="card"><b>Fonction non incluse.</b> {e.active ? `La recherche n'est pas incluse dans votre formule ${e.plan.name}.` : "Aucun abonnement actif."} <Link to="/tableau-de-bord/abonnement">Voir les formules</Link></div></>);
  return (<><h3>Rechercher des talents</h3><Usage e={e} />
    <form className="filters wide" onSubmit={search}>
      <input placeholder="Mot-clé (titre, compétence, diplôme)" value={q.q} onChange={(x) => set("q", x.target.value)} />
      <select value={q.level_id} onChange={(x) => set("level_id", x.target.value)}><option value="">Tout niveau de diplôme</option>{refs?.levels.map((l) => <option key={l.id} value={l.id}>Au moins : {l.label}</option>)}</select>
      <CommuneSelect value={q.location} onChange={(v) => set("location", v)} />
      {e.can_advanced_filters && <>
        <select value={q.specialty_id} onChange={(x) => set("specialty_id", x.target.value)}><option value="">Toute spécialité</option>{refs?.specialties.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
        <input placeholder="Compétences (virgules)" value={q.skills} onChange={(x) => set("skills", x.target.value)} />
        <input type="number" min={0} step={0.5} placeholder="Expérience min. (ans)" value={q.min_years} onChange={(x) => set("min_years", x.target.value)} />
        <input type="number" min={0} step={0.5} placeholder="Expérience max. (ans)" value={q.max_years} onChange={(x) => set("max_years", x.target.value)} />
        <select value={q.availability} onChange={(x) => set("availability", x.target.value)}><option value="">Toute disponibilité</option>{["available", "employed_open", "temporary_mission", "unavailable"].map((k) => <option key={k} value={k}>{L[k]}</option>)}</select></>}
      {e.can_see_matching && <select value={q.offer_id} onChange={(x) => set("offer_id", x.target.value)}><option value="">Classer par réputation</option>{offers?.map((o) => <option key={o.id} value={o.id}>Classer selon : {o.title}</option>)}</select>}
      <button className="btn">Rechercher</button></form>
    <Msg err={a.err} />
    {res && <><p className="mut">{res.total} profil(s). {res.note}</p>{q.offer_id && <div className="card selection-bar"><b>Sélectionner les profils retenus</b><span className="mut">{selected.length} choisi(s)</span><button className="btn" disabled={!selected.length || a.busy} onClick={select}>Notifier les profils choisis</button></div>}{res.items.map((t: any) => <TalentCard key={t.id} t={t}>{q.offer_id && <label className="check selection-check"><input type="checkbox" checked={selected.includes(t.id)} onChange={() => toggle(t.id)} /> Sélectionner ce profil</label>}<Link className="link" to={`/tableau-de-bord/talents/${t.id}${q.offer_id ? "?offer=" + q.offer_id : ""}`}>Ouvrir le profil</Link></TalentCard>)}</>}</>);
}

function TalentDetail() {
  const { id } = useParams(); const offer = new URLSearchParams(window.location.search).get("offer");
  const { data: t, err, reload } = useLoad<any>(`/company/talents/${id}${offer ? "?offer_id=" + offer : ""}`); const a = useAct();
  const [c, setC] = useState({ kind: "job", title: "", start_date: "", end_date: "" });
  if (!t) return <Loading err={err} data={t} />;
  return (<><Link to="/tableau-de-bord/talents">← Recherche</Link>
    <TalentCard t={t}><h3>{t.full_name}</h3><p>{t.bio}</p>
      <h4>Diplômes</h4>{t.degrees.map((d: any) => <p key={d.id}><b>{d.title}</b> <Tag s={d.status} /> — {d.level.label}{d.specialty ? " · " + d.specialty : ""}{d.year ? " · " + d.year : ""}</p>)}
      <h4>Expériences (nature, durée et niveau de responsabilité)</h4>{t.experiences.map((x: any) => <p key={x.id}>{x.role} — {x.organization} <Tag s={x.status} /> ({lab(x.kind)}, {dt(x.start_date)} → {x.end_date ? dt(x.end_date) : "en cours"})</p>)}
      <h4>Compétences</h4><div className="chips">{t.skills.map((s: any) => <span className="chip" key={s.name}>{s.name}{s.verified ? " ✓" : ""}</span>)}</div>
      {t.achievements.length > 0 && <><h4>Réalisations</h4>{t.achievements.map((x: any, i: number) => <p key={i}><b>{x.title}</b> {x.description}</p>)}</>}
      <h4>Réputation</h4><p>{t.reputation.score}/100 — {t.reputation.note}</p>
      <h4>Contact</h4>{t.contact ? <p>{t.contact.email} {t.contact.phone}</p> : <p className="mut">{t.contact_note}</p>}
      {t.can_download_cv && <button className="link" onClick={() => a.run(() => download(`/company/talents/${t.id}/cv`, "cv-" + t.full_name), "Téléchargé.")}>Télécharger le CV</button>}
      <p className="mut">Quota : {t.quota.used}/{t.quota.limit === null ? "illimité" : t.quota.limit} profils consultés ce mois-ci.</p></TalentCard>
    {t.match && <MatchView m={t.match} />}{t.match_note && <p className="mut">{t.match_note}</p>}
    <details><summary>Déclarer une collaboration passée avec ce talent (pour l'évaluer ou le recommander)</summary>
      <form className="card form" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/company/collaborations", "POST", { graduate_id: t.id, kind: c.kind, title: c.title, start_date: c.start_date, end_date: c.end_date || null }); reload(); }, "Déclarée : l'administration vérifie son existence avant de permettre l'évaluation."); }}>
        <Msg ok={a.ok} err={a.err} /><label>Nature<select value={c.kind} onChange={(e) => setC({ ...c, kind: e.target.value })}><option value="job">Emploi</option><option value="internship">Stage</option><option value="apprenticeship">Alternance</option><option value="mission">Mission</option></select></label>
        <label>Intitulé<input required minLength={3} value={c.title} onChange={(e) => setC({ ...c, title: e.target.value })} /></label>
        <label>Début<input type="date" required value={c.start_date} onChange={(e) => setC({ ...c, start_date: e.target.value })} /></label>
        <label>Fin<input type="date" value={c.end_date} onChange={(e) => setC({ ...c, end_date: e.target.value })} /></label><button className="btn">Déclarer</button></form></details>
    <button className="link" onClick={() => { const r = prompt("Motif du signalement de ce profil (10 caractères min.) :"); if (r) a.run(() => api("/reports", "POST", { kind: "profile", target_id: t.id, reason: r }), "Signalement transmis."); }}>Signaler ce profil</button></>);
}

const DIMS: [string, string][] = [["technical", "Compétences techniques et qualité du travail"], ["deadlines", "Respect des délais et ponctualité"], ["adaptability", "Adaptabilité"], ["professionalism", "Professionnalisme et communication"], ["teamwork", "Esprit d'équipe"], ["results", "Résultats et respect des engagements"]];

function Collabs() {
  const { data, err, reload } = useLoad<any[]>("/company/collaborations"); const a = useAct(); const [sel, setSel] = useState<any>(null);
  const [ev, setEv] = useState<any>({ technical: 3, deadlines: 3, adaptability: 3, professionalism: 3, teamwork: 3, results: 3, comment: "" }); const [reco, setReco] = useState("");
  if (!data) return <Loading err={err} data={data} />;
  return (<><h3>Collaborations, évaluations et recommandations</h3><Msg ok={a.ok} err={a.err} />
    <p className="mut">Une évaluation n'est possible que pour une collaboration vérifiée (embauche via AgriConnect, ou collaboration déclarée puis vérifiée par l'administration). Les commentaires ne doivent contenir ni coordonnées, ni liens, ni accusations personnelles. Le talent est informé et peut répondre ou contester.</p>
    {data.length === 0 ? <div className="empty">Aucune collaboration. Elles apparaissent à l'acceptation d'une candidature, ou si vous en déclarez une depuis le profil d'un talent.</div> : data.map((c) => (
      <div className="card" key={c.id}><b>{c.graduate.full_name}</b> — {c.title} <Tag s={c.status} /><span>{lab(c.kind)} · {dt(c.start_date)} → {c.end_date ? dt(c.end_date) : "en cours"} · {c.source === "platform" ? "via AgriConnect" : "déclarée"}</span>
        {c.evaluated && <span>Évaluation {lab(c.evaluation_status)}{c.evaluation_response ? " · le talent a répondu" : ""}</span>}{c.recommended && <span>Recommandation publiée</span>}
        {c.status === "verified" && (!c.evaluated || !c.recommended) && <button className="link" onClick={() => setSel(sel?.id === c.id ? null : c)}>{sel?.id === c.id ? "Fermer" : "Évaluer / recommander"}</button>}
        {sel?.id === c.id && <div className="card">
          {!c.evaluated && <form className="form wide" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/company/evaluations", "POST", { collaboration_id: c.id, ...ev }); setSel(null); reload(); }, "Évaluation publiée : le talent est informé."); }}>
            {DIMS.map(([k, l]) => <label key={k}>{l} : {ev[k]}/5<input type="range" min={1} max={5} value={ev[k]} onChange={(e) => setEv({ ...ev, [k]: Number(e.target.value) })} /></label>)}
            <label>Commentaire factuel (600 car. max.)<textarea maxLength={600} rows={3} value={ev.comment} onChange={(e) => setEv({ ...ev, comment: e.target.value })} /></label><button className="btn">Publier l'évaluation</button></form>}
          {!c.recommended && <form className="form wide" onSubmit={(e) => { e.preventDefault(); a.run(async () => { await api("/company/recommendations", "POST", { collaboration_id: c.id, text: reco }); setSel(null); setReco(""); reload(); }, "Recommandation publiée."); }}>
            <label>Recommandation (20 car. min.) — visible de l'entreprise auprès de laquelle le talent candidate<textarea minLength={20} maxLength={1000} rows={3} value={reco} onChange={(e) => setReco(e.target.value)} /></label><button className="btn ghost">Recommander ce talent</button></form>}</div>}</div>))}</>);
}

export default function Company() {
  const { user } = useAuth();
  return (<Shell title={user!.org?.name ?? "Espace entreprise"} items={NAV}><Routes>
    <Route index element={<Overview />} /><Route path="organisation" element={<Org />} /><Route path="abonnement" element={<Billing />} /><Route path="offres" element={<Offers />} />
    <Route path="offres/:id/candidatures" element={<Applicants />} /><Route path="offres/:id/recommandations" element={<Recos />} />
    <Route path="talents" element={<Talents />} /><Route path="talents/:id" element={<TalentDetail />} /><Route path="collaborations" element={<Collabs />} />
    <Route path="notifications" element={<Notifications />} /><Route path="compte" element={<Account />} /><Route path="*" element={<p>Page introuvable.</p>} /></Routes></Shell>);
}
