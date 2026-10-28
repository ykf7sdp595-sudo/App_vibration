# Historique des versions

## V1.1 — 2026-10-28

Version issue de V1.0 (30332bb), publiée sur une branche distincte pour préserver
la version existante. Aucun fichier supprimé dans cette version.

- Gestion des valeurs non numériques dans les vues CHOCS et PSD fournie.
- Préparation des données mise en cache, une seule analyse exécutée à la fois.
- Export CSV préparé à la demande et réduction des allocations mémoire.
- Réduction du tracé libre avec limite stricte et extrema par intervalle.
- Libellé de détection des pics clarifié.
- Instructions d’installation et dépendances directes versionnées.
- Tests supplémentaires : données invalides et réduction des graphiques.

Validation : 41 tests réussis, 4 ignorés (CSV de référence absent).
Navigation des cinq vues et préparation de l’export vérifiées sur CSV synthétique.
La consommation sur le poste Windows reste à mesurer avec les fichiers réels.

## V1.0

Version de référence : commit 30332bb (« App_vibration V1.0 »).
