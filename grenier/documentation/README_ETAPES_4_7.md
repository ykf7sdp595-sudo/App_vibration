# App_vibration — étapes 4 à 7

Base : copie de l’étape 3 validée. Aucune modification du dépôt GitHub.

## Fichiers
- `App_vibration.py` : onglets SWEEPS, VIBRATIONS, CHOCS, PSD et ancien Tracé libre ; export CSV conservé ; réinitialisation des sélections au changement de fichier.
- `csv_reader.py` : ajout de la résolution **écrite par valeur** des axes Time, sans perdre les lignes irrégulières. Les timestamps exportés n'ont pas tous autant de décimales.
- `column_registry.py`, `sweeps.py` : repris de l’étape 3.
- `selection.py` : appariement par index, unité et support de lignes ; identification conservatrice du profil sinus de référence.
- `vibrations.py` : détection de grille à rapport constant et test de cohérence accélération/vitesse/déplacement.
- `science.py` : extraction de fs uniquement depuis le temps, FFT unilatérale avec fenêtre/detrend déclarés, contrôle Parseval, PSD Welch, RMS par bande.
- `specialized_tabs.py` : interfaces spécialisées, refus explicites, graphiques et export JSON des paramètres.
- `tests/test_science.py` : tests sur signaux synthétiques et le CSV réel ; les tests historiques restent présents.

## Dépendances
Identiques au projet : `streamlit`, `pandas`, `plotly`, `numpy`, `scipy`. Aucune dépendance ajoutée.

## Tests exécutés ici
`python -m unittest discover -s tests -v` (31 tests réussis, avec pandas 2.2.3). Python compilé via `python -m compileall -q .`.
L'interface Streamlit n'a **pas** été exécutée dans un navigateur. Refaire les tests sous pandas 3.1.0 sur le PC cible.

## Vérification locale
1. Décompresser dans un dossier dédié, ouvrir ce dossier dans VS Code. `python -m streamlit run App_vibration.py`.
2. Importer `csv_test_sin.csv` : 7 572 lignes ; SWEEPS fonctionne comme à l’étape 3.
3. VIBRATIONS : profil fréquentiel à 2 000 points, choix par défaut Demand1 (G) et Control1 (G), limites en G possibles. Vérifier bascule log/linéaire ; activer le contrôle a/v/d si souhaité.
4. CHOCS : 4 voies, 4 096 points ; FFT décochée au départ. L'activer ; vérifier `fs ≈ 65 536 Hz`, `Δf ≈ 16 Hz`. Essayer une fs attendue de 8 192 Hz : la FFT doit être refusée.
5. PSD : le CSV sinus de référence affiche « Aucune PSD fournie » et refuse le calcul Welch. Essayer un CSV d'essai aléatoire distinct ; confirmer la nature aléatoire ; choisir explicitement la taille de segment et autres paramètres ; 5 segments au minimum.
6. Vérifier les téléchargements JSON des paramètres, l'export CSV, le tracé libre historique et le changement de fichier dans la même session.

## Limites explicites
- Le contrôle de stationnarité est **déclaratif** : la confirmation de l'utilisateur est requise ; aucun test statistique automatique ne certifie la stationnarité.
- Le profil de référence sinus est reconnu par son schéma d'en-têtes, pas par le nom du fichier. Un autre export sinus non reconnu reste de type « inconnu » et requiert une confirmation explicite avant PSD.
- Les degrés de liberté Welch `≈ 2K` et l'incertitude `≈ 1/√K` sont indicatifs ; ils ignorent la corrélation introduite par le recouvrement et la fenêtre.
- Il n'y a pas de SRS ni de verdict automatique entre PSD fournie et PSD calculée.
- Le mode Tracé libre conserve son comportement historique, y compris son tri de l’abscisse, pour éviter de changer une fonction validée.
