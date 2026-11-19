import { useParams } from "react-router-dom";
const T: Record<string, string> = { confidentialite: "Politique de confidentialité", conditions: "Conditions d'utilisation", mentions: "Mentions légales" };
export default function Legal() {
  const { page = "" } = useParams();
  return (<div className="card"><h2>{T[page] ?? "Page"}</h2>
    <p className="warn">PROJET DE DOCUMENT — à faire valider par un juriste avant toute exploitation publique.</p>
    <p>Le contenu définitif sera rédigé avec les informations de l'éditeur (identité, hébergeur, traitement des données personnelles conformément à la réglementation béninoise applicable).</p></div>);
}
