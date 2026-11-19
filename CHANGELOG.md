# Historique des versions

## AgriConnect 1.1.0 — 18 novembre 2026

- Refonte visuelle de la page d'accueil, nouvelle promesse, carrousel photo Pexels avec navigation, pause et respect de la préférence de réduction des animations.
- Photographies documentaires africaines créditées, documentation de licence et visuel local de secours.
- Formulaire de publication des opportunités enrichi : rémunération fixe/fourchette/à négocier/non rémunérée, périodicité, atouts et avantages.
- Publication obligatoirement soumise à la revue de l'administration ; approbation, demande de corrections ou rejet motivé.
- Les modifications d'une offre publiée déclenchent une nouvelle revue.
- Consentement explicite au matching, distinct de la visibilité du profil et désactivé par défaut.
- Instantanés de correspondance avec score, rang individuel, critères explicables et notifications ; retrait du consentement sans bloquer la candidature manuelle.
- Interface candidat enrichie avec espace « Mes correspondances » et explication des critères. Le dépôt et la gestion du CV existants sont conservés.
- Migration `0002` pour les bases existantes ; les anciennes offres publiées repassent en attente de contrôle.
- Tests backend : 67 réussis ; migrations SQLite neuve et mise à niveau 1.0 vérifiées ; syntaxe TS/TSX contrôlée. Le build frontend complet reste à exécuter sur une machine disposant des dépendances npm.

## 1.1.2
- Accueil : nouvelle image (agriculture connectée), carrousel réduit à une photo sans contrôles.
- Cartes Diplômés et Établissements : photos locales (/images/graduates.jpg, /images/schools.jpg).
- Non testé : build Vite non exécuté dans cet environnement (pas de réseau).
- Navigation : Maison / Nos services / À propos de nous au centre ; Créer un espace et Accéder à mon espace à droite (ancres #services et #a-propos sur l accueil).
- Mission, Vision, Entreprises : nouvelles photos locales (plus aucune image Pexels distante).

## 1.1.4
- Accueil : bannière plein écran immersive (photo haute résolution, voile dégradé, animations d entrée, bouton de défilement), carte supprimée.
- Section Mission : image agriculture connectée (IoT).

## 1.1.5
- Menu : Contact ajouté au centre ; Créer un espace placé à l extrême droite.
- Page Contact refaite (bandeau, cartes e-mail / WhatsApp, sujets, champs flottants, confirmation animée). Le sujet choisi est ajouté au début du message envoyé.
