"""Read-only diagnosis of the Cloudflare token, account scope and D1 access.

Run only through the owner's manually dispatched GitHub Actions workflow.
Never print tokens, raw Cloudflare responses, URLs, account IDs, headers or
Wrangler stderr. This program performs only HTTPS GETs and an optional D1 list.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://api.cloudflare.com/client/v4"
MAX_RESPONSE = 65536


def api_get(path: str, token: str) -> tuple[int, dict]:
    request = Request(
        BASE + path,
        method="GET",
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            status, payload = response.status, response.read(MAX_RESPONSE)
    except HTTPError as exc:
        status, payload = exc.code, exc.read(MAX_RESPONSE)
    except (URLError, TimeoutError, OSError) as exc:
        # Never print a third-party exception, which may contain a full URL.
        print("NETZWERKFEHLER: Cloudflare-API nicht erreichbar (keine Details ausgegeben).")
        raise RuntimeError("Cloudflare-Netzwerkfehler") from None

    try:
        obj = json.loads(payload)
    except (ValueError, UnicodeError):
        obj = {}
    return status, obj if isinstance(obj, dict) else {}


def error_codes(data: dict) -> str:
    """Return *only* short numeric Cloudflare codes, never arbitrary messages."""
    codes = []
    for item in data.get("errors", []):
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        if isinstance(code, int) and 0 <= code <= 999999:
            codes.append(str(code))
        elif isinstance(code, str) and re.fullmatch(r"[0-9]{1,6}", code):
            codes.append(code)
    return ",".join(codes[:4]) if codes else "keine"


def credentials() -> tuple[str, str]:
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{32}", account):
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID ist nicht als gueltige GitHub-Variable gesetzt.")
    if not token:
        raise RuntimeError("CLOUDFLARE_API_TOKEN ist nicht als GitHub-Secret gesetzt.")
    return account, token


def diagnose() -> int:
    account, token = credentials()
    print("Cloudflare-Verbindung: nur lesende Pruefung. Keine Ressourcen-Aenderungen.")

    status, response = api_get("/user/tokens/verify", token)
    token_status = response.get("result", {}).get("status") if isinstance(response.get("result"), dict) else None
    if status != 200 or response.get("success") is not True or token_status != "active":
        print(f"TOKEN: nicht erfolgreich verifiziert (HTTP {status}; Code {error_codes(response)}).")
        print("Pruefe GitHub-Secret, Token-Aktivierung, Ablauf und IP-Beschraenkung.")
        return 1
    print("TOKEN: aktiv und von Cloudflare akzeptiert.")

    status, response = api_get(f"/accounts/{account}/d1/database", token)
    if status != 200 or response.get("success") is not True:
        print(f"D1: Datenbankliste nicht lesbar (HTTP {status}; Code {error_codes(response)}).")
        if status in (401, 403) or "10000" in error_codes(response).split(","):
            print("Haeufige Ursachen: falscher Account-Scope, fehlende Account-D1-Rechte "
                  "(D1 Read/Edit bzw. D1 Admin fuer Erstanlage), andere Kontozuordnung.")
        else:
            print("Bitte Cloudflare-Status und Token-Berechtigungen pruefen; keine automatische Rechteausweitung.")
        return 2
    print("D1: Cloudflare-REST-Abfrage der Datenbankliste erfolgreich.")

    # Compare official Wrangler command to REST API, without revealing raw errors.
    try:
        result = subprocess.run(
            ["npx", "wrangler", "d1", "list", "--json"],
            text=True, capture_output=True, check=False, timeout=45,
        )
    except (OSError, subprocess.TimeoutExpired):
        print("WRANGLER: konnte den lesenden D1-Befehl nicht ausfuehren.")
        return 3
    if result.returncode != 0:
        print("WRANGLER: D1-Liste fehlgeschlagen, obwohl REST-Zugriff funktioniert. "
              "Wrangler-Version/Konfiguration getrennt pruefen.")
        return 3
    try:
        databases = json.loads(result.stdout)
        if isinstance(databases, dict):
            databases = databases.get("result", databases.get("databases"))
        if not isinstance(databases, list):
            raise ValueError("unexpected shape")
    except (ValueError, TypeError):
        print("WRANGLER: unerwartete JSON-Antwort; keine Cloud-Operation.")
        return 3
    print("WRANGLER: D1-Liste erfolgreich lesbar.")
    print("DIAGNOSE OK. Du kannst separat einen bewussten bootstrap-Lauf freigeben.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(diagnose())
    except RuntimeError as exc:
        # Only own curated text is allowed.
        print(str(exc), file=sys.stderr)
        sys.exit(1)
