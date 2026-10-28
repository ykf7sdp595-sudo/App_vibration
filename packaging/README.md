# Fabriquer le paquet Windows depuis VS Code

Cette configuration prépare une distribution en dossier, pas un EXE autonome.
La compilation Windows et le test sur un poste sans Python restent à effectuer.

## Préparation

Utiliser Windows 64 bits et Python 3.12 64 bits sur le PC de fabrication.
Ouvrir la racine du projet dans VS Code puis un terminal PowerShell.
Vérifier `py -3.12 --version`. Internet est requis pour installer les dépendances
sur le poste de fabrication, pas pour les calculs chez les utilisateurs.

## Fabrication

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1
```

Cette option concerne uniquement ce processus PowerShell ; elle ne modifie pas
la politique permanente du poste. Si votre entreprise interdit les scripts,
utiliser les commandes manuelles ci-dessous selon ses règles.
Le script crée `.venv-build`, installe les dépendances, exécute les tests puis
fabrique `dist\App_vibration\App_vibration.exe`. Les dossiers de fabrication
`build` et `dist\App_vibration` peuvent être remplacés lors d'une nouvelle compilation.
Ne pas y conserver de mesures ou de travail personnel.

Alternative manuelle :

```powershell
py -3.12 -m venv .venv-build
.\.venv-build\Scripts\python -m pip install -r requirements-build.txt
.\.venv-build\Scripts\python -m unittest discover -s tests -v
.\.venv-build\Scripts\python -m PyInstaller --clean --noconfirm App_vibration.spec
```

Arrêter si une commande échoue. Quatre tests ignorés faute de CSV de référence
sont attendus. Le script automatique copie aussi les instructions utilisateur
et enregistre les versions installées à côté de l'exécutable.

## Vérification avant distribution

Lancer l'EXE depuis l'Explorateur Windows. Vérifier l'import d'un CSV, les cinq
vues, FFT, PSD, modifications des axes et téléchargement CSV/JSON. Vérifier
l'arrêt par Ctrl+C, puis le redémarrage. Fermer le navigateur n'arrête pas le serveur.
Tester ensuite sur un poste Windows sans Python, avec les CSV de référence
FFT/PSD déjà validés. Aucune compilation Linux ne remplace ce contrôle.
En cas d'erreur, conserver le texte de la console et les avertissements de
`build\App_vibration\warn-App_vibration.txt` pour le diagnostic.

Compresser **tout** le dossier `dist\App_vibration` en ZIP, puis le transmettre.
Ne pas transmettre uniquement l'EXE : `_internal` contient les dépendances.
Aucun installateur, signature ou mécanisme de mise à jour automatique n'est fourni.
