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


def parse_json_object(output: str) -> dict:
    data = json.loads(output)
    # Some Cloudflare tools wrap response objects in "result".
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        data = data["result"]
    if not isinstance(data, dict):
        raise RuntimeError("Unerwartete D1-Info-Antwort; keine Freigabe.")
    return data


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
    """D1 jurisdiction is immutable. A location hint is NOT enough."""
    info = parse_json_object(wrangler("d1", "info", NAME, "--json", capture=True))
    if info.get("name") != NAME:
        raise RuntimeError("D1-Info meldet falschen/fehlenden Datenbanknamen; Abbruch.")
    info_id = info.get("uuid") or info.get("id")
    if info_id is not None:
        try:
            verified_id = str(uuid.UUID(str(info_id)))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Unlesbare D1-ID in der Detailabfrage.") from exc
        if verified_id != database_id:
            raise RuntimeError("D1-Liste und Detailabfrage stimmen nicht ueberein; Abbruch.")
    jurisdiction = info.get("jurisdiction")
    if jurisdiction != "eu":
        raise RuntimeError(
            "D1-Jurisdiktion ist nicht nachweislich eu "
            "(fehlend/unbekannt/andere Jurisdiktion). "
            "Bestehende DB nicht automatisch verwenden oder aendern."
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
