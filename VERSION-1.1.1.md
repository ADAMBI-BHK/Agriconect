# AgriConnect 1.1.1 — notes de version

- Refonte de la vitrine : hiérarchie visuelle, espacements, typographie, boutons, sections et pied de page.
- Présentation développée des trois publics : diplômés, entreprises clientes et établissements partenaires.
- Retrait de la rubrique publique « Opportunités » de la navigation et de la page d’accueil. Les offres et candidatures restent dans les espaces privés des utilisateurs et la modération reste dans l’administration.
- Retrait du bandeau global de démonstration. Les avertissements liés aux paiements simulés restent dans les parcours de paiement afin de ne pas faire croire qu’un paiement réel est activé.
- Coordonnées affichées en texte simple dans le pied de page : hamdaneadambi@gmail.com et WhatsApp +229 0166338310 (sans bouton WhatsApp).
- Accès admin dédié via `/administration`. Ajout de `python -m app.cli create-admin` pour créer ou réinitialiser le compte à partir de `ADMIN_EMAIL` et `ADMIN_PASSWORD` dans `backend/.env`.
- Photographies documentaires Pexels utilisées dans le carrousel et les sections de présentation ; crédits et provenance documentés dans `frontend/public/images/PHOTOGRAPHIES-LICENCES.md`.

## Vérifications

- Backend : `python -m compileall -q backend/app` réussi.
- Tests backend : 67 réussis.
- Build frontend non exécuté ici : l’installation `npm ci` a dépassé le délai disponible dans l’environnement de livraison. À lancer localement avec `npm ci`, puis `npm run build` et `npm run typecheck`.
