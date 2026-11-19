# TODO — Refonte AgriConnect

## Accueil visuel et FAQ
- [x] Au début de l’accueil, plusieurs photographies locales alternent dans un carrousel fluide, responsive desktop/mobile, avec crédits, indicateurs, contrôles précédent/suivant et pause ; les images existantes du projet sont réutilisées.
- [x] Le carrousel reste utilisable au clavier et désactive ses animations lorsque `prefers-reduced-motion` est activé.
- [x] La section « Questions fréquentes » est plus discrète visuellement, conserve ses réponses dépliables et expose un focus visible sans prendre toute la place.

## Profils entreprises et établissements
- [x] Une entreprise peut ouvrir « Mon organisation », retrouver ses informations enregistrées et modifier le nom, la description, le secteur, la commune, le site, le téléphone et la référence IFU/RCCM.
- [x] Un établissement peut ouvrir « Mon établissement », retrouver ses informations enregistrées et modifier le nom, la description, la commune, le site, le téléphone et la référence officielle.
- [x] Les champs sont contrôlés côté interface et côté API ; les erreurs sont lisibles et la confirmation « Informations enregistrées » reste visible après réussite.
- [x] Les formulaires n’écrasent pas les valeurs saisies pendant le chargement et la mise à jour est rechargée après sauvegarde.

## Mot de passe oublié
- [x] Depuis la connexion, l’utilisateur peut demander un lien de récupération avec son adresse email.
- [x] La réponse de demande ne révèle pas si l’adresse existe ; le lien est temporaire, à usage unique et stocké uniquement sous forme hachée.
- [x] Un lien valide permet de définir un nouveau mot de passe conforme aux règles existantes et ferme les sessions précédentes.
- [x] Les états d’email invalide, de lien expiré/invalide, d’erreur d’envoi et de réinitialisation réussie sont explicites.

## Données fictives de test du matching
- [x] La prévisualisation fournit des comptes fictifs d’entreprises, d’établissement et de diplômés, avec leurs identifiants de démonstration clairement séparés des données réelles.
- [x] Les profils fictifs contiennent diplômes, spécialités, compétences, expériences, localisations et disponibilités variées ; le consentement au matching est activé pour permettre les essais.
- [x] Plusieurs offres fictives publiées et leurs snapshots de correspondance sont disponibles pour consulter les scores, créer de nouvelles offres et tester le classement côté entreprise.
- [x] Le chargement est idempotent et limité au mode démonstration local ; les données de démonstration ne sont pas activées par défaut en production.

## Activation manuelle des profils diplômés
- [x] Après création manuelle, l’administration affiche un lien d’activation ouvrable et réécrit l’hôte vers l’origine locale courante, afin d’éviter le décalage entre les ports 5173 et 3000.

## Présentation sans tarifs ni vocabulaire de simulation
- [x] Aucun prix, montant de formule ou libellé « démo »/« démonstration » n’est visible dans les interfaces publiques, entreprise et comptes fictifs ; les accès existants restent fonctionnels.
- [x] La page d’accueil conserve les statistiques de diplômés, entreprises et offres publiées, mais ne présente plus de statistique d’établissement.

## Matching et sélection des talents
- [x] Lorsqu’une offre est sélectionnée, les profils satisfaisant le niveau d’étude requis sont classés avant ceux qui ne le satisfont pas, puis le score détaillé départage les profils du même groupe.
- [x] Les résultats de matching mettent en avant le nom complet du diplômé ainsi que son diplôme, son expérience, sa réputation, sa disponibilité et ses compétences, sans exposer ses coordonnées prématurément.
- [x] Une entreprise peut sélectionner une ou plusieurs personnes depuis les résultats liés à une offre ; la sélection est enregistrée sans doublon et le diplômé reçoit une notification lisible dans son interface.
- [x] L’action de sélection respecte les droits de l’entreprise, l’offre choisie et la visibilité du profil ; les erreurs et la confirmation sont visibles dans l’interface.

## Validation technique et livraison
- [x] Le manifeste `/manus-routes.json` liste `/mot-de-passe-oublie` et `/reinitialiser-mot-de-passe`.
- [x] Les diagnostics TypeScript sont activés ; le typecheck/build frontend et les tests backend passent.
- [x] La migration de base de données est présente et compatible avec l’initialisation SQLite existante.

## Tarif entreprise annuel
- [ ] L’offre entreprise affichée et facturable est annuelle, à 15 000 FCFA pour la première année, pour chaque entreprise.
- [ ] L’interface ne propose plus de durée mensuelle, trimestrielle ou semestrielle pour ce parcours ; la facture et le récapitulatif indiquent clairement 15 000 FCFA / an.
- [ ] Le contrôle d’accès, la validation du paiement et les quotas existants continuent de fonctionner avec cette formule annuelle.

## Aperçu et photo du diplômé
- [ ] Après connexion, l’aperçu étudiant présente une fiche cadrée avec le nom complet en grand caractère, la photo, le titre professionnel, le diplôme/intitulé exact, la localisation, la disponibilité, l’expérience, la réputation et la complétude du profil.
- [ ] Le diplômé peut téléverser, remplacer et supprimer une photo depuis son espace ; le fichier est contrôlé, stocké hors du dossier public et réaffiché lors des connexions suivantes.
- [ ] Les états de chargement, d’erreur, de suppression et de réussite sont compréhensibles sur ordinateur et mobile.

## Matching précis et lisible
- [ ] Les résultats restent classés en priorité selon le respect du niveau d’étude requis, puis par le score de matching.
- [ ] Chaque résultat montre clairement le nom complet du diplômé, l’intitulé exact du diplôme, son niveau, sa spécialité, son score/rang, son expérience, sa disponibilité et ses compétences ; aucun résultat ne repose sur une information vague.
- [ ] Les données restent cohérentes entre l’API, les cartes de matching, les recommandations et le détail d’un talent.
