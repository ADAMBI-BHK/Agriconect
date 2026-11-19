import { createContext, useContext, useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, Navigate, useNavigate, useLocation } from "react-router-dom";
import { api } from "./api";
import Home from "./pages/Home";
import { Login, Register, Activation, ForgotPassword, ResetPassword } from "./pages/Auth";
import Plans from "./pages/Plans";
import Dashboard from "./pages/Dashboard";
import Contact from "./pages/Contact";
import Legal from "./pages/Legal";
import { useScrollReveal } from "./components/Motion";

type User = { id: number; email: string; full_name: string; role: string; org?: { id: number; name: string; status: string; status_reason: string } | null } | null;
const Ctx = createContext<{ user: User; setUser: (u: User) => void; loading: boolean }>({ user: null, setUser: () => {}, loading: true });
export const useAuth = () => useContext(Ctx);

export function Logo() {
  return (
    <span className="logo">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
        <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#34d399" /><stop offset="1" stopColor="#16a34a" /></linearGradient></defs>
        <rect width="32" height="32" rx="9" fill="url(#lg)" />
        <path d="M9 22c0-7 4-11 14-12-1 9-5 13-12 13" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="9" cy="22" r="2.3" fill="#fff" />
        <circle cx="23" cy="10" r="2.3" fill="#d9f99d" />
      </svg>
      Agri<span>Connect</span>
    </span>
  );
}

function SpaceLink({ user }: { user: User }) {
  return user
    ? <Link className="space-link" to="/tableau-de-bord"><span className="space-dot" aria-hidden="true" />Mon espace</Link>
    : <Link className="space-link" to="/connexion"><span className="space-dot" aria-hidden="true" />Accéder à mon espace</Link>;
}

export default function App() {
  const [user, setUser] = useState<User>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const loc = useLocation();
  useScrollReveal(loc.pathname);
  useEffect(() => { api("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); }, []);
  useEffect(() => {
    setOpen(false);
    if (loc.hash) { const t = window.setTimeout(() => document.getElementById(loc.hash.slice(1))?.scrollIntoView({ behavior: "smooth", block: "start" }), 60); return () => window.clearTimeout(t); }
    window.scrollTo(0, 0);
  }, [loc.pathname, loc.hash]);
  const logout = async () => { await api("/auth/logout", "POST"); setUser(null); nav("/"); };
  return (
    <Ctx.Provider value={{ user, setUser, loading }}>
      <header className="nav">
        <div className="nav-in">
          <Link to="/" aria-label="Accueil AgriConnect"><Logo /></Link>
          <button className="burger" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}><span /><span /><span /></button>
          <nav className={open ? "open" : ""} aria-label="Navigation principale">
            <div className="nav-center">
              <Link className={loc.pathname === "/" && !loc.hash ? "active" : ""} to="/">Maison</Link>
              <Link className={loc.pathname === "/" && loc.hash === "#services" ? "active" : ""} to="/#services">Nos services</Link>
              <Link className={loc.pathname === "/" && loc.hash === "#a-propos" ? "active" : ""} to="/#a-propos">À propos de nous</Link>
              <Link className={loc.pathname === "/contact" ? "active" : ""} to="/contact">Contact</Link>
            </div>
            <div className="nav-right">
              <SpaceLink user={user} />
              {user ? <button className="link" onClick={logout}>Déconnexion</button> : <Link className="btn nav-cta" to="/inscription">Créer un espace</Link>}
            </div>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/connexion" element={<Login />} />
          <Route path="/mot-de-passe-oublie" element={<ForgotPassword />} />
          <Route path="/reinitialiser-mot-de-passe" element={<ResetPassword />} />
          <Route path="/inscription" element={<Register />} />
          <Route path="/opportunites" element={<Navigate to="/" replace />} />
          <Route path="/administration" element={<Login adminMode />} />
          <Route path="/activation" element={<Activation />} />
          <Route path="/tarifs" element={<Plans />} />
          <Route path="/tableau-de-bord/*" element={loading ? <p>Chargement…</p> : user ? <Dashboard /> : <Navigate to="/connexion" />} />
          <Route path="/a-propos" element={<Navigate to="/#a-propos" replace />} />
          <Route path="/services" element={<Navigate to="/#services" replace />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/legal/:page" element={<Legal />} />
          <Route path="*" element={<p>Page introuvable.</p>} />
        </Routes>
      </main>
      <footer className="foot">
        <div className="foot-in">
          <div><Logo /><p>La plateforme AgriTech qui relie diplômés, entreprises et établissements de formation. Conçue pour le Bénin, pensée pour l'Afrique.</p></div>
          <div><b>Plateforme</b><Link to="/tarifs">Accès entreprise</Link><Link to="/inscription">Espace organisation</Link><Link to="/contact">Contact</Link><Link to="/administration">Administration</Link></div>
          <div><b>Contact & informations</b><a className="foot-contact contact-link" href="mailto:hamdaneadambi@gmail.com">E-mail : hamdaneadambi@gmail.com</a><a className="foot-contact contact-link" href="https://wa.me/2290166338310?text=Bonjour%20AgriConnect%2C%20je%20souhaite%20en%20savoir%20plus." target="_blank" rel="noreferrer">WhatsApp : +229 0166338310</a><Link to="/legal/confidentialite">Confidentialité</Link><Link to="/legal/conditions">Conditions d'utilisation</Link><Link to="/legal/mentions">Mentions légales</Link></div>
        </div>
        <div className="foot-end">© {new Date().getFullYear()} AgriConnect. Tous droits réservés.</div>
      </footer>
    </Ctx.Provider>
  );
}
