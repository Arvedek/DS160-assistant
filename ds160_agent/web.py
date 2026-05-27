from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .audit import log_event, read_recent_events
from .core import analyze_application, save_analysis, schema_payload
from .dossier import dossier_schema
from .document_intake import ai_status, analyze_document


STATIC_DIR = Path(__file__).parent / "static"
WORKSPACE_ROOT = Path.cwd().resolve()
OUTPUT_ROOT = WORKSPACE_ROOT / "outputs" / "ds160"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local DS-160 drafting assistant.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), DS160Handler)
    print(f"DS-160 local assistant running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping DS-160 local assistant.")
    return 0


class DS160Handler(BaseHTTPRequestHandler):
    server_version = "DS160LocalAssistant/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send_file(STATIC_DIR / "index.html")
            return
        if parsed.path.startswith("/static/"):
            self._send_file(STATIC_DIR / parsed.path.removeprefix("/static/"))
            return
        if parsed.path == "/api/schema":
            self._send_json(schema_payload())
            return
        if parsed.path == "/api/dossier-schema":
            self._send_json(dossier_schema())
            return
        if parsed.path == "/api/audit":
            self._send_json({"events": read_recent_events(OUTPUT_ROOT)})
            return
        if parsed.path == "/api/ai-status":
            self._send_json(ai_status())
            return
        if parsed.path.startswith("/outputs/ds160/"):
            self._send_output_file(parsed.path.removeprefix("/outputs/ds160/"))
            return
        self._send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            self._handle_analyze(save=False)
            return
        if parsed.path == "/api/save":
            self._handle_analyze(save=True)
            return
        if parsed.path == "/api/document/analyze":
            self._handle_document_analyze()
            return
        self._send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def _handle_analyze(self, save: bool) -> None:
        try:
            payload = self._read_json_body()
            analysis = analyze_application(payload)
            log_event(
                OUTPUT_ROOT,
                "save" if save else "analyze",
                {
                    "caseId": analysis["dossier"]["caseId"],
                    "requiredAnswered": analysis["completeness"]["requiredAnswered"],
                    "requiredTotal": analysis["completeness"]["requiredTotal"],
                    "issueCount": len(analysis["issues"]),
                },
            )
            if save:
                paths = save_analysis(analysis, OUTPUT_ROOT)
                analysis["saved"] = {
                    "jsonUrl": "/" + _workspace_url(paths["jsonPath"]),
                    "markdownUrl": "/" + _workspace_url(paths["markdownPath"]),
                }
            self._send_json(analysis)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001 - local UI should surface unexpected failures
            self._send_json({"error": f"Unexpected server error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_document_analyze(self) -> None:
        try:
            payload = self._read_json_body()
            result = analyze_document(payload)
            log_event(
                OUTPUT_ROOT,
                "document_analyze",
                {
                    "caseId": payload.get("caseId") or "unknown",
                    "mode": result.get("mode"),
                    "candidateCount": len(result.get("candidates", [])),
                    "mimeType": result.get("evidence", {}).get("mimeType"),
                },
            )
            self._send_json(result)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001 - local UI should surface unexpected failures
            self._send_json({"error": f"Unexpected server error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        resolved = path.resolve()
        if not _is_within(resolved, STATIC_DIR.resolve()) or not resolved.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return
        self._send_bytes(resolved)

    def _send_output_file(self, relative_path: str) -> None:
        path = (OUTPUT_ROOT / relative_path).resolve()
        if not _is_within(path, OUTPUT_ROOT.resolve()) or not path.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "Output file not found")
            return
        self._send_bytes(path)

    def _send_bytes(self, path: Path) -> None:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"error": message}, status=status)


def _workspace_url(path: str) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
    except ValueError:
        return resolved.name


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
