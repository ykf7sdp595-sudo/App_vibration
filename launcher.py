"""Lanceur local, utilisable avec Python ou dans un paquet PyInstaller."""
from pathlib import Path
import argparse
import signal
import socket
import sys
import threading
import time
import urllib.request
import webbrowser


def stop_when_tabs_closed(grace_seconds=15):
    """Arrêter le serveur lorsque le dernier onglet reste fermé."""
    from streamlit.runtime.runtime import Runtime, RuntimeState

    connected_once = False
    disconnected_at = None
    while True:
        if Runtime.exists():
            state = Runtime.instance().state
            if state in (RuntimeState.STOPPING, RuntimeState.STOPPED):
                return
            if state == RuntimeState.ONE_OR_MORE_SESSIONS_CONNECTED:
                connected_once = True
                disconnected_at = None
            elif connected_once and state == RuntimeState.NO_SESSIONS_CONNECTED:
                now = time.monotonic()
                if disconnected_at is None:
                    disconnected_at = now
                elif now - disconnected_at >= grace_seconds:
                    print('Dernier onglet fermé : arrêt de l’application.', flush=True)
                    signal.raise_signal(signal.SIGINT)
                    return
        time.sleep(1)


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
    print('App_vibration V1.3 — laissez cette fenêtre ouverte pendant utilisation.', flush=True)
    print('Fermeture automatique après le dernier onglet ; Ctrl+C reste possible.', flush=True)
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
    threading.Thread(target=stop_when_tabs_closed, daemon=True).start()
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
