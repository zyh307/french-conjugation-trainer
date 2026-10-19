"""Build a Windows portable ZIP with a private Python runtime; no pip dependencies."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['version']
if os.name != 'nt' or struct.calcsize('P') != 8:
    raise SystemExit('Build the Windows x64 package using 64-bit Python on Windows.')
BUILD = ROOT / '.desktop-build' / 'Conjugaison-Windows'
if BUILD.exists():
    if not BUILD.resolve().is_relative_to(ROOT.resolve()) or not BUILD.resolve().is_relative_to((ROOT / '.desktop-build').resolve()):
        raise SystemExit('Unexpected desktop build path.')
    shutil.rmtree(BUILD)
BUILD.mkdir(parents=True)
for name in ['server.py', 'conjugaison_core.py', 'learning_schedule.py', 'LICENSE']:
    shutil.copy2(ROOT / name, BUILD / name)
for name in ['dist', 'wordlists']:
    shutil.copytree(ROOT / name, BUILD / name)

runtime = BUILD / 'runtime'
runtime.mkdir()
python_root = Path(sys.base_prefix)
python_tag = f'python{sys.version_info.major}{sys.version_info.minor}'
for name in ['python.exe', 'python3.dll', python_tag + '.dll', 'LICENSE.txt']:
    shutil.copy2(python_root / name, runtime / name)
for source in python_root.glob('vcruntime*.dll'):
    shutil.copy2(source, runtime / source.name)
shutil.copytree(python_root / 'DLLs', runtime / 'DLLs', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*_test*', '*.pdb', '*.lib', '*.exp'))
excluded = {'site-packages', '__pycache__', 'test', 'tests', 'idlelib', 'turtledemo', 'ensurepip', 'venv', 'tkinter'}
with ZipFile(runtime / (python_tag + '.zip'), 'w', ZIP_DEFLATED, compresslevel=6) as archive:
    for source in sorted((python_root / 'Lib').rglob('*')):
        relative = source.relative_to(python_root / 'Lib')
        if source.is_file() and not excluded.intersection(relative.parts) and source.suffix not in {'.pyc', '.pyo'}:
            archive.write(source, relative.as_posix())
(runtime / (python_tag + '._pth')).write_text(f'{python_tag}.zip\n.\nDLLs\n..\n', encoding='ascii')
(runtime / '运行环境.txt').write_text(f'Python {sys.version.split()[0]} / Windows x64\n仅供法语变位器运行使用。许可证见 LICENSE.txt。\n', encoding='utf-8')
launcher = '''@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
"runtime\\python.exe" "server.py" --open
if errorlevel 1 (
  echo.
  echo The app could not start. Keep this window open to see the error above.
  pause
  exit /b 1
)
endlocal
'''
(BUILD / '启动法语变位器.bat').write_bytes(launcher.replace('\n', '\r\n').encode('ascii'))
(BUILD / '使用说明.txt').write_text(f'''法语变位器 · 电脑版（Windows x64）{VERSION}

1. 完整解压整个文件夹，不要直接在压缩包里运行。
2. 双击“启动法语变位器.bat”，应用会在默认浏览器中打开。
3. 使用期间保持启动窗口打开；结束时关闭窗口即可。

已内置 Python 和编译后的界面，无需安装 Node.js、Python 或项目依赖。
支持 Windows 10/11 64 位，所有练习离线可用。
地址：http://127.0.0.1:8765；同时只运行一个电脑版实例。

学习记录自动保存在同目录下的 data 文件夹。
更新时将原来的 data 文件夹复制到新版目录，可保留学习记录。
电脑版与安卓手机版各自保存记录，目前没有自动同步。
runtime 为内置运行环境，请与程序文件放在一起。
''', encoding='utf-8')
output = ROOT / '电脑运行包'
output.mkdir(exist_ok=True)
zip_path = output / f'french-conjugation-trainer-{VERSION}-windows-x64.zip'
with ZipFile(zip_path, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
    for source in sorted(BUILD.rglob('*')):
        if source.is_file():
            archive.write(source, source.relative_to(BUILD.parent).as_posix())
checksum = hashlib.sha256(zip_path.read_bytes()).hexdigest()
(output / 'SHA256.txt').write_text(f'{checksum}  {zip_path.name}\n', encoding='utf-8')
print(f'Windows package: {zip_path}\nSize: {zip_path.stat().st_size:,} bytes\nSHA-256: {checksum}')
