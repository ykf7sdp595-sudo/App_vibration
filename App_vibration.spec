# Paquet dossier Windows ; exécuter depuis la racine du dépôt.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH)
datas, binaries, hiddenimports = collect_all('streamlit')
# Plotly charge dynamiquement ses validateurs et ses ressources.
plotly_data, plotly_bins, plotly_imports = collect_all('plotly')
datas += plotly_data
binaries += plotly_bins
hiddenimports += plotly_imports
for package in ('streamlit', 'pandas', 'numpy', 'scipy', 'plotly'):
    datas += copy_metadata(package)
# Streamlit exécute le script source. Ses imports doivent également être analysés.
modules = ['csv_reader', 'column_registry', 'science', 'selection', 'sweeps',
           'vibrations', 'specialized_tabs', 'plotting']
datas += [(str(root / 'App_vibration.py'), '.')]
hiddenimports += modules + ['pandas', 'numpy', 'scipy.signal', 'plotly.express',
                            'plotly.graph_objects', 'streamlit.web.bootstrap']
a = Analysis([str(root / 'launcher.py')], pathex=[str(root)],
             binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['skrf'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='App_vibration',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='App_vibration')
