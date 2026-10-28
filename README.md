# App_vibration

Application locale Streamlit de lecture de CSV et d’analyse vibratoire.
Python 3.12 recommandé. Les dépendances directes validées sont dans `requirements.txt`.

## Installation et lancement sous Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run App_vibration.py
```

Sous Linux/macOS, utiliser `python3.12 -m venv .venv`, puis
`.venv/bin/python` à la place de `.\.venv\Scripts\python`.
Le navigateur affiche l'application locale ; aucun compte ni service distant requis.

## Utilisation

Importer le CSV puis choisir une analyse : SWEEPS, VIBRATIONS, CHOCS,
PSD ou Tracé libre. Seule l’analyse sélectionnée s’exécute.
La lecture, conversion numérique et construction du registre sont mises en cache
(au maximum deux fichiers). Les calculs utilisent les données complètes.
Les filtres latéraux concernent le tracé libre et l’export, pas les analyses spécialisées.
Cliquer sur « Préparer l’export CSV », puis télécharger le fichier.
Si les filtres changent, préparer de nouveau l’export.

La réduction du tracé libre conserve les extrémités et les extrema par intervalle,
mais pas nécessairement chaque pic local. Les valeurs manquantes restent présentes
pour conserver les interruptions. Si leur nombre empêche de respecter la limite,
le tracé est refusé avec une explication. Les analyses et exports ne sont pas réduits.
Les pics détectés sont des maxima locaux : ils ne constituent pas un verdict de conformité.

## Vérification

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Quatre tests nécessitent `/mnt/data/csv_test_sin.csv` et sont ignorés en son absence.
Les autres utilisent des données synthétiques ; ils ne remplacent pas une validation
avec les fichiers d’essais réels. Les documents README_ETAPE* décrivent l’historique.

## Organisation

- `App_vibration.py` : entrée et navigation.
- `csv_reader.py`, `column_registry.py` : import et description des colonnes.
- `science.py`, `selection.py`, `sweeps.py`, `vibrations.py` : contrôles et calculs.
- `specialized_tabs.py` : interfaces spécialisées et réglages des graphiques.
- `plotting.py` : réduction des données pour l’affichage uniquement.
- `tests/` : tests automatisés.

`test.py` est une application RF distincte, conservée pour éviter de perdre du
travail existant. Elle n’est pas lancée par App_vibration et n’est pas un test de
cette application. Sa dépendance `scikit-rf` est volontairement exclue de cette installation.
