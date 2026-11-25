"""Inicia o agente em loopback, usando dados de desenvolvimento separados."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10+ é necessário.')
env = os.environ.copy()
env['INGEST_DATA_DIR'] = env.get('INGEST_DEV_DATA_DIR', str(Path.home()/'IngestControl-dev'))
env['INGEST_PORT'] = env.get('INGEST_DEV_PORT','8766')
print('DESENVOLVIMENTO: http://127.0.0.1:'+env['INGEST_PORT']+'/', flush=True)
print('Dados separados da operação:',env['INGEST_DATA_DIR'],flush=True)
print('REC/STOP locais podem executar FFmpeg de verdade. Use somente fontes de teste.',flush=True)
try:
    raise SystemExit(subprocess.call([sys.executable,str(ROOT/'backend'/'ingest_server.py')],cwd=ROOT,env=env))
except KeyboardInterrupt:
    pass
