# AgriConnect 1.1

Plateforme B2B de confiance pour recruter des talents du secteur agricole et agroalimentaire au Bénin.
Conforme au cahier des charges v2.2 et au modèle économique : **les entreprises paient**, **les établissements transmettent des listes**,
**AgriConnect valide puis crée manuellement les comptes candidats**, **chaque entreprise définit le diplôme requis de chaque offre**.

> **État de la livraison 1.1.1.** Les parcours backend sont testés dans l'environnement de livraison : **69 tests d'intégration et de logique réussis** (`pytest -q`). Les migrations Alembic ont été exécutées sur une base SQLite neuve. Le contrôle TypeScript et le build Vite passent également. Les données fictives de test sont disponibles dans la prévisualisation via `scripts/dev.sh` et restent désactivées par défaut en production. Aucun test de paiement réel n'est revendiqué.

## 1. Fonctionnement

| Acteur | Rôle | Paie ? |
|---|---|---|
| **Entreprises** | Clients : publient des offres, cherchent des talents, évaluent après collaboration vérifiée | Oui (abonnement) |
| **Établissements** | Partenaires : transmettent des listes de diplômés (CSV/Excel), suivent leur traitement | Non |
| **Diplômés** | Comptes **créés par l'administration** après validation ; activation par lien personnel ; profil, candidatures | Non |
| **Administration** | Valide organisations et listes, crée les comptes, vérifie diplômes et collaborations, modère, gère formules et paiements | — |

Parcours : établissement transmet une liste → l'administration contrôle/valide les lignes → crée les comptes (liens d'invitation affichés et exportables ; courriel si SMTP configuré) →
le diplômé active son compte (mot de passe + acceptation des conditions) → complète son profil → les entreprises abonnées le trouvent et reçoivent ses candidatures.
Les diplômés ne créent pas leur compte depuis la page publique : l'administration crée leur compte à partir d'une liste validée ou manuellement, puis remet un lien d'activation personnel. Ce lien permet au diplômé de choisir son mot de passe et d'accéder à son espace.

Principes implémentés : diplôme et expérience séparés ; score de **correspondance** (par offre, expliqué critère par critère), score de **réputation** (évaluations de collaborations vérifiées,
lissé, récent), **disponibilité** : trois indicateurs distincts ; aucun profil exclu automatiquement ; droits d'abonnement contrôlés **côté serveur** à chaque requête ;
aucun paiement n'achète un rang.

### Publication contrôlée des opportunités
Chaque offre est saisie par l'entreprise dans un formulaire structuré : intitulé, description, type de contrat, lieu, niveau de diplôme requis, spécialité, expérience, compétences, rémunération (montant fixe, fourchette, à négocier ou non rémunéré), périodicité, avantages et date limite. Une nouvelle offre est toujours créée en **brouillon**. L'entreprise la soumet ensuite à la revue AgriConnect ; elle n'est visible publiquement qu'après approbation administrative. L'administration peut approuver, demander des corrections avec motif ou rejeter. Toute modification d'une offre déjà publiée la renvoie en revue avant sa nouvelle diffusion.

### Consentement et classement de correspondance
Le consentement au matching (`matching_opt_in`) est distinct de la visibilité publique (`visible`) et des autorisations de contact/CV. Il est désactivé par défaut, y compris pour les comptes existants après migration. Le candidat peut le retirer à tout moment ; cela supprime ses instantanés personnels de matching sans bloquer la consultation des offres ni la candidature manuelle. À l'approbation d'une offre, le système calcule un instantané explicable pour les profils actifs ayant consenti, enregistre score, rang, total de profils correspondants et critères, puis notifie individuellement chaque candidat. Dans une recherche liée à une offre, les profils ayant le niveau requis sont présentés en premier et leur nom complet est visible ; les coordonnées restent protégées jusqu'à la consultation autorisée.

### CV candidat
Le candidat conserve la rubrique de dépôt et de gestion de CV (PDF/DOCX, limites et contrôles du backend), en complément de ses diplômes, expériences, compétences, réalisations, candidatures et paramètres de confidentialité.

## 2. Prérequis (Windows 11)

1. **Python 3.11+** — https://www.python.org/downloads/ (cochez *Add python.exe to PATH*). Vérifiez : `python --version`
2. **Node.js 20 LTS+** — https://nodejs.org/ . Vérifiez : `node --version` et `npm --version`
3. *(Optionnel)* Git. PostgreSQL n'est **pas** nécessaire : SQLite est utilisé par défaut.

## 3. Installation (PowerShell, dans le dossier du projet)

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # une seule fois, si les scripts sont bloqués
.\scripts\setup.ps1 -Demo                              # installe tout, crée la base et les comptes de démonstration
.\scripts\dev.ps1                                      # lance backend (8000) + frontend (5173)
```

Ouvrez http://localhost:3000 . Le script `dev.ps1` recharge automatiquement les données fictives à chaque démarrage local ; définir `DEV_SEED_DEMO=false` pour les désactiver. Documentation interactive de l'API : http://127.0.0.1:8000/docs

### Installation manuelle équivalente
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env            # puis éditez .env (SECRET_KEY, ADMIN_PASSWORD…)
.\.venv\Scripts\python.exe -m app.cli init-db      # migrations Alembic + référentiels + administrateur
.\.venv\Scripts\python.exe -m app.cli seed-demo    # (facultatif) données et comptes de démonstration
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
# nouveau terminal :
cd frontend
npm install
npm run dev
```

## 4. Comptes fictifs de test (mot de passe : `Demo2026!`)

Créés par `seed-demo` (ou `SEED_DEMO=true`). Ils utilisent le domaine réservé `agriconnect.test` et sont séparés des comptes réels. Les fonctions de paiement restent en attente de connexion à une passerelle réelle.

| Rôle | Email | Intérêt |
|---|---|---|
| Administrateur | `ADMIN_EMAIL` / `ADMIN_PASSWORD` de votre `.env` (défaut : `admin@agriconnect.local` / `ChangezMoi2026`) | Tout gérer |
| Établissement validé | `etablissement@agriconnect.test` | Contient une liste « à traiter » |
| Établissement en attente | `etablissement.attente@agriconnect.test` | À valider par l'admin |
| Entreprise **Professional** | `entreprise.pro@agriconnect.test` | Recherche, correspondance, 3 offres |
| Entreprise **Starter** | `entreprise.starter@agriconnect.test` | Fonctions limitées (pas de recherche) |
| Entreprise sans abonnement | `entreprise.sansabo@agriconnect.test` | Publication/recherche bloquées (402) |
| Entreprise en attente | `entreprise.attente@agriconnect.test` | Dossier à valider |
| Diplômés | `diplome.deat`, `diplome.licence`, `diplome.ingenieur`, `diplome.bts`, `diplome.master`, `diplome.indisponible` `@agriconnect.test` | Profils variés (DEAT, Licence, Ingénieur…) |
| Diplômé non activé | `diplome.attente@agriconnect.test` | Réémettez son invitation depuis Admin → Utilisateurs |

La commande `python -m app.cli accounts` réaffiche cette liste. Pour ouvrir l’administration, utilisez le lien « Administration » dans le pied de page ou `/administration`, puis connectez-vous avec `ADMIN_EMAIL` et `ADMIN_PASSWORD`. Si le compte est absent ou si ses identifiants ont changé, mettez à jour ces deux valeurs dans `backend/.env`, puis exécutez `python -m app.cli create-admin` depuis `backend` ; cette commande crée ou réinitialise le compte admin sans toucher aux autres comptes.

## 5. Tester les parcours à la main

**A. Établissement → administration → candidat**
1. Connectez-vous en `etablissement@…` → *Listes transmises* → *Télécharger le modèle*, complétez-le, transmettez-le. Les lignes invalides sont signalées (à corriger).
2. Déconnexion ; connectez-vous en administrateur → *Listes des établissements* → *Examiner* → *Valider toutes les lignes sans erreur* → *Créer les comptes* → **copiez ou exportez les liens** (affichés une seule fois).
3. Ouvrez un lien dans une fenêtre de navigation privée → choisissez un mot de passe, acceptez les conditions → profil du diplômé. Complétez profil, formation, compétences et déposez le CV (PDF/DOCX). Dans *Profil et visibilité*, le candidat peut accepter ou refuser séparément le matching ; il peut toujours consulter les offres et candidater manuellement.
4. Retour établissement → *Candidats transmis* : le compte passe à « Actif ».

**B. Entreprise**
1. *Espace organisation* → créer une entreprise → l'admin la valide (*Entreprises et établissements*).
2. *Accès entreprise et facturation* → choisir un accès → **Confirmer le règlement** → l'accès est actif ; facture imprimable.
3. *Mes offres* → *Nouvelle offre* : remplissez le formulaire complet (intitulé, missions, rémunération, avantages, lieu, date limite, diplôme et compétences requis). Enregistrez le brouillon, puis soumettez-le à validation. L'administration peut approuver, demander des corrections motivées ou rejeter ; une offre n'est jamais publique avant approbation. Essayez de dépasser le quota Starter (2 offres publiées) : refus 402.
4. En Professional : *Rechercher des talents* (filtres, classement selon une offre), « Pourquoi ce profil ? », ouverture d'un profil (compté au quota mensuel).
5. Candidatez avec un diplômé, puis traitez la candidature (examen → présélection → entretien → acceptée) : le diplômé est notifié ; la collaboration vérifiée permet d'**évaluer** et de **recommander**.

**C. Droits et sécurité** : essayez avec un diplômé d'ouvrir `/api/company/offers` (403), sans connexion (401), suspendez un compte depuis l'admin (sa session s'arrête immédiatement).

## 6. Configuration (`backend\.env`, voir `.env.example`)

| Variable | Rôle |
|---|---|
| `SECRET_KEY` | Signe les sessions. **Obligatoire en production** (le démarrage est refusé avec `COOKIE_SECURE=true` si elle garde la valeur par défaut) |
| `DATABASE_URL` | SQLite par défaut ; PostgreSQL : `postgresql+psycopg://user:mdp@hote:5432/agriconnect` (+ `pip install "psycopg[binary]"`) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Compte administrateur créé au premier démarrage |
| `APP_URL` | Base des liens d'invitation (votre URL publique en production) |
| `COOKIE_SECURE` | `true` derrière HTTPS |
| `PAYMENT_MODE` | `demo` (simulation) ou `live` (passerelle réelle, voir §7) |
| `SMTP_*` | Envoi des invitations par courriel (facultatif) |
| `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `MAX_LIST_ROWS` | Fichiers téléversés et limites |

## 7. Services externes : ce qui reste à configurer

**Paiements.** Le mode de règlement actuel n'encaisse pas encore d'argent : les écrans restent prêts à recevoir une passerelle réelle, mais **aucun paiement réel ne fonctionne** tant que celle-ci n'est pas configurée.
Pour passer en réel (FedaPay, KkiaPay, CinetPay, PayDunya… adaptés au Bénin / mobile money) :
1. Créez un compte marchand et récupérez les clés (sandbox d'abord).
2. Dans `backend/app/payments.py`, implémentez une classe `PaymentProvider` (`create_checkout`, `verify_webhook`) et enregistrez-la dans `PROVIDERS`.
3. Complétez `POST /api/billing/webhook` (vérification de signature, puis appeler `settle()` de `routes_billing.py`).
4. `.env` : `PAYMENT_MODE=live`, `PAYMENT_PROVIDER=…`, `PAYMENT_API_KEY=…`, `PAYMENT_WEBHOOK_SECRET=…`. En mode `live`, la simulation est refusée par le serveur.
En attendant, l'administrateur peut **rapprocher manuellement** un règlement reçu hors plateforme (*Abonnements et paiements → Marquer reçu*) ou octroyer un abonnement.
Limites connues : pas de prorata lors d'un changement de formule ; le renouvellement automatique n'est qu'un indicateur de rappel (aucun prélèvement ni rappel automatique).

**Courriel.** Sans `SMTP_HOST`, l'administrateur copie ou exporte (CSV) les liens d'invitation à la création des comptes ; « Réémettre l'invitation » en génère un nouveau. Le jeton en clair n'est jamais stocké (empreinte SHA-256 uniquement).

## 8. Architecture (détails dans `docs/ARCHITECTURE.md`)

- `backend/` FastAPI + SQLAlchemy 2 + Alembic. Logique métier pure et testée dans `app/logic/` ; routes par rôle `routes_*.py`.
- `frontend/` React 18 + TypeScript + Vite, interface en français, responsive, un espace par rôle ; accueil avec carrousel photographique et contrôles manuels/accessibilité.
- Sécurité : mots de passe scrypt, sessions par cookie HttpOnly signé (invalidées au changement de mot de passe/suspension), en-tête anti-CSRF, limitation des tentatives de connexion et d'activation (en mémoire : un seul processus), contrôle des rôles côté serveur, validation Pydantic, requêtes SQLAlchemy paramétrées, CV contrôlés (extension + signature + taille) et stockés hors dossier public sous nom aléatoire.
- Migrations : `0001` est l'instantané initial ; `0002` ajoute le circuit de revue, les champs de rémunération/avantages, le consentement matching et les instantanés `offer_matches` ; `0003` ajoute la récupération de mot de passe. Les anciennes offres déjà publiées sont replacées en `pending_review` et ne sont pas considérées comme approuvées rétroactivement. Évolutions suivantes : `alembic revision --autogenerate -m "…"` puis `alembic upgrade head` (depuis `backend`).

## 9. Dépannage

| Symptôme | Piste |
|---|---|
| `Set-ExecutionPolicy` / script bloqué | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `python` introuvable | Réinstallez Python en cochant *Add to PATH*, rouvrez PowerShell |
| `ModuleNotFoundError` | Utilisez `.\.venv\Scripts\python.exe` (et non le Python global) |
| Erreur au démarrage mentionnant SQLAlchemy/mapper | Copiez le message complet (voir « Ce que j'attends de vous » ci-dessous) |
| `npm install` échoue | Supprimez `frontend\node_modules`, relancez ; vérifiez la version de Node |
| Page blanche / erreur 502 sur `/api` | Le backend n'est pas lancé (port 8000) |
| 403 « En-tête de sécurité manquant » | Appel API hors de l'interface : ajoutez l'en-tête `X-Requested-With: agriconnect` |
| Base corrompue en essai | `.\scripts\reset-db.ps1 -Demo` (supprime les données locales) |

**Ce que j'attends de vous** en cas d'erreur : la commande lancée et le message complet (ou la sortie de `.\scripts\test.ps1`) ; je corrige à partir de là.

## 10. Tests

`.\scripts\test.ps1` lance `pytest` (logique + parcours API) puis la vérification de types TypeScript. Le détail de ce qui a été **réellement exécuté** lors de la livraison et de ce qui ne l'a **pas** été est dans `docs/TESTS.md`.

## 11. Limitations restantes

- Code **non exécuté** de bout en bout (voir encadré en tête) ; aucun test sur navigateur ni mobile réel.
- Pas de passerelle de paiement réelle, pas de courriel testé, pas de rappel automatique d'échéance.
- Les pages juridiques (conditions, confidentialité, mentions) sont des **projets à faire valider par un juriste** ; factures sans mentions légales complètes.
- Évaluation réciproque des entreprises par les talents, tests techniques, assistant conversationnel : prévus en phase 3 du cahier des charges, **non réalisés**.
- Pas de favoris/présélection d'entreprise distincte des candidatures, pas de statistiques d'insertion détaillées pour les établissements. Les photos actuelles sont des visuels Pexels d'Afrique de l'Ouest/Centrale, pas des photographies prises au Bénin ; prévoir à terme un reportage local avec autorisations.
- Limiteur de tentatives en mémoire (un seul processus) ; sauvegardes et chiffrement au repos à prévoir côté hébergement.
- Les tarifs de départ (15 000 / 45 000 / 120 000 FCFA) sont **indicatifs** et modifiables dans l'administration ; la pondération de réputation et de correspondance est une hypothèse à calibrer.


## 12. Photographies de l'accueil
Le carrousel utilise trois photographies documentaires sous licence Pexels, avec crédit visible dans l'interface. Les images sont chargées depuis Pexels : une connexion Internet est nécessaire ; un visuel SVG local sert de secours pour le carrousel principal. Les références, photographes et conditions de licence sont détaillés dans `frontend/public/images/PHOTOGRAPHIES-LICENCES.md`. Ne pas présenter ces clichés comme des photos prises au Bénin.
