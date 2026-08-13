#!/usr/bin/env python3
"""Valide FaceLens en environnement local simulant la production.

Le script lance l’API Uvicorn sans rechargement automatique, dans un répertoire
isolé et avec des garde-fous de production explicites. Il n’utilise ni clé réelle
ni image biométrique réelle : l’image de test est générée localement.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOST, PORT = "127.0.0.1", 18765
BASE_URL = f"http://{HOST}:{PORT}"
API_KEY = "integration-test-key-with-at-least-thirty-two-characters"
ALLOWED_ORIGIN = "http://localhost:4173"


def call(path, *, expected, method="GET", headers=None, body=None):
    request = Request(f"{BASE_URL}{path}", data=body, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=8) as response:
            status, payload = response.status, response.read()
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as error:
        status, payload = error.code, error.read()
        response_headers = {key.lower(): value for key, value in error.headers.items()}
    except URLError as error:
        raise AssertionError(f"Appel réseau impossible vers {path}: {error}") from error
    if status != expected:
        preview = payload.decode("utf-8", errors="replace")[:400]
        raise AssertionError(f"{method} {path}: statut {status}, attendu {expected}; {preview}")
    return response_headers, payload


def multipart(parts):
    boundary = "----FaceLensIntegrationBoundary"
    chunks = []
    for name, filename, media_type, content in parts:
        chunks += [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {media_type}\r\n\r\n".encode(),
            content,
            b"\r\n",
        ]
    chunks.append(f"--{boundary}--\r\n".encode())
    return f"multipart/form-data; boundary={boundary}", b"".join(chunks)


def png_bytes():
    stream = BytesIO()
    Image.new("RGB", (32, 32), color=(20, 60, 100)).save(stream, format="PNG")
    return stream.getvalue()


def as_json(payload):
    return json.loads(payload.decode("utf-8"))


def wait_until_ready():
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        try:
            _, payload = call("/", expected=200, headers={"X-FaceLens-API-Key": API_KEY})
            if as_json(payload)["status"] == "online":
                return
        except (AssertionError, KeyError, json.JSONDecodeError):
            time.sleep(1)
    raise AssertionError("Le service ne répond pas avec son état de santé après 75 secondes.")


def main():
    runtime_dir = Path(tempfile.mkdtemp(prefix="facelens-production-sim-"))
    log_path = runtime_dir / "uvicorn.log"
    environment = os.environ | {
        "PYTHONPATH": str(PROJECT_ROOT),
        "FACELENS_API_KEY": API_KEY,
        "CORS_ORIGINS": ALLOWED_ORIGIN,
        "MAX_IMAGE_UPLOAD_BYTES": "1048576",
        "MAX_IMAGE_PIXELS": "2000000",
        "MAX_REMOTE_IMAGE_BYTES": "1048576",
        "STRICT_REMOTE_URL_VALIDATION": "true",
        "INSIGHTFACE_CTX_ID": "-1",
    }
    checks, process = [], None

    try:
        with log_path.open("wb") as logs:
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", HOST,
                 "--port", str(PORT), "--log-level", "warning"],
                cwd=runtime_dir, env=environment, stdout=logs, stderr=subprocess.STDOUT,
            )
            wait_until_ready()
        checks.append("démarrage Uvicorn isolé avec paramètres de production")

        call("/", expected=401)
        call("/", expected=401, headers={"X-FaceLens-API-Key": "wrong-key"})
        _, health = call("/", expected=200, headers={"X-FaceLens-API-Key": API_KEY})
        assert as_json(health)["app"] == "FaceLens"
        checks.append("clé API obligatoire et endpoint de santé authentifié")

        allowed, _ = call(
            "/", expected=200, method="OPTIONS",
            headers={"Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "GET",
                     "Access-Control-Request-Headers": "X-FaceLens-API-Key"},
        )
        assert allowed.get("access-control-allow-origin") == ALLOWED_ORIGIN
        rejected, _ = call(
            "/", expected=400, method="OPTIONS",
            headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"},
        )
        assert "access-control-allow-origin" not in rejected
        checks.append("CORS autorise uniquement l’origine configurée")

        call("/api/faces/count", expected=401)
        _, count = call("/api/faces/count", expected=200, headers={"X-FaceLens-API-Key": API_KEY})
        assert as_json(count)["total"] == 0
        call("/static/images/not-a-real-biometric-file.png", expected=404)
        checks.append("corpus protégé et absence de montage statique biométrique")

        image = png_bytes()
        content_type, body = multipart([
            ("image_a", "test-a.png", "image/png", image),
            ("image_b", "test-b.png", "image/png", image),
        ])
        _, verified = call(
            "/api/faces/verify", expected=200, method="POST",
            headers={"X-FaceLens-API-Key": API_KEY, "Content-Type": content_type}, body=body,
        )
        result = as_json(verified)
        assert result["verified"] is True and result["similarity"] == 1.0
        checks.append("comparaison multipart avec image synthétique et repli pHash")

        invalid_type, invalid_body = multipart([
            ("image_a", "invalid.jpg", "image/jpeg", b"not-an-image"),
            ("image_b", "test-b.png", "image/png", image),
        ])
        call(
            "/api/faces/verify", expected=400, method="POST",
            headers={"X-FaceLens-API-Key": API_KEY, "Content-Type": invalid_type}, body=invalid_body,
        )
        checks.append("refus HTTP d’un faux fichier image")

        search_type, search_body = multipart([("file", "synthetic.png", "image/png", image)])
        _, search = call(
            "/api/faces/search", expected=200, method="POST",
            headers={"X-FaceLens-API-Key": API_KEY, "Content-Type": search_type}, body=search_body,
        )
        result = as_json(search)
        assert result["faces_detected"] == 0 and result["results"] == []
        checks.append("recherche sur corpus isolé sans fuite de résultat")

        print(json.dumps({"status": "success", "checks": checks}, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        print(json.dumps({"status": "failed", "error": str(error), "server_log": log[-4000:]}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
        shutil.rmtree(runtime_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
