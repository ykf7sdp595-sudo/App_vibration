# App_vibration — V1.3

Application locale Streamlit de lecture de CSV et d’analyse vibratoire.
Les dépendances directes sont dans `requirements.txt`. Les tests et la fabrication
locale de cette V1.3 ont été exécutés sous Windows avec Python 3.15.

## Installation et lancement sous Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python launcher.py
```

Sous Linux/macOS, utiliser `python3.12 -m venv .venv`, puis
`.venv/bin/python` à la place de `.\.venv\Scripts\python`.
Le navigateur affiche l'application locale ; aucun compte ni service distant requis.
Sous Windows, `lancer.bat` lance aussi l'application après installation des dépendances.
La fermeture du dernier onglet arrête l'application après 15 secondes ; les réglages
de session ne sont pas enregistrés.

## Utilisation

Importer un ou plusieurs CSV dans le volet latéral (Ctrl ou Maj dans le sélecteur,
ou glisser-déposer plusieurs fichiers). Chaque fichier dispose d’un onglet numéroté
avec ses propres réglages, filtres et exports. Les essais ne sont pas concaténés.
Un fichier vide ou illisible affiche un diagnostic sans bloquer les autres.
Dans chaque onglet, choisir une analyse : SWEEPS, VIBRATIONS, CHOCS,
PSD ou Courbe libre. L’analyse sélectionnée de chaque fichier s’exécute, y compris
dans les onglets masqués ; importer de gros lots peut donc augmenter le temps de calcul.
Chaque graphique précède ses propres réglages ; les légendes sont placées en dessous.
Les informations d'import sont regroupées sous le sélecteur de fichiers. Les messages
scientifiques liés à une analyse restent près des résultats concernés.
La lecture, conversion numérique et construction du registre sont mises en cache
(au maximum seize fichiers). Les calculs utilisent les données complètes.
Les filtres se trouvent dans « Filtres du fichier » dans chaque onglet et concernent
le tracé libre et l’export, pas les analyses spécialisées.
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
- [`grenier/`](grenier/README.md) : anciennes documentations et artefacts historiques.
- `launcher.py`, `App_vibration.spec`, `packaging/` : lancement et fabrication Windows.

## Versions

`main` contient la V1.3. La branche [v1.2](https://github.com/ykf7sdp595-sudo/App_vibration/tree/v1.2)
conserve l'état précédent ; les branches et tags historiques restent disponibles.
La V1.0 est conservée dans l’historique Git (commit `30332bb`). Les données de mesure,
captures et exécutables ne sont pas ajoutés au dépôt.

## Distribution Windows sans Python

Voir le [guide de fabrication dans VS Code](packaging/README.md). Une construction
en dossier a été vérifiée localement sous Windows ; la distribution sur un autre
poste et les analyses avec les fichiers d'essais réels restent à valider.
