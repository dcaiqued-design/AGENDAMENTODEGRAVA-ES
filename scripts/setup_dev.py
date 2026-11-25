"""Verifica e testa o ambiente de desenvolvimento sem instalar pacotes globais."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-capture', action='store_true', help='Exige FFmpeg com RTMP, RTMPS e SRT')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        print('ERRO: Python 3.10 ou superior é necessário.')
        return 1
    print('Python:', sys.version.split()[0])
    missing = [p for p in ('index.html','assets/styles.css','assets/app.js','assets/integration.js','backend/ingest_server.py') if not (ROOT / p).is_file()]
    if missing:
        print('ERRO: checkout incompleto:', ', '.join(missing))
        return 1
    node = shutil.which('node')
    if not node:
        print('ERRO: Node.js é necessário para verificar o JavaScript no desenvolvimento.')
        return 1
    for asset in ('app.js','integration.js','real.js'):
        subprocess.run([node,'--check',str(ROOT/'assets'/asset)],check=True)
    ffmpeg = os.environ.get('INGEST_FFMPEG','ffmpeg')
    executable = shutil.which(ffmpeg)
    if not executable and Path(ffmpeg).is_file():
        executable = ffmpeg
    protocols = set()
    if executable:
        result = subprocess.run([executable,'-hide_banner','-protocols'],capture_output=True,text=True,check=True)
        protocols = set(result.stdout.split())
    missing_protocols = {'rtmp','rtmps','srt'} - protocols
    if missing_protocols:
        print('Captura incompleta: FFmpeg ausente ou sem protocolos:', ', '.join(sorted(missing_protocols)))
        if args.require_capture:
            return 1
    else:
        print('FFmpeg: RTMP, RTMPS e SRT disponíveis. Captura efetiva ainda requer teste de mídia.')
    with tempfile.TemporaryDirectory(prefix='ingest-dev-tests-') as folder:
        env = os.environ.copy()
        env['INGEST_DATA_DIR'] = folder
        subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,env=env,check=True)
    print('Ambiente de desenvolvimento verificado. Nenhum banco de operação foi utilizado.')
    print('Iniciar: python scripts/start_dev.py')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.SubprocessError) as exc:
        print('Falha na preparação:', type(exc).__name__)
        sys.exit(1)
