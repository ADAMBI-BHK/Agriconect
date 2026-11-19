# Architecture

## Backend (`backend/app`)
- `models.py` : utilisateurs, organisations (`kind` = company|institution, `status` = pending|validated|rejected|suspended), référentiels (`DegreeLevel` avec `rank`, `Specialty`), profils (diplômes, expériences, compétences, réalisations, consentement matching distinct), `SubmittedList`/`SubmittedRow`, offres (exigences de diplôme explicites, rémunération, avantages, état de revue), `OfferMatch` (snapshot de classement), candidatures, collaborations, évaluations, recommandations, signalements, `Plan`/`Subscription`/`Invoice`/`Payment`, `ProfileView` (quota de consultation), notifications, journal, réglages.
- `logic/` (pur, testé) : `matching.py` (score explicable ; critères non exigés ignorés puis normalisation ; critère obligatoire manquant = signalé, jamais exclu), `reputation.py` (évaluations lissées et pondérées par la récence ; niveau de diplôme absent du calcul), `entitlements.py` (quotas, validité, renouvellement), `importer.py` (CSV `;`/`,`, Excel, alias de colonnes).
- `deps.py` : authentification, rôles, organisation validée requise (`company_ok`, `institution_ok`).
- `services.py` : droits d'abonnement (`entitlements`, `require_subscription`), construction des données de matching, création des comptes candidats, activation d'abonnement.
- Routes : `routes_auth` (inscription organisation, connexion, activation par jeton, mot de passe), `routes_graduate`, `routes_company`, `routes_institution`, `routes_admin`, `routes_billing`, `routes_misc`.
- Règles transversales : une offre n'est visible des candidats que si elle est approuvée/publiée, non suspendue, non échue, l'entreprise validée **et** son abonnement actif ; seule la route administrative de revue peut la publier. Une modification d'offre publiée renvoie celle-ci en revue. Le matching n'inclut que les profils dont le consentement explicite est actif ; l'instantané est personnel et n'expose jamais les autres candidats.

## Choix techniques notables
- Jeton d'activation : `secrets.token_urlsafe(32)`, seule l'empreinte SHA-256 est stockée, validité 7 jours, usage unique.
- Session : cookie signé HMAC contenant `uid:expiration:version` ; la version change au changement de mot de passe, à l'activation et à la suspension.
- Pas de prorata ni de prélèvement automatique ; pas d'équivalence de diplômes présumée (les équivalences sont déclarées par l'entreprise, offre par offre).
- Une évaluation contestée est retirée du calcul de réputation jusqu'à la décision de l'administration.
- Migrations `0001` (schéma initial) et `0002` (revue des offres, rémunération/avantages, consentement matching et instantanés). `0002` gère les bases existantes et met les anciennes offres publiées en attente de contrôle humain.

## Frontend (`frontend/src`)
`ui.tsx` (composants partagés : statuts, explication du matching, carte de talent), `pages/dash/{Graduate,Company,Institution,Admin}.tsx` (un espace par rôle, routes imbriquées sous `/tableau-de-bord`), `pages/{Auth,Plans,Opportunities,Home,Contact,Legal}.tsx`. L'accueil utilise un carrousel Pexels avec pause/commandes et prise en compte de `prefers-reduced-motion`. Le build (`vite build`) ne vérifie pas les types ; `npm run typecheck` le fait séparément.
