"""Safely inspect or create the Cloudflare EU D1 database for Phase A.

Only invoked by an explicitly user-triggered GitHub Actions workflow.
Credentials are provided as environment variables; never log or persist them.
No account JSON, portfolio ledger or Worker is changed by this script.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

NAME = "kmn"
PLACEHOLDER = 'database_id = "00000000-0000-0000-0000-000000000000"'


def wrangler(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["npx", "wrangler", *args],
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""


def list_databases() -> list[dict]:
    data = json.loads(wrangler("d1", "list", "--json", capture=True))
    if isinstance(data, dict):
        data = data.get("result", data.get("databases"))
    if not isinstance(data, list) or not all(isinstance(db, dict) for db in data):
        raise RuntimeError("Unerwartete D1-Datenbankliste; Abbruch.")
    return data


def find_database() -> str | None:
    matches = [db for db in list_databases() if db.get("name") == NAME]
    if len(matches) > 1:
        raise RuntimeError("Mehr als eine Datenbank namens kmn; keine automatische Auswahl.")
    if not matches:
        return None
    identifier = matches[0].get("uuid") or matches[0].get("id")
    try:
        return str(uuid.UUID(str(identifier)))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Unverifizierbare D1-UUID; Abbruch.") from exc


def require_eu_jurisdiction(database_id: str) -> None:
    """Verify the immutable EU jurisdiction using Cloudflare's canonical D1 GET API.

    Do not infer jurisdiction from EEUR/WEUR regional hints or the create log.
    Never reveal authentication headers, raw errors or HTTP response bodies.
    """
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not re.fullmatch("[0-9a-fA-F]{32}", account_id) or not token:
        raise RuntimeError("Cloudflare-Konto-ID oder GitHub-Secret ungueltig.")

    try:
        database_id = str(uuid.UUID(database_id))
    except (ValueError, TypeError) as exc:
        raise RuntimeError("D1-ID ist keine gueltige UUID; Abbruch.") from exc

    request = Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}",
        method="GET",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            status = response.status
            payload = response.read(65536)
    except HTTPError as exc:
        raise RuntimeError(
            f"Cloudflare D1-Detailpruefung abgelehnt (HTTP {exc.code}); "
            "kein Deploy. Token-D1-Berechtigung pruefen."
        ) from None
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(
            "Cloudflare-D1-Details konnten nicht sicher abgerufen werden; kein Deploy."
        ) from None
    if status != 200:
        raise RuntimeError("D1-Detailpruefung lieferte keinen HTTP 200; Abbruch.")

    try:
        data = json.loads(payload)
    except (ValueError, UnicodeError):
        raise RuntimeError("Nicht lesbare D1-Detailantwort; Abbruch.") from None
    if not isinstance(data, dict) or data.get("success") is not True:
        raise RuntimeError("D1-Detailantwort nicht erfolgreich; Abbruch.")
    info = data.get("result")
    if not isinstance(info, dict):
        raise RuntimeError("Keine gueltigen D1-Detaildaten; Abbruch.")
    if info.get("name") != NAME:
        raise RuntimeError("D1-Details enthalten den falschen Namen; Abbruch.")
    try:
        verified_id = str(uuid.UUID(str(info.get("uuid"))))
    except (TypeError, ValueError):
        raise RuntimeError("Cloudflare liefert keine gueltige D1-UUID; Abbruch.") from None
    if verified_id != database_id:
        raise RuntimeError("D1-ID stimmt nicht mit der Cloudflare-Detailantwort ueberein.")
    if info.get("jurisdiction") != "eu":
        raise RuntimeError(
            "Die D1-Jurisdiktion ist nicht nachweislich eu "
            "(unbekannt, fehlend oder andere Jurisdiktion); Abbruch. "
            "Keine automatische Verschiebung oder Neuanlage."
        )

def ensure_credentials() -> None:
    if not re.fullmatch("[0-9a-fA-F]{32}", os.getenv("CLOUDFLARE_ACCOUNT_ID", "")):
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID fehlt oder ist ungueltig.")
    if not os.getenv("CLOUDFLARE_API_TOKEN", "").strip():
        raise RuntimeError("CLOUDFLARE_API_TOKEN fehlt als GitHub-Secret.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("bootstrap", "resolve"))
    args = parser.parse_args()
    ensure_credentials()

    database_id = find_database()
    if args.operation == "bootstrap":
        if database_id is None:
            print("Erstelle exakt eine neue D1 kmn mit EU-Jurisdiktion.")
            wrangler("d1", "create", NAME, "--jurisdiction", "eu")
            database_id = find_database()
            if database_id is None:
                raise RuntimeError("D1-Neuanlage nicht durch D1-Liste bestaetigt; Abbruch.")
        else:
            print("D1 kmn bereits vorhanden; pruefe die unveraenderliche EU-Jurisdiktion.")
    elif database_id is None:
        raise RuntimeError("D1 kmn fehlt; bitte erst bootstrap autorisieren.")

    # Required both after creation and before *each* remote migration/deploy.
    require_eu_jurisdiction(database_id)

    if args.operation == "resolve":
        source = Path("wrangler.toml").read_text(encoding="utf-8")
        if source.count(PLACEHOLDER) != 1:
            raise RuntimeError("D1-Platzhalter fehlt oder ist mehrfach vorhanden.")
        Path("wrangler.deploy.toml").write_text(
            source.replace(PLACEHOLDER, f'database_id = "{database_id}"'),
            encoding="utf-8",
        )
        print("EU-D1-Binding nur fuer diesen temporaeren CI-Job eingerichtet.")
    else:
        print("D1 kmn vorhanden und Jurisdiktion eu bestaetigt; kein Worker-Deploy.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"Cloudflare-D1-Pruefung sicher abgebrochen: {exc}", file=sys.stderr)
        sys.exit(1)
