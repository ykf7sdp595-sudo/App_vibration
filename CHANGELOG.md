# Historique des versions

## V1.3

- Interface harmonisée : import latéral, graphiques avant leurs réglages,
  légendes en dessous, panneaux repliés et informations d'import regroupées.
- Fermeture automatique 15 secondes après la fermeture du dernier onglet.
- Documentation et sauvegarde GitHub organisées ; version précédente conservée
  sur la branche `v1.2`. Les calculs scientifiques restent inchangés.

La V1.3 locale comprenait déjà les évolutions suivantes :

- Import de plusieurs CSV/TXT en une seule opération, avec un onglet par fichier.
- Analyses, filtres, graphiques et exports indépendants, même en cas de noms identiques.
- Un fichier vide ou illisible ne bloque pas les autres fichiers du lot.
- Nettoyage des réglages des fichiers retirés et cache de lecture porté à seize entrées.
- Tests d’intégration multi-fichiers pour les cinq analyses et la suppression de fichiers.

## Rangement du dépôt — 2026-10-28

- V1.1 active sur `main` (PR nº 1 déjà fusionnée).
- Anciennes notes et caches compilés déplacés dans `grenier/`.
- Ancienne application RF archivée depuis le tag V1.1.
- Aucun changement de calcul ; tag V1.1 et historique conservés.

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
