# Plan — Version AgriConnect 1.1.0 enrichie

## Direction visuelle

Style retenu : **éditorial agricole premium**, en continuité avec l’archive fournie.

- **Mouvement design :** magazine numérique agricole chaleureux, crédible et ancré au Bénin.
- **Principes :** confiance, lisibilité, identité humaine et lecture immédiate.
- **Philosophie couleur :** vert profond pour la confiance, lime pour l’élan, ivoire pour le calme de lecture.
- **Mise en page :** aperçu étudiant cadré comme une fiche de profil, avec nom très visible, identité visuelle et informations structurées plutôt qu’une grille uniforme.
- **Signatures :** avatar circulaire ou carré doux, bandeau d’identité, cartes de critères explicites et badge tarif annuel.
- **Interaction :** actions importantes visibles, états d’attente et d’erreur explicites ; sélection et téléversement confirmés immédiatement.
- **Animation :** transitions discrètes, désactivées sous `prefers-reduced-motion`.
- **Typographie :** sans-serif système, nom du diplômé en grande taille, intitulé professionnel et diplôme en niveaux secondaires distincts.
- **Voix :** directe, professionnelle et précise : aucun résultat de matching ne doit être présenté avec une information vague.

## Implémentation

- Repartir de l’archive `agriconnect(4).zip` comme base fonctionnelle et conserver les routes et rôles existants.
- Remplacer les trois formules tarifaires par un accès entreprise annuel clair à **15 000 FCFA pour la première année**, valable pour chaque entreprise ; la durée est annuelle, l’interface ne propose plus de choix mensuel/trimestriel et la facture affiche explicitement le montant annuel.
- Conserver le contrôle d’accès, les quotas et le paiement existants, mais aligner le plan actif, le seed local et les réponses API sur le tarif annuel unique.
- Ajouter une photo de profil étudiant persistée côté serveur : stockage sécurisé hors dossier public, contrôle de type et de taille, remplacement/suppression, route protégée de lecture et affichage dans l’aperçu après connexion.
- Recomposer l’aperçu étudiant autour d’une fiche d’identité : photo, nom complet en grand caractère, titre professionnel, localisation, disponibilité, niveau/intitulé de diplôme, complétude, réputation et expérience.
- Garder une section Profil séparée pour modifier les informations et gérer la photo sans écraser les saisies en cours.
- Rendre le matching explicite dans les cartes et résultats : nom complet, intitulé exact du diplôme, niveau, spécialité, score, rang, expérience, disponibilité et compétences ; éviter les libellés génériques tels que « profil correspondant » sans détail.
- Conserver la priorité aux profils qui satisfont le niveau requis, puis départager par score ; afficher l’identité en premier dans les recommandations et les sélections entreprise.
- Ajouter les migrations nécessaires sans casser la base SQLite locale de l’archive ; mettre à jour les comptes fictifs et leurs plans pour permettre un test immédiatement compréhensible.

## Structure concernée

- `frontend/src/pages/Plans.tsx` et `frontend/src/pages/dash/Company.tsx` : tarif annuel unique, facture et accès entreprise.
- `frontend/src/pages/dash/Graduate.tsx` et `frontend/src/styles.css` : aperçu étudiant, photo, identité et responsive.
- `frontend/src/ui.tsx` : cartes de talents/matching avec identité et intitulé exact.
- `backend/app/models.py` : chemins et noms de photo du profil étudiant.
- `backend/app/files.py` : validation, stockage et suppression des images de profil.
- `backend/app/routes_graduate.py` et `backend/app/services.py` : API profil/photo et résumé détaillé du matching.
- `backend/app/seed.py`, `routes_billing.py` et `logic/entitlements.py` : plan annuel à 15 000 FCFA et données locales cohérentes.
- `backend/migrations/versions/0006_profile_photo.py` et éventuellement migration de normalisation tarifaire : compatibilité de schéma.
