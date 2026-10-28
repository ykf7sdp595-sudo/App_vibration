# App_vibration — V1.1

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
avec les fichiers d’essais réels. Les anciennes notes de développement sont dans [grenier/documentation](grenier/documentation/).

## Organisation

- `App_vibration.py` : entrée et navigation.
- `csv_reader.py`, `column_registry.py` : import et description des colonnes.
- `science.py`, `selection.py`, `sweeps.py`, `vibrations.py` : contrôles et calculs.
- `specialized_tabs.py` : interfaces spécialisées et réglages des graphiques.
- `plotting.py` : réduction des données pour l’affichage uniquement.
- `tests/` : tests automatisés.

- `requirements.txt` : dépendances de l’application.
- `CHANGELOG.md` : historique des versions.
- [`grenier/`](grenier/README.md) : anciennes documentations, application RF et artefacts historiques.

## Versions

`main` contient la V1.1 active et la réorganisation du dépôt.
Le tag `v1.1` conserve la livraison originale avant rangement ; la branche
`release/v1.1` reste disponible. La V1.0 est conservée dans l’historique Git
(commit `30332bb`). Le rangement ne modifie pas les calculs ni la commande de lancement.

## Distribution Windows sans Python

Voir le [guide de fabrication dans VS Code](packaging/README.md).
Le paquet doit être construit et validé sur Windows avant distribution.
