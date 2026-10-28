"""Lanceur local, utilisable avec Python ou dans un paquet PyInstaller."""
from pathlib import Path
import argparse
import socket
import sys
import threading
import time
import urllib.request
import webbrowser


def application_path():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return root / 'App_vibration.py'


def available_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def open_when_ready(url):
    # Les requêtes locales ne doivent pas passer par le proxy d'entreprise.
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(120):
        try:
            with client.open(url + '/_stcore/health', timeout=1) as response:
                if response.status == 200 and response.read().strip() == b'ok':
                    if not webbrowser.open(url):
                        print('Ouverture automatique impossible. Copiez cette adresse dans votre navigateur :', url)
                    return
        except OSError:
            pass
        time.sleep(.5)
    print('Le serveur tarde à démarrer. Consultez les messages dans cette fenêtre.')


def main():
    parser = argparse.ArgumentParser(description='App_vibration — application locale')
    parser.add_argument('--no-browser', action='store_true', help='Ne pas ouvrir le navigateur automatiquement')
    parser.add_argument('--port', type=int, help='Port local facultatif (sinon choisi automatiquement)')
    args = parser.parse_args()
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error('Le port doit être compris entre 1 et 65535.')
    script = application_path()
    if not script.is_file():
        raise FileNotFoundError(f'Application introuvable : {script}. Conservez tout le dossier distribué.')
    port = args.port or available_port()
    url = f'http://127.0.0.1:{port}'
    print('App_vibration V1.1 — laissez cette fenêtre ouverte pendant utilisation.', flush=True)
    print('Pour arrêter : Ctrl+C dans cette fenêtre, puis fermez l’onglet du navigateur.', flush=True)
    print('Adresse locale :', url, flush=True)
    from streamlit.web import bootstrap
    options = {
        'server.address': '127.0.0.1',
        'server.port': port,
        'server.headless': True,
        'server.fileWatcherType': 'none',
        'browser.gatherUsageStats': False,
        'global.developmentMode': False,
    }
    bootstrap.load_config_options(options)
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    bootstrap.run(str(script), False, [], options)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        if getattr(sys, 'frozen', False):
            input('Échec du démarrage. Appuyez sur Entrée pour fermer cette fenêtre…')
        sys.exit(1)
