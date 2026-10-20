"""Check the distributed Windows ZIP using its own runtime and isolated data."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['version']
package = ROOT / '电脑运行包' / f'french-conjugation-trainer-{version}-windows-x64.zip'
workspace = ROOT / '.desktop-build' / 'smoke-tests'
workspace.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='desktop-', dir=workspace) as temporary:
    folder = Path(temporary).resolve()
    assert folder.is_relative_to(workspace.resolve())
    with ZipFile(package) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert all(name.startswith('Conjugaison-Windows/') and '..' not in Path(name).parts for name in names)
        assert not any('/data/' in name or '/site-packages/' in name or 'node_modules/' in name for name in names)
        archive.extractall(folder)
    app = folder / 'Conjugaison-Windows'
    runtime = app / 'runtime' / 'python.exe'
    environment = {**os.environ, 'CONJUGAISON_DATA_DIR': str(folder / 'isolated-data'), 'NO_PROXY': '127.0.0.1,localhost'}
    probe = subprocess.run([str(runtime), '-c', 'import sys, csv, json, ssl, http.server; print(sys.version.split()[0])'], cwd=app, env=environment, capture_output=True, text=True, check=True)
    print('Bundled Python:', probe.stdout.strip())
    launcher = (app / '启动法语变位器.bat').read_bytes()
    assert b'runtime\\python.exe' in launcher and b'\r\n' in launcher
    log_path = folder / 'server.log'
    def api(path, body=None):
        payload = None if body is None else json.dumps(body).encode('utf-8')
        request = Request('http://127.0.0.1:18768/api/' + path, data=payload, headers={'Content-Type': 'application/json', 'X-Conjugaison-Client': '3.0'})
        with urlopen(request, timeout=3) as response:
            return json.load(response)
    def launch(log):
        process = subprocess.Popen([str(runtime), 'server.py', '--port', '18768'], cwd=app, env=environment, stdout=log, stderr=log)
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError(log_path.read_text(encoding='utf-8', errors='replace'))
            try:
                api('state')
                return process
            except (URLError, OSError):
                time.sleep(.1)
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError('Desktop server did not start.')
    with log_path.open('w', encoding='utf-8') as log:
        process = launch(log)
        try:
            with urlopen('http://127.0.0.1:18768/', timeout=3) as response:
                assert '<title>法语变位器</title>' in response.read().decode('utf-8')
            assert len(api('state')['wordlists']) == 9
            forms = api('dictionary')['être']['必会']['现在时']
            api('favorites/toggle', {'verb': 'être', 'tense': '现在时', 'saved': True})
            question = api('session/start', {'verb': 'être', 'tense': '现在时'})
            count = 0
            while not question.get('completed'):
                answer = question['personne'] if question['round'] == 'reverse' else forms[question['personne']]
                result = api('session/answer', {'id': question['id'], 'answer': answer})
                assert result['correct']
                question = result['next']
                count += 1
                assert count <= 18
            assert count == 18
            assert api('state')['favorites'][0]['practice_count'] == 1
            assert len(api('state')['mastered']) == 6
            assert not any(m.get('known') for m in api('state')['mastered'])
            api('notebooks/move', {'keys': ['être|现在时'], 'target': 'known'})
            assert all(m['known'] for m in api('state')['mastered'])
        finally:
            process.terminate()
            process.wait(timeout=5)
        process = launch(log)
        try:
            state = api('state')
            assert state['favorites'][0]['practice_count'] == 1
            assert len(state['mastered']) == 6
            assert all(m['known'] for m in state['mastered'])
        finally:
            process.terminate()
            process.wait(timeout=5)
    print('Windows ZIP verified: bundled runtime, page title, 9 wordlists, 18 answers, favorites, notebooks and restart persistence.')
