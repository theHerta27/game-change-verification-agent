from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from agent_service.agents.dual_agent import run_dual_agent
from agent_service.agents.single_agent import run_single_agent
from agent_service.schemas import ReviewRequest


class AgentServiceHandler(BaseHTTPRequestHandler):
    server_version = "DevQualityAgentHTTP/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._write_json(200, {"status": "ok"})
            return
        self._write_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path not in {"/agent/review", "/agent/mock-review"}:
            self._write_json(404, {"error": "not found"})
            return

        try:
            payload = self._read_json()
            workflow = payload.pop("workflow", "single_agent")
            payload["workflow"] = workflow
            request = ReviewRequest(**payload)
            if workflow == "dual_agent":
                response = run_dual_agent(request)
            else:
                response = run_single_agent(request)
            self._write_json(200, response.model_dump())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._write_json(400, {"error": f"invalid json: {exc}"})
        except ValidationError as exc:
            details = [
                {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
                for item in exc.errors()
            ]
            self._write_json(422, {"error": "validation error", "details": details})
        except Exception as exc:  # noqa: BLE001 - boundary handler must serialize errors
            self._write_json(500, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw)

    def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def load_environment(env_path: str | Path | None = None) -> None:
    load_dotenv(dotenv_path=env_path, override=False)


def run_server(host: str = "127.0.0.1", port: int = 8010) -> None:
    server = ThreadingHTTPServer((host, port), AgentServiceHandler)
    print(f"agent service listening on http://{host}:{port}", flush=True)
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    load_environment()
    parser = argparse.ArgumentParser(prog="devquality-agent-service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args(argv)
    run_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
