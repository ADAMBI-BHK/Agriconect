import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../App";

export function Login({ adminMode = false }: { adminMode?: boolean }) {
  const { setUser } = useAuth(); const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "" }); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { const account = await api("/auth/login", "POST", f); if (adminMode && account.role !== "admin") { await api("/auth/logout", "POST"); throw new Error("Ce compte n'a pas les droits administrateur. Utilisez un compte admin configuré par le responsable technique."); } setUser(account); nav("/tableau-de-bord"); } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <form className="card form" onSubmit={submit}>
      <h2>{adminMode ? "Accès administration" : "Connexion"}</h2>{adminMode && <p className="mut">Espace réservé aux administrateurs AgriConnect. Connectez-vous avec les identifiants ADMIN_EMAIL et ADMIN_PASSWORD configurés sur le serveur.</p>}{err && <p className="err" role="alert">{err}</p>}
      <label>Email<input type="email" required autoComplete="username" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
      <label>Mot de passe<input type="password" required autoComplete="current-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></label>
      <button className="btn" disabled={busy}>{busy ? "…" : "Se connecter"}</button>
      {!adminMode && <Link className="form-link" to="/mot-de-passe-oublie">Mot de passe oublié ?</Link>}
      {!adminMode && <p className="mut">Diplômé ? Votre compte est créé par AgriConnect après transmission de la liste de votre établissement : utilisez le lien d'invitation reçu. Entreprise ou établissement : <Link to="/inscription">créez votre espace</Link>.</p>}
    </form>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState(""); const [err, setErr] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try { const r = await api("/auth/request-password-reset", "POST", { email }); setMessage(r.message); }
    catch (x: any) { setErr(x.message); }
    finally { setBusy(false); }
  };
  if (message) return <div className="card form auth-result"><h2>Vérifiez votre boîte mail</h2><p className="ok" role="status">{message}</p><p className="mut">Pour protéger les comptes, nous affichons ce même message même si l’adresse n’est pas associée à un compte.</p><Link className="btn" to="/connexion">Retour à la connexion</Link></div>;
  return <form className="card form" onSubmit={submit}>
    <h2>Mot de passe oublié ?</h2><p className="mut">Saisissez l’adresse utilisée pour votre compte. Si un compte actif correspond, vous recevrez un lien temporaire.</p>
    {err && <p className="err" role="alert">{err}</p>}
    <label>Adresse email<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
    <button className="btn" disabled={busy}>{busy ? "Envoi…" : "Recevoir le lien"}</button><Link className="form-link" to="/connexion">Retour à la connexion</Link>
  </form>;
}

export function ResetPassword() {
  const [sp] = useSearchParams(); const token = sp.get("token") || ""; const [f, setF] = useState({ new_password: "", confirm: "" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false); const [done, setDone] = useState("");
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr("");
    if (f.new_password !== f.confirm) { setErr("Les mots de passe ne correspondent pas"); return; }
    setBusy(true);
    try { const r = await api("/auth/reset-password", "POST", { token, new_password: f.new_password }); setDone(r.message); }
    catch (x: any) { setErr(x.message); }
    finally { setBusy(false); }
  };
  if (!token) return <div className="card form auth-result"><h2>Lien incomplet</h2><p className="err" role="alert">Le lien de récupération est incomplet. Demandez un nouveau lien.</p><Link className="btn" to="/mot-de-passe-oublie">Demander un lien</Link></div>;
  if (done) return <div className="card form auth-result"><h2>Mot de passe réinitialisé</h2><p className="ok" role="status">{done}</p><Link className="btn" to="/connexion">Se connecter</Link></div>;
  return <form className="card form" onSubmit={submit}>
    <h2>Choisir un nouveau mot de passe</h2><p className="mut">Le lien est à usage unique et valable pendant une durée limitée.</p>
    {err && <p className="err" role="alert">{err}</p>}
    <label>Nouveau mot de passe (8 caractères min., lettres et chiffres)<input type="password" minLength={8} required autoComplete="new-password" value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} /></label>
    <label>Confirmation<input type="password" minLength={8} required autoComplete="new-password" value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} /></label>
    <button className="btn" disabled={busy}>{busy ? "Réinitialisation…" : "Définir le nouveau mot de passe"}</button>
  </form>;
}

/** Inscription publique : entreprises et établissements uniquement. */
export function Register() {
  const { setUser } = useAuth(); const nav = useNavigate();
  const [f, setF] = useState({ full_name: "", email: "", password: "", confirm: "", role: "company", org_name: "", accept_terms: false });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr("");
    if (f.password !== f.confirm) return setErr("Les mots de passe ne correspondent pas");
    setBusy(true);
    try { const { confirm, ...body } = f; setUser(await api("/auth/register-organization", "POST", body)); nav("/tableau-de-bord"); } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <form className="card form" onSubmit={submit}>
      <h2>Créer l'espace de mon organisation</h2>
      <p className="mut">Les entreprises et établissements partenaires sont examinés par l'administration AgriConnect avant d'accéder à toutes les fonctions.
        Les diplômés utilisent le lien d'activation généré après validation de leur dossier.</p>
      {err && <p className="err" role="alert">{err}</p>}
      <label>Je représente
        <select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
          <option value="company">Une entreprise agricole ou agroalimentaire</option><option value="institution">Un établissement de formation</option>
        </select></label>
      <label>Nom de l'organisation<input required minLength={2} value={f.org_name} onChange={(e) => setF({ ...f, org_name: e.target.value })} /></label>
      <label>Votre nom complet<input required minLength={2} value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></label>
      <label>Email professionnel<input type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
      <label>Mot de passe (8 caractères min., lettres et chiffres)<input type="password" minLength={8} required autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></label>
      <label>Confirmation<input type="password" required autoComplete="new-password" value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} /></label>
      <label className="check"><input type="checkbox" checked={f.accept_terms} onChange={(e) => setF({ ...f, accept_terms: e.target.checked })} /> J'accepte les <Link to="/legal/conditions">conditions d'utilisation</Link></label>
      <button className="btn" disabled={busy || !f.accept_terms}>{busy ? "…" : "Créer mon espace"}</button>
    </form>
  );
}

/** Activation d'un compte candidat à partir du lien d'invitation. */
export function Activation() {
  const { setUser } = useAuth(); const nav = useNavigate();
  const [sp] = useSearchParams(); const token = sp.get("token") || "";
  const [info, setInfo] = useState<any>(null); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ password: "", confirm: "", accept_terms: false });
  useEffect(() => { api(`/auth/activation-info?token=${encodeURIComponent(token)}`).then(setInfo).catch((e) => setErr(e.message)); }, [token]);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr("");
    if (f.password !== f.confirm) return setErr("Les mots de passe ne correspondent pas");
    setBusy(true);
    try { setUser(await api("/auth/activate", "POST", { token, password: f.password, accept_terms: f.accept_terms })); nav("/tableau-de-bord"); } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  if (!info) return <div className="card form"><h2>Activation du compte</h2>{err ? <p className="err">{err}</p> : <p>Vérification du lien…</p>}</div>;
  return (
    <form className="card form" onSubmit={submit}>
      <h2>Activer mon compte</h2>
      <p>Bonjour <b>{info.full_name}</b> ({info.email}). Votre établissement a transmis vos informations et AgriConnect les a vérifiées. Choisissez votre mot de passe pour accéder à votre espace.</p>
      {err && <p className="err" role="alert">{err}</p>}
      <label>Mot de passe (8 caractères min., lettres et chiffres)<input type="password" minLength={8} required autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></label>
      <label>Confirmation<input type="password" required autoComplete="new-password" value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} /></label>
      <label className="check"><input type="checkbox" checked={f.accept_terms} onChange={(e) => setF({ ...f, accept_terms: e.target.checked })} />
        <span>J'accepte les <Link to="/legal/conditions">conditions d'utilisation</Link> et le <Link to="/legal/confidentialite">traitement de mes données</Link>, et l'activation de mon profil auprès des entreprises abonnées (je pourrai modifier sa visibilité à tout moment).</span></label>
      <button className="btn" disabled={busy || !f.accept_terms}>{busy ? "…" : "Activer mon compte"}</button>
    </form>
  );
}
