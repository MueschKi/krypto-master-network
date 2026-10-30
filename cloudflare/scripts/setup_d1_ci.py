"""Resolve or create the dedicated Cloudflare D1 database for Phase A.

Only called manually by the owner's GitHub Actions workflow. All authentication
comes from the environment via CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN.
This script never logs or persists credentials, modifies account files or
runs a Worker deployment.
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
    cmd = ["npx", "wrangler", *args]
    result = subprocess.run(
        cmd, check=True, text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""


def list_databases() -> list[dict]:
    output = wrangler("d1", "list", "--json", capture=True)
    data = json.loads(output)
    if isinstance(data, dict):
        data = data.get("result", data.get("databases", None))
    if not isinstance(data, list):
        raise RuntimeError("Unerwartete Wrangler-D1-JSON-Antwort; Abbruch.")
    if not all(isinstance(item, dict) for item in data):
        raise RuntimeError("Nicht interpretierbare D1-Eintraege; Abbruch.")
    return data


def find_database() -> str | None:
    matches = [db for db in list_databases() if db.get("name") == NAME]
    if len(matches) > 1:
        raise RuntimeError("Mehr als eine Datenbank namens 'kmn'; Abbruch.")
    if not matches:
        return None
    identifier = matches[0].get("uuid") or matches[0].get("id")
    try:
        return str(uuid.UUID(str(identifier)))
    except (ValueError, TypeError) as exc:
        raise RuntimeError("D1-Datenbank-ID ist keine UUID; Abbruch.") from exc


def ensure_credentials() -> None:
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not re.fullmatch("[0-9a-fA-F]{32}", account_id):
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID fehlt oder ist ungueltig.")
    if not token.strip():
        raise RuntimeError("CLOUDFLARE_API_TOKEN fehlt als GitHub-Secret.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("bootstrap", "resolve"))
    args = parser.parse_args()
    ensure_credentials()

    database_id = find_database()
    if args.operation == "bootstrap":
        if database_id is None:
            print("Erstelle die D1-Datenbank kmn (EU-Jurisdiktion).")
            wrangler("d1", "create", NAME, "--jurisdiction", "eu")
            database_id = find_database()
            if database_id is None:
                raise RuntimeError("D1-Erstellung nicht in Liste bestaetigt; Abbruch.")
        else:
            print("D1 kmn besteht bereits; keine zweite Datenbank angelegt.")
    elif database_id is None:
        raise RuntimeError("D1 kmn fehlt. Erst 'bootstrap' ausfuehren.")

    if args.operation == "resolve":
        config_path = Path("wrangler.toml")
        config = config_path.read_text(encoding="utf-8")
        if config.count(PLACEHOLDER) != 1:
            raise RuntimeError("Erwarteter eindeutiger D1-Platzhalter fehlt.")
        Path("wrangler.deploy.toml").write_text(
            config.replace(PLACEHOLDER, f'database_id = "{database_id}"'),
            encoding="utf-8",
        )
        print("D1-Binding fuer diesen GitHub-Job konfiguriert.")
    else:
        print(f"Cloudflare-D1 'kmn' bereit (ID: {database_id}).")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"Cloudflare-Setup sicher abgebrochen: {exc}", file=sys.stderr)
        sys.exit(1)
