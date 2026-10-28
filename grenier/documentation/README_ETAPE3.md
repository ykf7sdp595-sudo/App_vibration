# Étape 3 — SWEEPS

Copie autonome de l'étape 2 validée ; le dépôt GitHub est inchangé.

## Fichiers
- `App_vibration.py` : deux onglets `SWEEPS` et `Tracé libre (historique)` ; export et filtres antérieurs maintenus.
- `sweeps.py` : recherche des couples temps/fréquence déclarés, contrôle des supports et des données, calculs descriptifs sans interpolation ni tri.
- `tests/test_sweeps.py` : 7 nouveaux tests.
- `csv_reader.py`, `column_registry.py`, et leurs tests : identiques à l'étape 2.

## Vérification locale
```powershell
python -m unittest discover -s tests -v
python -m streamlit run App_vibration.py
```
Importer `csv_test_sin.csv`. SWEEPS doit proposer en priorité `[36] Time (min)` avec `[37] Frequency (Hz)` et afficher les 7 572 points, la courbe parcourue en ordre de mesure et ses 23 changements de sens. Sélectionner `[61] Time (ms)` avec `[37] Frequency (Hz)` doit refuser le tracé. Vérifier qu'un petit CSV `Time (s),Frequency (Hz)` fonctionne. Vérifier le tracé libre et l'export CSV conservés.

## Limites
Les tests automatiques ne couvrent pas la sortie visuelle dans un navigateur. La fréquence de consigne n'est annoncée que pour le profil confirmé, pas déduite des seuls noms d'en-tête. Les vitesses descriptives sont calculées en Hz/min et octaves/min, les courbes restent dans les unités déclarées. La suggestion d'échelle logarithmique n'est activée que sur une grille globalement strictement croissante à rapport constant ; l'utilisateur peut la modifier.
