import { useState } from "react";
import { api } from "../api";

const TOPICS = ["Entreprise", "Établissement", "Diplômé", "Partenariat", "Autre"];
const MAIL = "hamdaneadambi@gmail.com";
const WA = "https://wa.me/2290166338310?text=Bonjour%20AgriConnect%2C%20je%20souhaite%20en%20savoir%20plus.";

const Ico = ({ d, d2 }: { d: string; d2?: string }) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} />{d2 && <path d={d2} />}</svg>
);

export default function Contact() {
  const [f, setF] = useState({ name: "", email: "", message: "" });
  const [topic, setTopic] = useState(TOPICS[0]);
  const [state, setState] = useState<"" | "sending" | "sent">("");
  const [err, setErr] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(""); setState("sending");
    try { await api("/contact", "POST", { ...f, message: `[${topic}] ${f.message}` }); setState("sent"); }
    catch (x: any) { setErr(x.message); setState(""); }
  };
  const again = () => { setF({ name: "", email: "", message: "" }); setState(""); };

  return (
    <div className="contact-page">
      <section className="page-hero">
        <img src="/images/vision.jpg" alt="" aria-hidden="true" />
        <div className="page-hero-veil" aria-hidden="true" />
        <div className="page-hero-in">
          <span className="hero-pill"><i aria-hidden="true" />Contact</span>
          <h1>Parlons de votre <em>projet agricole.</em></h1>
          <p>Entreprise, établissement de formation, diplômé ou partenaire : écrivez-nous, nous revenons vers vous dès que possible.</p>
        </div>
      </section>

      <section className="contact-grid">
        <aside className="contact-side">
          <a className="c-card" href={`mailto:${MAIL}`}>
            <span className="c-ico"><Ico d="M4 6h16v12H4z" d2="M4 7l8 6 8-6" /></span>
            <span><small>E-mail</small><b>{MAIL}</b></span>
            <span className="c-go" aria-hidden="true">→</span>
          </a>
          <a className="c-card" href={WA} target="_blank" rel="noreferrer">
            <span className="c-ico wa"><Ico d="M20 11.5A8 8 0 0 1 8.2 18.6L4 20l1.4-4A8 8 0 1 1 20 11.5z" d2="M9 9.5c.4 2 2.4 4 4.5 4.5" /></span>
            <span><small>WhatsApp</small><b>+229 0166338310</b></span>
            <span className="c-go" aria-hidden="true">→</span>
          </a>
          <div className="c-card static">
            <span className="c-ico"><Ico d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z" d2="M12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z" /></span>
            <span><small>Zone d'action</small><b>Bénin, puis toute l'Afrique</b></span>
          </div>
          <div className="c-note">
            <b>Vous êtes une entreprise ?</b>
            <p>Indiquez votre secteur et le type de profils recherchés : nous vous orienterons vers la formule adaptée.</p>
          </div>
        </aside>

        <div className="contact-form-wrap">
          {state === "sent" ? (
            <div className="c-sent" role="status">
              <svg viewBox="0 0 52 52" width="76" height="76" aria-hidden="true"><circle cx="26" cy="26" r="24" fill="none" stroke="#176b45" strokeWidth="3" className="c-circle" /><path d="M15 27l8 8 15-17" fill="none" stroke="#176b45" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" className="c-check" /></svg>
              <h2>Message envoyé</h2>
              <p>Merci, votre message a bien été enregistré. Nous vous répondrons par e-mail.</p>
              <button type="button" className="btn ghost" onClick={again}>Envoyer un autre message</button>
            </div>
          ) : (
            <form className="c-form" onSubmit={submit}>
              <h2>Envoyez-nous un message</h2>
              <p className="c-sub">Tous les champs sont obligatoires.</p>
              {err && <p className="err" role="alert">{err}</p>}
              <div className="c-topics" role="group" aria-label="Sujet du message">
                {TOPICS.map((t) => <button type="button" key={t} className={t === topic ? "on" : ""} aria-pressed={t === topic} onClick={() => setTopic(t)}>{t}</button>)}
              </div>
              <div className="c-row">
                <label className="c-field"><input required placeholder=" " value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /><span>Nom complet</span></label>
                <label className="c-field"><input type="email" required placeholder=" " value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /><span>Adresse e-mail</span></label>
              </div>
              <label className="c-field"><textarea required minLength={10} rows={6} placeholder=" " value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} /><span>Votre message</span></label>
              <button className="btn big c-send" disabled={state === "sending"}>{state === "sending" ? "Envoi en cours…" : <>Envoyer le message <span aria-hidden="true">→</span></>}</button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
