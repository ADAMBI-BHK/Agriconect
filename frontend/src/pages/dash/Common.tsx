import { useState } from "react";
import { api } from "../../api";
import { useLoad, Loading, Msg, useAct, dtt } from "../../ui";

export function Notifications() {
  const { data, err, reload } = useLoad<any[]>("/notifications");
  return (<><h3>Notifications</h3><Loading err={err} data={data} />
    {data && <>{data.some((n) => !n.read) && <button className="link" onClick={async () => { await api("/notifications/read-all", "POST"); reload(); }}>Tout marquer comme lu</button>}
      {data.length === 0 ? <div className="empty">Aucune notification.</div> : data.map((n) => (
        <div key={n.id} className={"card " + (n.read ? "" : "unread")}>{n.message} <small>{dtt(n.created_at)}</small>
          {!n.read && <button className="link" onClick={async () => { await api(`/notifications/${n.id}/read`, "POST"); reload(); }}>Marquer lu</button>}</div>))}</>}</>);
}

export function Account() {
  const [f, setF] = useState({ current_password: "", new_password: "", confirm: "" });
  const a = useAct();
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (f.new_password !== f.confirm) return a.run(async () => { throw new Error("Les mots de passe ne correspondent pas"); });
    if (await a.run(() => api("/auth/change-password", "POST", { current_password: f.current_password, new_password: f.new_password }), "Mot de passe modifié. Vos autres sessions ont été fermées.")) setF({ current_password: "", new_password: "", confirm: "" });
  };
  return (<><h3>Mon compte</h3><form className="card form" onSubmit={submit}><Msg ok={a.ok} err={a.err} />
    <label>Mot de passe actuel<input type="password" required autoComplete="current-password" value={f.current_password} onChange={(e) => setF({ ...f, current_password: e.target.value })} /></label>
    <label>Nouveau mot de passe (8 caractères min., lettres et chiffres)<input type="password" required minLength={8} autoComplete="new-password" value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} /></label>
    <label>Confirmation<input type="password" required autoComplete="new-password" value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} /></label>
    <button className="btn" disabled={a.busy}>Modifier le mot de passe</button></form></>);
}
