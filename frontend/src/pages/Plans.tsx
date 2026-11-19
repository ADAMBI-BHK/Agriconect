import { Link } from "react-router-dom";
import { useLoad, Loading, xof } from "../ui";

export function PlanCards({ plans, action }: { plans: any[]; action?: (p: any) => any }) {
  return (<div className="trio">{plans.map((p) => (
    <div className="feat plan" key={p.code}>
      <h3>{p.name}</h3><p className="plan-price">{xof(p.price_xof)} <small>/ première année</small></p><p>{p.description}</p>
      <ul className="ticks">
        <li>{p.max_active_offers === null ? "Offres publiées illimitées" : `${p.max_active_offers} offre(s) publiée(s) à la fois`}</li>
        <li className={p.can_search ? "" : "off"}>Recherche de talents{p.can_search ? ` · ${p.profile_views_per_month === null ? "profils illimités" : p.profile_views_per_month + " profils / mois"}` : " — non incluse"}</li>
        <li className={p.can_advanced_filters ? "" : "off"}>Filtres avancés</li>
        <li className={p.can_see_matching ? "" : "off"}>Correspondance expliquée et recommandations</li>
        <li className={p.can_see_contacts ? "" : "off"}>Coordonnées des talents qui les autorisent</li>
      </ul>
      {action?.(p)}
    </div>))}</div>);
}

export default function Plans() {
  const { data, err } = useLoad<any>("/plans");
  return (<><h2>Accès entreprise</h2>
    <p className="lead">Chaque entreprise bénéficie d’un accès annuel complet à <b>15 000 FCFA pour la première année</b>. Les diplômés et les établissements partenaires ne paient rien, et aucun avantage d’accès ne peut améliorer le rang d’un talent.</p>
    <Loading err={err} data={data} />
    {data && <PlanCards plans={data.plans} action={() => <Link className="btn ghost" to="/inscription">Créer l'espace entreprise</Link>} />}</>);
}
