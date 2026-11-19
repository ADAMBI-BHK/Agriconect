import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export const L: Record<string, string> = {
  // candidatures
  submitted: "Soumise", received: "Reçue", under_review: "En examen", shortlisted: "Présélectionnée", interview: "Entretien", accepted: "Acceptée", rejected: "Refusée", withdrawn: "Retirée",
  // comptes, organisations, listes, lignes
  active: "Actif", pending_activation: "Activation en attente", suspended: "Suspendu", pending: "En attente", validated: "Validé", invalid: "À corriger",
  account_created: "Compte créé", in_review: "En cours d'examen", partially_validated: "Partiellement validée",
  // diplômes / expériences
  declared: "Déclaré", verified: "Vérifié", to_complete: "À compléter",
  // offres
  draft: "Brouillon", pending_review: "En attente de validation", changes_requested: "Corrections demandées", published: "Publiée", paused: "Suspendue", archived: "Archivée", ok: "Conforme",
  // abonnements, paiements
  pending_payment: "Paiement en attente", expired: "Expiré", cancelled: "Annulé", replaced: "Remplacé", unpaid: "Impayée", paid: "Payée", void: "Annulée",
  succeeded: "Réussi", failed: "Échoué", refunded: "Remboursé",
  // évaluations, signalements
  contested: "Contestée", hidden: "Retirée", open: "Ouvert", resolved: "Traité", dismissed: "Classé",
  // disponibilité
  available: "Disponible", employed_open: "En poste, ouvert aux propositions", temporary_mission: "En mission temporaire", unavailable: "Non disponible",
  // types
  job: "Emploi", internship: "Stage", apprenticeship: "Alternance", mission: "Mission", training: "Formation",
  institution: "Établissement", company: "Entreprise", graduate: "Diplômé", admin: "Administration",
};
export const lab = (k: string) => L[k] ?? k;
export const TYPES: Record<string, string> = { job: "Emploi", internship: "Stage", apprenticeship: "Alternance", mission: "Mission", training: "Formation" };
export const xof = (n: number | null | undefined) => (n ?? 0).toLocaleString("fr-FR") + " FCFA";
export const dt = (s?: string | null) => (s ? new Date(s).toLocaleDateString("fr-FR") : "—");
export const dtt = (s?: string | null) => (s ? new Date(s).toLocaleString("fr-FR") : "—");

export function Tag({ s, label }: { s: string; label?: string }) {
  const good = ["active", "validated", "verified", "published", "paid", "succeeded", "accepted", "resolved", "available", "ok", "account_created"];
  const bad = ["rejected", "suspended", "invalid", "failed", "hidden", "void", "cancelled", "expired", "unavailable", "contested"];
  const cls = good.includes(s) ? "good" : bad.includes(s) ? "bad" : "mid";
  return <span className={"tag " + cls}>{label ?? lab(s)}</span>;
}

export function useLoad<T = any>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState("");
  const reload = useCallback(() => {
    if (path === null) return Promise.resolve();
    return api(path).then((d) => { setData(d); setErr(""); }).catch((e) => setErr(e.message));
  }, [path]);
  useEffect(() => { setData(null); reload(); }, [reload]);
  return { data, err, reload, setData };
}

export function Loading({ err, data }: { err?: string; data: any }) {
  if (err) return <p className="err">{err}</p>;
  return data ? null : <p className="mut">Chargement…</p>;
}

export function Msg({ ok, err }: { ok?: string; err?: string }) {
  return <>{err && <p className="err" role="alert">{err}</p>}{ok && <p className="ok" role="status">{ok}</p>}</>;
}

/** Exécute une action, affiche succès/erreur. */
export function useAct() {
  const [ok, setOk] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<any>, success = "Enregistré.") => {
    setOk(""); setErr(""); setBusy(true);
    try { const r = await fn(); setOk(success); return r ?? true; } catch (e: any) { setErr(e.message); return false; } finally { setBusy(false); }
  };
  return { ok, err, busy, run, clear: () => { setOk(""); setErr(""); } };
}

let refCache: Promise<any> | null = null;
export function useRefs() {
  const [r, setR] = useState<any>(null);
  useEffect(() => { refCache = refCache ?? api("/referentials"); refCache.then(setR).catch(() => { refCache = null; }); }, []);
  return r as { levels: any[]; specialties: any[] } | null;
}

export function LevelSelect({ value, onChange, required, label = "Niveau de diplôme" }: { value: any; onChange: (v: number) => void; required?: boolean; label?: string }) {
  const r = useRefs();
  return (<label>{label}<select required={required} value={value ?? ""} onChange={(e) => onChange(Number(e.target.value))}>
    <option value="">— Choisir —</option>{r?.levels.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}</select></label>);
}

export function SpecialtySelect({ value, onChange, label = "Spécialité", empty = "— Aucune —" }: { value: any; onChange: (v: number | null) => void; label?: string; empty?: string }) {
  const r = useRefs();
  return (<label>{label}<select value={value ?? ""} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
    <option value="">{empty}</option>{r?.specialties.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>);
}

const ST: Record<string, string> = { met: "✔", partial: "◐", missing: "✘", to_verify: "⚠", na: "—" };
const STL: Record<string, string> = { met: "Satisfait", partial: "Partiel", missing: "Manquant", to_verify: "À vérifier", na: "Non exigé" };

/** Explication du score de correspondance, critère par critère. */
export function MatchView({ m }: { m: any }) {
  if (!m) return null;
  return (<div className="match">
    <div className="score"><b>{m.score}</b><span>/100 correspondance</span></div>
    {m.blocking_missing?.length > 0 && <p className="warn">Critère(s) obligatoire(s) non satisfait(s) : {m.blocking_missing.join(", ")}. Le profil n'est pas exclu : c'est à vous de décider.</p>}
    <ul>{m.criteria.map((c: any) => <li key={c.key} className={"c-" + c.status}><span className="ic" title={STL[c.status]}>{ST[c.status]}</span><b>{c.label}</b> <small>({c.weight} pts · {STL[c.status]})</small><br /><span className="mut">{c.detail}</span></li>)}</ul>
    <small className="mut">{m.note}</small>
  </div>);
}

/** Carte de talent : diplôme, expérience, réputation, correspondance et disponibilité restent des indicateurs SÉPARÉS. */
export function TalentCard({ t, children }: { t: any; children?: any }) {
  return (<div className="card talent">
    <div className="row-h"><div><h3 className="talent-name">{t.full_name || "Talent"}</h3><b>{t.headline || "Profil sans titre"}</b></div><span className="mut">{t.location || "—"}</span></div>
    <div className="kpis">
      <div><small>Diplôme</small><b>{t.degree ? t.degree.title : "—"}</b>{t.degree && <span><Tag s={t.degree.status} /> {t.degree.level.label}{t.degree.specialty ? " · " + t.degree.specialty : ""}</span>}</div>
      <div><small>Expérience</small><b>{t.experience.category}</b><span>{t.experience.years} an(s)</span></div>
      <div><small>Réputation</small><b>{t.reputation.score}/100</b><span>{t.reputation.provisional ? "provisoire (aucune évaluation)" : t.reputation.evaluations_count + " évaluation(s)"}</span></div>
      <div><small>Disponibilité</small><b>{t.availability.label}</b><span>mise à jour le {dt(t.availability.updated_at)}</span></div>
      {t.match && <div className="k-match"><small>Correspondance</small><b>{t.match.score}/100</b><span>{t.match.blocking_missing.length ? "critère obligatoire manquant" : "critères obligatoires OK"}</span></div>}
    </div>
    {t.skills?.length > 0 && <div className="chips">{t.skills.slice(0, 8).map((s: string) => <span className="chip" key={s}>{s}</span>)}</div>}
    {t.origin && <small className="mut">{t.origin === "institution" ? "Sélectionné par un établissement" + (t.institution ? " : " + t.institution : "") : "Recommandé par une entreprise"}</small>}
    {children}
  </div>);
}

export function Confirm({ text, onYes, children, cls = "link" }: { text: string; onYes: () => void; children: any; cls?: string }) {
  return <button className={cls} onClick={() => { if (window.confirm(text)) onYes(); }}>{children}</button>;
}

export function Table({ head, rows, empty = "Aucune donnée." }: { head: string[]; rows: any[][]; empty?: string }) {
  if (!rows.length) return <div className="empty">{empty}</div>;
  return (<div className="tablewrap"><table><thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody></table></div>);
}
