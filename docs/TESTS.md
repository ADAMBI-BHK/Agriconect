# Tests AgriConnect 1.1 — état de vérification

## Contrôles réellement exécutés dans l'environnement de livraison

| Contrôle | Résultat |
|---|---:|
| `pytest -q` dans `backend` (parcours API, rôles, sécurité, matching, réputation, offres, CV, quotas) | **67 / 67 réussis** |
| `python -m compileall -q backend/app backend/migrations` | **OK** |
| Migration `alembic upgrade head` sur une base SQLite neuve et sur un schéma 1.0 simulé | **OK**, révision `0002` |
| Vérification des colonnes ajoutées et de la table `offer_matches` après migration | **OK** |
| Analyse syntaxique TypeScript/TSX avec le compilateur TypeScript (19 fichiers) | **0 erreur de syntaxe** |

Les tests API couvrent notamment : création d'offres en brouillon, blocage de publication directe, soumission, revue administrative, demande de correction et nouvelle soumission, validation du salaire et des avantages, quota d'abonnement, consentement matching, snapshot/rang individuel, retrait du consentement et maintien de la candidature manuelle.

## Contrôles non réalisés

- `npm ci` / `npm install` complet : les tentatives ont expiré dans l'environnement de livraison.
- `npm run build` / `vite build` : non exécuté (installation Vite incomplète).
- `npm run typecheck` avec les types React complets : non exécuté.
- Tests dans un vrai navigateur, responsive sur appareils mobiles et tests d'accessibilité complets.
- Envoi SMTP, paiement réel, PostgreSQL, audit de sécurité indépendant et test de charge.

## Procédure locale à exécuter sous Windows 11

Dans PowerShell, depuis le dossier du projet :

```powershell
cd frontend
npm ci
npm run typecheck
npm run build
```

Dans un autre terminal :

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Puis lancer `..\scripts\dev.ps1` et parcourir les scénarios décrits dans le README. Ne considérer aucun contrôle comme réussi avant d'avoir observé sa sortie locale.
