from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ainative.core.engine import AINativeEngine


class StarterServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], engine: AINativeEngine, web_dir: Path):
        self.engine = engine
        self.web_dir = web_dir
        super().__init__(address, StarterHandler)


class StarterHandler(BaseHTTPRequestHandler):
    server: StarterServer

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json({"status": "ok", "version": "0.1.0"})
            return
        if path == "/api/dashboard":
            self._json(self.server.engine.dashboard())
            return
        self._static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/demo/run":
                self._json(self.server.engine.run_monitoring(), HTTPStatus.CREATED)
                return
            if path.startswith("/api/approvals/") and path.endswith("/decision"):
                approval_id = path.split("/")[3]
                body = self._body()
                task = self.server.engine.decide_approval(
                    approval_id=approval_id,
                    approved=bool(body.get("approved")),
                    decided_by=str(body.get("decided_by") or "经营分析负责人"),
                )
                self._json(task)
                return
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except (KeyError, ValueError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path: str) -> None:
        relative = "index.html" if path in ("/", "") else path.lstrip("/")
        candidate = (self.server.web_dir / relative).resolve()
        web_root = self.server.web_dir.resolve()
        if web_root not in candidate.parents and candidate != web_root:
            self._json({"error": "Invalid path"}, HTTPStatus.BAD_REQUEST)
            return
        if not candidate.is_file():
            candidate = self.server.web_dir / "index.html"
        body = candidate.read_bytes()
        mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[ai-native] {self.address_string()} - {format % args}")


def serve(engine: AINativeEngine, web_dir: str | Path, host: str = "127.0.0.1", port: int = 8000):
    server = StarterServer((host, port), engine=engine, web_dir=Path(web_dir))
    print(f"AI Native Starter running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
    finally:
        server.server_close()

