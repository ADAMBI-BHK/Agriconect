import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Photo, FieldScene, GraduateScene, CompanyScene, SchoolScene, VisionScene } from "../components/Art";
import { Icon, CountUp, RotatingWord } from "../components/Motion";

const TYPES: Record<string, string> = { job: "Emploi", internship: "Stage", apprenticeship: "Alternance", mission: "Mission", training: "Formation" };
const FAQ = [
  ["AgriConnect est-il gratuit ?", "Oui pour les diplômés et les établissements partenaires. Les entreprises disposent d’un accès adapté à leurs besoins de recrutement ; contactez-nous pour connaître les modalités."],
  ["Qui peut s'inscrire ?", "Les entreprises agricoles et agroalimentaires et les établissements de formation créent leur espace, examiné par AgriConnect. Les diplômés reçoivent une invitation après validation de la liste de leur établissement."],
  ["Mes informations sont-elles visibles par tous ?", "Non. Votre profil est privé par défaut : vous choisissez de le rendre public ou non."],
  ["Comment suivre ma candidature ?", "Depuis votre espace, chaque candidature affiche son statut, et vous êtes notifié à chaque changement."],
  ["AgriConnect est-il réservé au Bénin ?", "La plateforme est conçue d'abord pour le Bénin, avec l'ambition de s'étendre à d'autres pays africains."],
];
const PROBLEMS: [string, string][] = [
  ["Premier emploi difficile", "Les jeunes diplômés agricoles peinent à trouver un premier emploi ou un stage."],
  ["Compétences invisibles", "Les compétences réelles des diplômés sont peu visibles pour les recruteurs."],
  ["Offres dispersées", "Les offres d'emploi et de stage sont éparpillées et difficiles à repérer."],
  ["Liens écoles-entreprises faibles", "Les relations entre établissements de formation et entreprises restent peu structurées."],
  ["Insertion peu suivie", "Le devenir professionnel des anciens étudiants est rarement suivi."],
  ["Recommandations peu fiables", "Il manque des mécanismes de recommandation professionnelle traçables."],
];
const GOALS: [string, string, string][] = [
  ["target", "Faciliter l'insertion", "Rapprocher les diplômés des opportunités qui correspondent à leur formation."],
  ["bulb", "Valoriser les compétences", "Donner à chacun un profil professionnel clair et partageable."],
  ["link", "Créer des collaborations", "Structurer les liens entre entreprises, établissements et diplômés."],
  ["globe", "Grandir avec l'Afrique", "Partir du Bénin pour bâtir un écosystème agricole numérique africain."],
];

const VALUES: [string, string, string][] = [
  ["lock", "Confiance", "Profils privés par défaut, recommandations traçables et organisations vérifiées."],
  ["search", "Transparence", "Aucune décision automatique opaque : les rapprochements restent explicables."],
  ["sprout", "Utilité concrète", "Chaque fonction répond à un besoin réel du secteur, pas à un effet de mode."],
  ["link", "Collaboration", "Diplômés, entreprises et établissements avancent ensemble."],
];
const AUDIENCE = ["Étudiants en fin de formation", "Jeunes diplômés", "Agronomes", "Ingénieurs agronomes", "Techniciens agricoles", "Spécialistes de l'agroalimentaire", "Environnement et ressources naturelles", "Entreprises agricoles", "Coopératives", "Industries agroalimentaires", "Cabinets de conseil", "ONG et projets de développement", "Universités et écoles"];
const ROAD: [string, string, string][] = [
  ["Socle opérationnel", "Comptes validés, espaces par rôle, profils, CV sécurisés, candidatures et suivi des étapes", "ok"],
  ["Recrutement encadré", "Offres structurées, revue administrative, gestion des abonnements et historique des décisions", "ok"],
  ["Matching transparent", "Consentement candidat, correspondance expliquée, classement individuel et notifications", "ok"],
];

const HERO_SLIDES = [
  { src: "/images/hero-accueil.jpg", alt: "Cultures agricoles baignées de lumière", credit: "AgriConnect · Agriculture au Bénin" },
  { src: "/images/companies.jpg", alt: "Entreprise agricole et production locale", credit: "AgriConnect · Entreprises et filières" },
  { src: "/images/schools.jpg", alt: "Établissement de formation agricole", credit: "AgriConnect · Formations et transmission" },
  { src: "/images/graduates.jpg", alt: "Jeunes talents agricoles en formation", credit: "AgriConnect · Talents agricoles" },
];

function Hero() {
  const [active, setActive] = useState(0); const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (paused) return;
    const id = window.setInterval(() => setActive((i) => (i + 1) % HERO_SLIDES.length), 6500);
    return () => window.clearInterval(id);
  }, [paused]);
  const move = (delta: number) => setActive((i) => (i + delta + HERO_SLIDES.length) % HERO_SLIDES.length);
  const slide = HERO_SLIDES[active];
  const goDown = () => document.getElementById("chiffres")?.scrollIntoView({ behavior: "smooth", block: "start" });
  return (
    <section className="hero-full" aria-labelledby="hero-title">
      <div className="hero-media" role="region" aria-roledescription="carrousel" aria-label="Photos AgriConnect">
        {HERO_SLIDES.map((item, i) => <img key={item.src} className={"hero-bg" + (i === active ? " active" : "")} src={item.src} alt="" aria-hidden={i !== active} fetchPriority={i === 0 ? "high" : "auto"} />)}
        <div className="hero-veil" aria-hidden="true" />
        <div className="hero-photo-caption" aria-live="polite"><span>{slide.alt}</span><small>{slide.credit}</small></div>
        <div className="hero-controls">
          <button type="button" onClick={() => move(-1)} aria-label="Photo précédente">←</button>
          <div className="hero-dots" aria-label="Choisir une photo">{HERO_SLIDES.map((item, i) => <button key={item.src} type="button" className={"dot" + (i === active ? " active" : "")} aria-label={`Afficher la photo ${i + 1}`} aria-current={i === active ? "true" : undefined} onClick={() => setActive(i)} />)}</div>
          <button type="button" onClick={() => move(1)} aria-label="Photo suivante">→</button>
          <button type="button" className="hero-pause" onClick={() => setPaused(!paused)} aria-pressed={paused} aria-label={paused ? "Relancer le carrousel" : "Mettre le carrousel en pause"}>{paused ? "▶" : "Ⅱ"}</button>
        </div>
      </div>
      <div className="hero-content">
        <span className="hero-pill"><i aria-hidden="true" />AgriTech · Bénin → Afrique</span>
        <h1 id="hero-title">Les talents agricoles de demain rencontrent <em>les opportunités d’aujourd’hui.</em></h1>
        <p className="hero-lead">AgriConnect rapproche les entreprises, les établissements de formation et les diplômés pour faire émerger des recrutements plus pertinents dans les secteurs agricole et agroalimentaire.</p>
        <div className="hero-cta">
          <Link className="btn big hero-primary" to="/inscription">Recruter des talents <span aria-hidden="true">→</span></Link>
          <Link className="btn big hero-ghost" to="/inscription">Créer un espace entreprise</Link>
        </div>
        <ul className="hero-trust">
          <li>Entreprises vérifiées</li><li>Offres contrôlées</li><li>Talents valorisés</li>
        </ul>
      </div>
      <button type="button" className="hero-scroll" onClick={goDown} aria-label="Découvrir la suite"><span /></button>
    </section>
  );
}

function Actor({ flip, title, text, link, to, photo, art }: any) {
  return (
    <article className={"actor" + (flip ? " flip" : "")}>
      <Photo name={photo} alt={`Photographie agricole — ${title}`} fallback={art} />
      <div><h3>{title}</h3><p>{text}</p><Link className="btn ghost" to={to}>{link}</Link></div>
    </article>
  );
}

export default function Home() {
  const [stats, setStats] = useState<any>(null);
  useEffect(() => { api("/stats").then(setStats).catch(() => {}); }, []);
  const S: [string, any][] = stats ? [["Diplômés inscrits", stats.graduates], ["Entreprises", stats.organizations], ["Offres publiées", stats.opportunities]] : [];
  return (
    <>
      <Hero />
      <section className="stats" id="chiffres">{stats ? S.map(([l, v]) => <div className="stat-card" key={l}><b><CountUp value={v} /></b><span>{l}</span></div>) : <p className="mut">Chargement des statistiques…</p>}</section>

      <section className="block mission" id="a-propos">
        <div><span className="pill dark">Notre mission</span><h2>Bien plus qu'un site d'annonces</h2>
          <p>AgriConnect construit un écosystème numérique autour de l'emploi, des compétences, de la formation et des collaborations dans le secteur agricole.</p>
          <p>Notre ambition : que chaque diplômé agricole puisse valoriser son parcours, que chaque entreprise trouve les bons profils, et que chaque établissement reste en lien avec ses anciens étudiants.</p></div>
        <Photo name="about.jpg" alt="Notre mission" fallback={<FieldScene />} />
      </section>

      <section className="block mission flip">
        <Photo name="vision.jpg" alt="Notre vision" fallback={<VisionScene />} />
        <div><span className="pill dark">Notre vision</span><h2>Un écosystème, pas une simple liste d'annonces</h2>
          <p>Nous imaginons un espace professionnel où les diplômés construisent leur identité et valorisent leurs compétences, où les entreprises identifient des talents, et où les établissements de formation suivent l'insertion de leurs diplômés.</p>
          <p>À terme, AgriConnect doit devenir la référence pour l'emploi, les compétences et les collaborations du secteur agricole en Afrique.</p></div>
      </section>

      <section className="block"><h2>Les défis que nous voulons relever</h2>
        <div className="trio">{PROBLEMS.map(([t, d]) => <article className="feat" key={t}><h3>{t}</h3><p>{d}</p></article>)}</div></section>

      <section className="block" id="services"><h2>Une plateforme pour chaque acteur</h2>
        <Actor photo="graduates.jpg" art={<GraduateScene />} title="Diplômés : faites reconnaître votre potentiel" text="AgriConnect vous aide à transformer votre formation en visibilité professionnelle. Après validation de votre établissement, vous activez votre compte, présentez vos diplômes, compétences, expériences et CV, puis choisissez vos paramètres de visibilité. Vous pouvez consulter les offres accessibles depuis votre espace, déposer vos candidatures et suivre leur évolution. Votre profil et vos coordonnées restent protégés selon vos choix de confidentialité." link="Comprendre le parcours diplômé" to="/connexion" />
        <Actor flip photo="companies.jpg" art={<CompanyScene />} title="Entreprises : recrutez avec plus de précision" text="AgriConnect est conçu pour les entreprises agricoles et agroalimentaires qui recherchent des profils qualifiés. Décrivez vos besoins, précisez le niveau de diplôme requis, les compétences, l’expérience et les conditions du poste. Après examen par notre équipe, votre offre est publiée. Vous pouvez ensuite rechercher des talents, examiner les candidatures, suivre les étapes de recrutement et retrouver un historique professionnel utile. Les entreprises sont les clientes abonnées de la plateforme." link="Créer un espace entreprise" to="/inscription" />
        <Actor photo="schools.jpg" art={<SchoolScene />} title="Établissements : accompagnez l’insertion de vos diplômés" text="Votre établissement est un partenaire essentiel. Vous créez un espace institutionnel, transmettez les listes de diplômés et suivez leur traitement. Après contrôle par AgriConnect, les comptes sont créés et les diplômés reçoivent une invitation personnelle pour activer leur espace. Vous contribuez ainsi à maintenir le lien avec vos anciens étudiants et à structurer les relations avec les entreprises, sans frais d’abonnement pour l’établissement partenaire." link="Créer un espace établissement" to="/inscription" />
      </section>

      <section className="block"><h2>Nos objectifs</h2>
        <div className="trio">{GOALS.map(([i, t, d]) => <article className="feat" key={t}><div className="ico"><Icon name={i} /></div><h3>{t}</h3><p>{d}</p></article>)}</div></section>

      <section className="block"><h2>Nos valeurs</h2>
        <div className="trio">{VALUES.map(([i, t, d]) => <article className="feat" key={t}><div className="ico"><Icon name={i} /></div><h3>{t}</h3><p>{d}</p></article>)}</div></section>

      <section className="block"><h2>À qui s'adresse AgriConnect</h2>
        <div className="chips">{AUDIENCE.map((c) => <span key={c} className="chip">{c}</span>)}</div></section>

      <section className="block"><h2>Où en est la plateforme</h2>
        <div className="road">{ROAD.map(([t, d, k]) => <article className={"step " + k} key={t}><b>{t}</b><p>{d}</p></article>)}</div></section>

      <section className="block"><h2>Comment ça marche</h2>
        <ol className="steps">
          <li><span>1</span><div><h3>Créez votre compte</h3><p>Entreprises et établissements créent leur espace ; les diplômés reçoivent une invitation sécurisée après validation de leur établissement.</p></div></li>
          <li><span>2</span><div><h3>Complétez votre espace</h3><p>Présentez vos compétences ou vos besoins de recrutement.</p></div></li>
          <li><span>3</span><div><h3>Des offres examinées avant publication</h3><p>Chaque offre déposée par une entreprise est contrôlée par l’équipe AgriConnect avant sa mise en ligne. Les diplômés peuvent ensuite candidater depuis leur espace.</p></div></li>
        </ol></section>



      <section className="block"><h2>Organisations et établissements partenaires</h2>
        <div className="empty">Les organisations et établissements vérifiés seront présentés ici dès les premières inscriptions.</div></section>

      <section className="block narrow faq-section"><div className="faq-heading"><div><span className="pill dark">En bref</span><h2>Questions fréquentes</h2></div><p>Les réponses essentielles avant de créer votre espace.</p></div><div className="faq-list">{FAQ.map(([q, a]) => <details key={q}><summary>{q}<span aria-hidden="true">+</span></summary><p>{a}</p></details>)}</div></section>

      <section className="cta-band"><span className="eyebrow-light">L’agriculture de demain se construit ensemble</span><h2>Prêt à faire avancer votre parcours ?</h2><p>Rejoignez AgriConnect, retrouvez votre espace ou écrivez-nous pour en savoir plus.</p>
        <div className="cta"><Link className="btn big light" to="/inscription">Créer l'espace de mon organisation</Link><Link className="btn big ghost-light" to="/connexion">Accéder à mon espace</Link><Link className="text-light" to="/contact">Nous contacter</Link></div></section>
    </>
  );
}
