"""Contrôle de l'exécutable dans Edge avec un CSV synthétique temporaire."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.request import urlopen

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
EDGE = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Microsoft/Edge/Application/msedge.exe'
EXE = ROOT / 'dist/App_vibration/App_vibration.exe'


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    app_port, debug_port = port(), port()
    with tempfile.TemporaryDirectory(prefix='vibration_browser_') as temporary:
        temp = Path(temporary)
        csv = temp / 'synthetic.csv'
        csv.write_text('Time (s),Frequency (Hz),Channel (G)\n0,1,1\n1,2,-2\n2,3,1\n', encoding='utf-8')
        processes = []
        try:
            processes.append(subprocess.Popen([str(EXE), '--no-browser', '--port', str(app_port)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW))
            processes.append(subprocess.Popen([str(EDGE), '--headless=new', '--no-first-run',
                '--remote-debugging-port=' + str(debug_port), '--user-data-dir=' + str(temp / 'profile'),
                'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW))
            deadline = time.monotonic() + 120
            while True:
                try:
                    with urlopen(f'http://127.0.0.1:{debug_port}/json', timeout=1) as response:
                        target = next(p for p in json.load(response) if p['type'] == 'page')
                    with urlopen(f'http://127.0.0.1:{app_port}/_stcore/health', timeout=1):
                        break
                except (OSError, StopIteration):
                    if any(p.poll() is not None for p in processes) or time.monotonic() > deadline:
                        raise RuntimeError('Démarrage du navigateur ou de l’application impossible.')
                    time.sleep(.3)
            with connect(target['webSocketDebuggerUrl'], max_size=20_000_000) as ws:
                serial = 0
                def command(method, params=None):
                    nonlocal serial
                    serial += 1
                    ws.send(json.dumps(dict(id=serial, method=method, params=params or {})))
                    while True:
                        message = json.loads(ws.recv(timeout=30))
                        if message.get('id') == serial:
                            if 'error' in message:
                                raise RuntimeError(message['error'])
                            return message.get('result', {})
                def evaluate(expression):
                    result = command('Runtime.evaluate', dict(expression=expression, returnByValue=True, awaitPromise=True))
                    if 'exceptionDetails' in result:
                        raise RuntimeError(result['exceptionDetails'])
                    return result.get('result', {}).get('value')
                def wait_for(expression):
                    deadline = time.monotonic() + 60
                    while not evaluate(expression):
                        if time.monotonic() > deadline:
                            raise RuntimeError('Condition non satisfaite : ' + expression + '\n' + str(evaluate('document.body.innerText')))
                        time.sleep(.3)
                command('Page.navigate', dict(url=f'http://127.0.0.1:{app_port}'))
                wait_for("!!document.querySelector('input[type=file]')")
                document = command('DOM.getDocument')
                node = command('DOM.querySelector', dict(nodeId=document['root']['nodeId'], selector='input[type=file]'))
                command('DOM.setFileInputFiles', dict(nodeId=node['nodeId'], files=[str(csv)]))
                plot = "document.querySelector('.js-plotly-plot')"
                wait_for(f'{plot}?.data?.length === 1')
                count = evaluate(f'{plot}._fullData[0].x?.length')
                assert count == 3, f'Nombre de points inattendu : {count}'
                assert evaluate(f'{plot}.layout.legend.orientation') == 'h'
                assert not evaluate("!!document.querySelector('[data-testid=stException]')")
                wait_for("!!document.querySelector('.modebar-btn[data-title*=\"camera\"], .modebar-btn[data-title*=\"Download\"], .modebar-btn[data-title*=\"télécharg\"]')")
                print('PASS : EXE Windows, import CSV synthétique, graphique SWEEPS, légende et commande PNG.')
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    process.wait(timeout=15)


if __name__ == '__main__':
    main()
