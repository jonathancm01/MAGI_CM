"""Launch MAGI without a console and stop after its last browser tab closes."""

import ctypes
import hashlib
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import sys
from threading import Event, RLock, Thread
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

from flask import Response, abort, request
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8050"
PROJECT = hashlib.sha256(str(ROOT).casefold().encode()).hexdigest()[:16]


class BrowserLifetime:
    def __init__(self, grace=8, startup_timeout=45, clock=time.monotonic):
        self.clock, self.grace, self.startup_timeout = clock, grace, startup_timeout
        self.instance, self.closed, self.lock = secrets.token_hex(24), Event(), RLock()
        self.clients, self.opened, self.empty_since = set(), False, clock()

    def connect(self):
        with self.lock:
            if self.closed.is_set():
                raise RuntimeError("MAGI se está cerrando.")
            client = secrets.token_hex(16)
            self.clients.add(client)
            self.opened = True
            return client

    def disconnect(self, client):
        with self.lock:
            if client in self.clients:
                self.clients.remove(client)
                if not self.clients:
                    self.empty_since = self.clock()

    def expired(self):
        with self.lock:
            timeout = self.grace if self.opened else self.startup_timeout
            return not self.clients and self.clock() - self.empty_since >= timeout

    def stream(self):
        client = self.connect()
        try:
            yield "retry: 1000\n: MAGI connected\n\n"
            while not self.closed.wait(1):
                yield ": MAGI alive\n\n"
        finally:
            self.disconnect(client)


def install_lifecycle(dash_app, lifetime):
    dash_app.index_string = dash_app.index_string.replace(
        "</head>", f'<meta name="magi-instance" content="{lifetime.instance}"></head>')

    @dash_app.server.before_request
    def magi_closing():
        if lifetime.closed.is_set() and request.path != "/_magi/health":
            abort(503)

    @dash_app.server.get("/_magi/health")
    def magi_health():
        with lifetime.lock:
            return ({"application": "MAGI_CM", "project": PROJECT, "mode": "launcher",
                     "clients": len(lifetime.clients), "closing": lifetime.closed.is_set()},
                    200, {"Cache-Control": "no-store"})

    @dash_app.server.get("/_magi/browser")
    def magi_browser():
        if not secrets.compare_digest(request.args.get("instance", "").encode(), lifetime.instance.encode()):
            abort(403)
        if lifetime.closed.is_set():
            abort(503)
        return Response(lifetime.stream(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


def open_existing():
    try:
        with urlopen(URL + "/_magi/health", timeout=1) as response:
            status = json.loads(response.read(4096))
        if (isinstance(status, dict) and status.get("application") == "MAGI_CM"
                and status.get("project") == PROJECT and status.get("mode") == "launcher"
                and status.get("closing") is False):
            if not webbrowser.open(URL + "/", new=2):
                raise RuntimeError("No se pudo abrir el navegador predeterminado.")
            return True
    except (URLError, OSError, ValueError):
        pass
    return False


def stop_when_closed(server, lifetime):
    while not lifetime.closed.wait(0.25):
        # Recheck under the same lock as connect: a reload must cancel shutdown.
        with lifetime.lock:
            if not lifetime.clients and lifetime.expired():
                lifetime.closed.set()
                break
    server.shutdown()


def run():
    import msvcrt

    (ROOT / ".magi").mkdir(exist_ok=True)
    with (ROOT / ".magi" / "launcher.lock").open("a+b") as lock_file:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"0")
            lock_file.flush()
        lock_file.seek(0)
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            for _ in range(20):
                if open_existing():
                    return
                time.sleep(0.25)
            raise RuntimeError("MAGI se está iniciando o cerrando. Vuelve a abrirlo en unos segundos.")

        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", 8050)) == 0:
                if open_existing():
                    return
                raise RuntimeError("El puerto 8050 está ocupado. Cierra la instancia manual de MAGI antes de usar el acceso directo.")

        import main

        lifetime = BrowserLifetime()
        install_lifecycle(main.app, lifetime)
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        try:
            server = make_server("127.0.0.1", 8050, main.app.server, threaded=True)
        except SystemExit as error:
            raise RuntimeError("No se pudo reservar el puerto 8050. Comprueba si otro programa lo está usando.") from error
        watcher = Thread(target=stop_when_closed, args=(server, lifetime), daemon=True)
        try:
            if not webbrowser.open(URL + "/", new=2):
                raise RuntimeError("No se pudo abrir el navegador predeterminado.")
            watcher.start()
            server.serve_forever()
        finally:
            lifetime.closed.set()
            server.server_close()
            main.controller.cancel()
            deadline = time.monotonic() + 15
            while main.controller.busy() and time.monotonic() < deadline:
                time.sleep(0.05)
            main.controller.persist()


def main():
    (ROOT / ".cache").mkdir(exist_ok=True)
    with (ROOT / ".cache" / "launcher.log").open("a", encoding="utf-8", buffering=1) as log:
        original_stdout, original_stderr = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = log
        try:
            run()
        except Exception as error:
            logging.exception("No se pudo iniciar MAGI")
            ctypes.windll.user32.MessageBoxW(0, f"{error}\n\nDetalles: {ROOT / '.cache' / 'launcher.log'}", "MAGI", 0x10)
        finally:
            sys.stdout, sys.stderr = original_stdout, original_stderr


if __name__ == "__main__":
    main()
