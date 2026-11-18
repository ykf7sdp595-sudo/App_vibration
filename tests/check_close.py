"""Vérifie la fermeture du dernier client WebSocket puis l'arrêt du serveur."""
import asyncio
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

import websockets

folder = Path(__file__).resolve().parents[1]
target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else folder / 'launcher.py'
command = ([str(target)] if target.suffix == '.exe' else [sys.executable, str(target)]) + ['--no-browser', '--port', '18732']
process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)


async def exercise_connections():
    uri = 'ws://127.0.0.1:18732/_stcore/stream'
    async with websockets.connect(uri, origin='http://127.0.0.1:18732', subprotocols=['streamlit']):
        await asyncio.sleep(2)
        async with websockets.connect(uri, origin='http://127.0.0.1:18732', subprotocols=['streamlit']):
            await asyncio.sleep(2)
        # Un onglet reste connecté : aucune extinction ne doit survenir.
        await asyncio.sleep(17)
        if process.poll() is not None:
            raise RuntimeError('L’application a quitté alors qu’un onglet était encore connecté.')


try:
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f'Lancement impossible : {process.returncode}')
        try:
            with urlopen('http://127.0.0.1:18732/_stcore/health', timeout=1) as response:
                if response.read() == b'ok':
                    break
        except OSError:
            time.sleep(0.5)
    else:
        raise RuntimeError('Délai de démarrage dépassé.')
    asyncio.run(exercise_connections())
    process.wait(timeout=35)
    if process.returncode != 0:
        raise RuntimeError(f'Arrêt anormal : {process.returncode}')
    print('L’application reste ouverte avec un onglet et se ferme après le dernier.')
finally:
    if process.poll() is None:
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
