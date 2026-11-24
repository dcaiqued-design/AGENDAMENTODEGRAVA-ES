"""Ingest Control: API local, SQLite e agente FFmpeg para piloto Windows.

ATENÇÃO: serviço de uso local (127.0.0.1), sem autenticação remota.
Não exponha a porta à rede nem a publique na internet.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("INGEST_DATA_DIR", str(Path.home() / "IngestControl"))).expanduser().resolve()
MEDIA_DIR = DATA_DIR / "gravacoes"
LOG_DIR = DATA_DIR / "logs"
DB_FILE = DATA_DIR / "ingest.sqlite3"
FFMPEG = os.environ.get("INGEST_FFMPEG", "ffmpeg")
PORT = int(os.environ.get("INGEST_PORT", "8765"))
MAX_SIMULTANEOUS = 4


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().isoformat(timespec="seconds")


def parse_date(value):
    if not isinstance(value, str):
        raise ValueError("Data inválida; envie horário ISO 8601 com fuso.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Formato de data inválido.") from exc
    if result.tzinfo is None:
        raise ValueError("Informe o fuso horário no agendamento.")
    return result.astimezone(timezone.utc)


def safe_name(value):
    value = unicodedata.normalize("NFKD", str(value or "gravacao"))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    return (re.sub(r"[^a-z0-9_-]+", "-", value).strip("-") or "gravacao")[:60]


def ffmpeg_available():
    return bool(shutil.which(FFMPEG) or (Path(FFMPEG).is_file()))


@contextmanager
def connection():
    db = sqlite3.connect(str(DB_FILE), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


class Engine:
    def __init__(self, spawn=subprocess.Popen):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.active = {}
        self.spawn = spawn
        with connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sources (
                  id TEXT PRIMARY KEY, name TEXT NOT NULL, protocol TEXT NOT NULL,
                  url TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id),
                  program TEXT NOT NULL, begins_at TEXT NOT NULL, ends_at TEXT NOT NULL,
                  pre_seconds INTEGER NOT NULL DEFAULT 0,
                  post_seconds INTEGER NOT NULL DEFAULT 0,
                  status TEXT NOT NULL DEFAULT 'scheduled',
                  recording_id TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS recordings (
                  id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id),
                  job_id TEXT, title TEXT NOT NULL, file_path TEXT NOT NULL,
                  status TEXT NOT NULL, started_at TEXT NOT NULL,
                  ended_at TEXT, error TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, begins_at);
                CREATE INDEX IF NOT EXISTS idx_recordings_source ON recordings(source_id, started_at);
            """)
            # O processo não pode ser recuperado automaticamente depois de reiniciar o agente.
            db.execute("UPDATE recordings SET status='interrupted', ended_at=?, error='Agente reiniciado durante a gravação.' WHERE status='recording'", (stamp(),))
            db.execute("UPDATE jobs SET status='interrupted' WHERE status='running'")

    def sources(self):
        with connection() as db:
            rows = db.execute("SELECT id,name,protocol,created_at FROM sources ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]

    def add_source(self, data):
        name = str(data.get("name", "")).strip()[:100]
        url = str(data.get("url", "")).strip()
        protocol = str(data.get("protocol", "")).lower()
        if not name:
            raise ValueError("Informe um nome para o sinal.")
        if protocol not in ("rtmp", "rtmps", "srt"):
            raise ValueError("Nesta versão, somente RTMP/RTMPS e SRT.")
        if len(url) > 2048 or any(ch in url for ch in "\r\n\x00"):
            raise ValueError("Endereço de sinal inválido.")
        parts = urlsplit(url)
        if parts.scheme.lower() != protocol or not parts.netloc:
            raise ValueError("O endereço deve corresponder ao protocolo selecionado.")
        source_id = uuid.uuid4().hex
        with self.lock, connection() as db:
            db.execute("INSERT INTO sources VALUES (?,?,?,?,?)", (source_id,name,protocol,url,stamp()))
        return {"id":source_id,"name":name,"protocol":protocol}

    def jobs(self):
        with connection() as db:
            rows = db.execute("""
                SELECT j.*,s.name AS source_name FROM jobs j
                JOIN sources s ON s.id=j.source_id ORDER BY j.begins_at DESC LIMIT 250
            """).fetchall()
            return [dict(row) for row in rows]

    def add_job(self, data):
        source_id = str(data.get("source_id", ""))
        program = str(data.get("program", "")).strip()[:100]
        begin = parse_date(data.get("begins_at"))
        end = parse_date(data.get("ends_at"))
        try:
            pre = int(data.get("pre_seconds", 0))
            post = int(data.get("post_seconds", 0))
        except (ValueError, TypeError) as exc:
            raise ValueError("Margens devem ser segundos inteiros.") from exc
        if not program:
            raise ValueError("Informe o programa.")
        if begin <= now() + timedelta(seconds=2) or end <= begin:
            raise ValueError("Informe início futuro e término posterior ao início.")
        if end - begin > timedelta(hours=24) or not (0 <= pre <= 1800 and 0 <= post <= 1800):
            raise ValueError("Limite de 24h e margens de até 30 minutos.")
        job_id = uuid.uuid4().hex
        begin_iso = begin.isoformat()
        end_iso = end.isoformat()
        with self.lock, connection() as db:
            source = db.execute("SELECT id FROM sources WHERE id=?", (source_id,)).fetchone()
            if not source:
                raise ValueError("Fonte de sinal não encontrada.")
            rows = db.execute("""
                SELECT begins_at, ends_at, pre_seconds, post_seconds
                FROM jobs WHERE source_id=? AND status IN ('scheduled','running')
            """, (source_id,)).fetchall()
            for other in rows:
                a = parse_date(other["begins_at"]) - timedelta(seconds=other["pre_seconds"])
                b = parse_date(other["ends_at"]) + timedelta(seconds=other["post_seconds"])
                if begin - timedelta(seconds=pre) < b and end + timedelta(seconds=post) > a:
                    raise ValueError("Já existe uma gravação programada nesse intervalo para o sinal.")
            db.execute("""
                INSERT INTO jobs(id,source_id,program,begins_at,ends_at,pre_seconds,post_seconds,status,created_at)
                VALUES (?,?,?,?,?,?,?,'scheduled',?)
            """, (job_id,source_id,program,begin_iso,end_iso,pre,post,stamp()))
        return {"id":job_id,"status":"scheduled"}

    def cancel_job(self, job_id):
        with self.lock, connection() as db:
            changed = db.execute("UPDATE jobs SET status='canceled' WHERE id=? AND status='scheduled'", (job_id,)).rowcount
            if not changed:
                raise ValueError("Somente agendamentos pendentes podem ser cancelados.")
        return {"id":job_id,"status":"canceled"}

    def recordings(self):
        with connection() as db:
            rows = db.execute("""
                SELECT r.*,s.name AS source_name FROM recordings r
                JOIN sources s ON s.id=r.source_id ORDER BY r.started_at DESC LIMIT 250
            """).fetchall()
            return [dict(row) for row in rows]

    def _start_locked(self, source_id, title, job_id=None):
        if not ffmpeg_available():
            raise RuntimeError("FFmpeg não localizado. Configure INGEST_FFMPEG ou PATH.")
        if len(self.active) >= MAX_SIMULTANEOUS:
            raise RuntimeError("Limite de quatro gravações simultâneas atingido.")
        with connection() as db:
            source = db.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
            if not source:
                raise ValueError("Fonte não cadastrada.")
            if any(session["source_id"] == source_id for session in self.active.values()):
                raise ValueError("Essa fonte já está em gravação.")
        rid = uuid.uuid4().hex
        file_name = now().strftime("%Y%m%d_%H%M%S") + "_" + safe_name(title) + "_" + rid[:8] + ".mp4"
        destination = MEDIA_DIR / file_name
        log_file = LOG_DIR / (rid + ".log")
        # Captura MP4: vídeo precisa ser compatível com o container, geralmente H.264.
        # A camada de áudio é convertida para AAC. Não há shell nem interpolação de comandos.
        cmd = [
            FFMPEG, "-hide_banner", "-loglevel", "warning", "-y",
            "-i", source["url"], "-map", "0:v:0", "-map", "0:a:0?",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+frag_keyframe+empty_moov",
            "-f", "mp4", str(destination)
        ]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        log = open(log_file, "ab")
        try:
            proc = self.spawn(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                              stderr=log, cwd=str(MEDIA_DIR), creationflags=flags)
        except Exception:
            log.close()
            raise
        log.close()
        self.active[rid] = {"process":proc,"source_id":source_id,"job_id":job_id}
        with connection() as db:
            db.execute("""
                INSERT INTO recordings(id,source_id,job_id,title,file_path,status,started_at)
                VALUES (?,?,?,?,?,'recording',?)
            """, (rid,source_id,job_id,title,str(destination),stamp()))
            if job_id:
                db.execute("UPDATE jobs SET status='running',recording_id=? WHERE id=?", (rid,job_id))
        return {"id":rid,"status":"recording","file_path":str(destination)}

    def start(self, source_id, title=None):
        with self.lock:
            return self._start_locked(str(source_id), str(title or "Gravacao manual")[:100])

    def _finish_locked(self, rid, status, error=None):
        session = self.active.pop(rid, None)
        with connection() as db:
            rec = db.execute("SELECT job_id,file_path FROM recordings WHERE id=?", (rid,)).fetchone()
            if not rec:
                return
            path = Path(rec["file_path"])
            if status == "completed" and (not path.is_file() or path.stat().st_size < 1024):
                status, error = "failed", "Arquivo de saída ausente ou muito pequeno."
            db.execute("UPDATE recordings SET status=?, ended_at=?, error=? WHERE id=?",
                       (status,stamp(),error,rid))
            if rec["job_id"]:
                job_status = "completed" if status == "completed" else ("interrupted" if status == "interrupted" else "failed")
                db.execute("UPDATE jobs SET status=? WHERE id=? AND status='running'",
                           (job_status,rec["job_id"]))

    def _stop_locked(self, rid, scheduled=False):
        session = self.active.get(rid)
        if not session:
            raise ValueError("Gravação não está ativa neste agente.")
        proc = session["process"]
        if proc.poll() is None:
            try:
                proc.stdin.write(b"q\n")
                proc.stdin.flush()
                proc.wait(timeout=12)
            except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
            finally:
                if proc.stdin:
                    proc.stdin.close()
        status = "completed" if proc.returncode == 0 else "failed"
        self._finish_locked(rid,status,None if status == "completed" else "FFmpeg retornou código " + str(proc.returncode))
        return {"id":rid,"status":status}

    def stop(self, rid):
        with self.lock:
            return self._stop_locked(str(rid))

    def tick(self):
        with self.lock:
            # Reconhece FFmpeg encerrado sem comando de parada.
            for rid, session in list(self.active.items()):
                code = session["process"].poll()
                if code is not None:
                    self._finish_locked(rid,"failed","FFmpeg terminou inesperadamente (código " + str(code) + ").")
            current = now()
            with connection() as db:
                ongoing = db.execute("""
                    SELECT id,recording_id,ends_at,post_seconds FROM jobs WHERE status='running'
                """).fetchall()
            for job in ongoing:
                if current >= parse_date(job["ends_at"]) + timedelta(seconds=job["post_seconds"]):
                    if job["recording_id"] in self.active:
                        self._stop_locked(job["recording_id"],scheduled=True)
            with connection() as db:
                waiting = db.execute("""
                    SELECT * FROM jobs WHERE status='scheduled' ORDER BY begins_at ASC
                """).fetchall()
            for job in waiting:
                begins = parse_date(job["begins_at"]) - timedelta(seconds=job["pre_seconds"])
                ends = parse_date(job["ends_at"]) + timedelta(seconds=job["post_seconds"])
                if current < begins:
                    continue
                if current >= ends:
                    with connection() as db:
                        db.execute("UPDATE jobs SET status='missed' WHERE id=? AND status='scheduled'", (job["id"],))
                    continue
                try:
                    self._start_locked(job["source_id"],job["program"],job["id"])
                except (ValueError,RuntimeError,OSError) as exc:
                    # Evita repetição infinita e registra a falha no job.
                    with connection() as db:
                        db.execute("UPDATE jobs SET status='failed' WHERE id=?", (job["id"],))
                    print("Agendamento falhou:",job["id"],type(exc).__name__)

    def loop(self):
        while True:
            try:
                self.tick()
            except Exception as exc:
                print("Erro na automação:",type(exc).__name__)
            time.sleep(2)

    def health(self):
        try:
            free = shutil.disk_usage(MEDIA_DIR).free
        except OSError:
            free = None
        return {"service":"online","ffmpeg":ffmpeg_available(),
                "active":len(self.active),"max_simultaneous":MAX_SIMULTANEOUS,
                "disk_free_bytes":free,"data_folder":str(DATA_DIR)}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE), **kwargs)

    def log_message(self, format, *args):
        # Não imprimir URLs de fontes RTMP/SRT nem cabeçalhos privados.
        pass

    def _json(self, code, payload):
        body = json.dumps(payload,ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _local_request(self):
        host = self.headers.get("Host","")
        allowed = ("127.0.0.1:"+str(PORT),"localhost:"+str(PORT))
        return host in allowed

    def do_GET(self):
        if not self._local_request():
            return self._json(403,{"error":"Acesso somente pelo computador local."})
        path = self.path.split("?",1)[0]
        if path.startswith("/api/"):
            try:
                if path == "/api/health":
                    return self._json(200,engine.health())
                if path == "/api/sources":
                    return self._json(200,engine.sources())
                if path == "/api/jobs":
                    return self._json(200,engine.jobs())
                if path == "/api/recordings":
                    return self._json(200,engine.recordings())
                return self._json(404,{"error":"API não encontrada."})
            except Exception:
                return self._json(500,{"error":"Falha interna da API."})
        if path == "/":
            self.path = "/index.html"
        elif path not in ("/index.html","/operacao-real.html","/assets/styles.css","/assets/app.js","/assets/real.js"):
            return self.send_error(404)
        return super().do_GET()

    def do_POST(self):
        if not self._local_request():
            return self._json(403,{"error":"Acesso somente pelo computador local."})
        origin = self.headers.get("Origin")
        if origin and origin not in ("http://127.0.0.1:"+str(PORT),"http://localhost:"+str(PORT)):
            return self._json(403,{"error":"Origem não autorizada."})
        if self.headers.get("Content-Type","").split(";",1)[0].strip().lower() != "application/json":
            return self._json(415,{"error":"Envie application/json."})
        try:
            size = int(self.headers.get("Content-Length","0"))
            if not 0 <= size <= 32768:
                raise ValueError("Tamanho de requisição inválido.")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data,dict):
                raise ValueError("Corpo deve ser um objeto JSON.")
            path = self.path.split("?",1)[0]
            if path == "/api/sources":
                return self._json(201,engine.add_source(data))
            if path == "/api/jobs":
                return self._json(201,engine.add_job(data))
            if path == "/api/recordings/start":
                return self._json(201,engine.start(data.get("source_id"),data.get("title")))
            m = re.fullmatch(r"/api/recordings/([a-f0-9]{32})/stop",path)
            if m:
                return self._json(200,engine.stop(m.group(1)))
            m = re.fullmatch(r"/api/jobs/([a-f0-9]{32})/cancel",path)
            if m:
                return self._json(200,engine.cancel_job(m.group(1)))
            return self._json(404,{"error":"Rota desconhecida."})
        except (ValueError,TypeError) as exc:
            return self._json(400,{"error":str(exc)})
        except RuntimeError as exc:
            return self._json(409,{"error":str(exc)})
        except Exception:
            return self._json(500,{"error":"Falha interna da gravação."})


if __name__ == "__main__":
    engine = Engine()
    threading.Thread(target=engine.loop,daemon=True,name="ingest-scheduler").start()
    print("Ingest Control — serviço local de gravação (piloto)")
    print("Painel: http://127.0.0.1:"+str(PORT)+"/operacao-real.html")
    print("Pasta de arquivos:",MEDIA_DIR)
    print("FFmpeg:", "localizado" if ffmpeg_available() else "NÃO localizado")
    print("IMPORTANTE: não exponha esta porta à rede. Use somente sinais autorizados.")
    server = ThreadingHTTPServer(("127.0.0.1",PORT),Handler)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("Encerrando. Aguarde finalização das gravações.")
    finally:
        with engine.lock:
            for rid in list(engine.active):
                engine._stop_locked(rid)
        server.server_close()
