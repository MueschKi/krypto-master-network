"""Manually attended one-time D1 native export. NEVER run in Actions or unattended.

No broad/default OAuth scope. No migrations, imports, deploys or trades.
Device authorization, maintenance attestation and export consent are separate.
All temporary OAuth credentials remain in an isolated private directory.
"""
from __future__ import annotations

from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError

import backup_preflight
import d1_oauth_prepare as prepared
import encrypted_d1 as core
import wrangler_export_diagnostics as export_diag

ROOT = Path(__file__).resolve().parents[2]
CLOUDFLARE_DIR = ROOT / "cloudflare"
ACCOUNT = "f0a60a3beddd872d99e04f88ad4b4ddb"
DATABASE = "a3455bc2-ab04-4b72-8d46-fda459d36ee3"
OUTPUT = ROOT / ".kmn-oauth-backup-private"
MAX_JSON = 65_536
MAX_TOK = 16_384


class Refused(Exception):
    def __init__(self, stage: str):
        super().__init__(stage)
        self.stage = stage


def ensure(condition: bool, stage: str):
    if not condition:
        raise Refused(stage)


def consent(exact: str, message: str):
    print(message)
    ensure(input("Bestätigung: ").strip() == exact, "OWNER_CONSENT_MISSING")


def isolated_environment(private: Path):
    """Avoid credentials and injection inherited from Codespaces and GitHub."""
    base = {k: os.environ[k] for k in ("PATH", "SystemRoot", "LANG", "LC_ALL", "LC_CTYPE", "TERM")
            if k in os.environ}
    home = private / "home"
    config = private / "config"
    home.mkdir(mode=0o700)
    config.mkdir(mode=0o700)
    log = private / "wrangler-discard.log"
    log.symlink_to(os.devnull)
    base.update(HOME=str(home), XDG_CONFIG_HOME=str(config),
                WRANGLER_LOG_PATH=str(log), WRANGLER_LOG="error",
                WRANGLER_LOG_SANITIZE="true", WRANGLER_SEND_METRICS="false",
                NO_COLOR="1", XDG_CACHE_HOME=str(private / "cache"))
    return base


def command(argv, env, *, capture=False, timeout=120):
    try:
        result = subprocess.run(
            argv, cwd=CLOUDFLARE_DIR, env=env, timeout=timeout,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            start_new_session=True, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Refused("LOCAL_COMMAND_FAILED") from None
    ensure(result.returncode == 0, "LOCAL_COMMAND_FAILED")
    return result.stdout if capture else b""


def oauth_token(env):
    """Never expose even a partial access token through stdout, logs or files."""
    data = command(["npx", "--no-install", "wrangler", "auth", "token", "--json"],
                   env, capture=True, timeout=30)
    ensure(0 < len(data) < MAX_TOK, "AUTH_TYPE_INVALID")
    try:
        token = json.loads(data)
    except (ValueError, UnicodeError):
        raise Refused("AUTH_TYPE_INVALID") from None
    ensure(isinstance(token, dict) and token.get("type") == "oauth",
           "AUTH_TYPE_INVALID")
    value = token.get("token")
    ensure(isinstance(value, str) and bool(re.fullmatch(r"cfoat_[A-Za-z0-9_-]{12,4096}", value)),
           "AUTH_TYPE_INVALID")
    return value


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        ensure(key not in result, "D1_IDENTITY_INVALID")
        result[key] = value
    return result


def identity(token: str):
    """Exact account/database/EU binding via the official metadata GET endpoint."""
    endpoint = ("https://api.cloudflare.com/client/v4/accounts/" + ACCOUNT +
                "/d1/database/" + DATABASE)
    request = Request(endpoint,
                      headers={"Authorization": "Bearer " + token,
                               "Accept": "application/json"}, method="GET")
    try:
        with build_opener(backup_preflight.NoRedirect).open(request, timeout=20) as response:
            ensure(response.status == 200, "D1_IDENTITY_INVALID")
            payload = response.read(MAX_JSON + 1)
            ensure(0 < len(payload) <= MAX_JSON, "D1_IDENTITY_INVALID")
    except (HTTPError, URLError, OSError, TimeoutError):
        raise Refused("D1_IDENTITY_INVALID") from None
    try:
        data = json.loads(payload.decode("utf-8"), object_pairs_hook=no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise Refused("D1_IDENTITY_INVALID") from None
    ensure(isinstance(data, dict) and data.get("success") is True and data.get("errors") == [],
           "D1_IDENTITY_INVALID")
    record = data.get("result")
    ensure(isinstance(record, dict) and record.get("uuid") == DATABASE
           and record.get("name") == "kmn" and record.get("jurisdiction") == "eu",
           "D1_IDENTITY_INVALID")
    return core.identity(ACCOUNT, DATABASE)


def source_commit(env):
    branch = command(["git", "-C", str(ROOT), "branch", "--show-current"],
                     env, capture=True, timeout=15).strip()
    ensure(branch == b"main", "MAIN_BRANCH_REQUIRED")
    sha = command(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                  env, capture=True, timeout=15).decode("ascii").strip()
    ensure(bool(re.fullmatch("[0-9a-f]{40}", sha)), "MAIN_BRANCH_REQUIRED")
    return sha


def key_from_operator():
    print("Backup-Passphrase aus deinem Passwortmanager eingeben (zweimal, ohne Echo).")
    a = getpass.getpass("Passphrase: ")
    b = getpass.getpass("Passphrase wiederholen: ")
    ensure(isinstance(a, str) and len(a) >= 32 and a == b
           and "\n" not in a and "\r" not in a, "PASSPHRASE_INVALID")
    return a


def perform(scratch: Path, env):
    """All user interaction here is manual; never scheduled or called from CI."""
    ensure(os.getenv("CODESPACES", "").lower() == "true" or bool(os.getenv("CODESPACE_NAME")),
           "ISOLATED_CODESPACE_REQUIRED")
    ensure(sys.stdin.isatty() and sys.stdout.isatty(), "PRIVATE_TTY_REQUIRED")
    ensure(not OUTPUT.exists() and not OUTPUT.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    ensure((CLOUDFLARE_DIR / "node_modules/wrangler/package.json").is_file(),
           "RUN_INSTALL_TASK_FIRST")
    prepared.contract()
    commit = source_commit(env)

    print("Einmaliges Backup der bestehenden D1 kmn (EU).")
    print("Cloudflare OAuth benötigt d1:write und offline_access; der Zugriff ist weitreichend.")
    print("Der Codespace kann GitHub-Kosten verursachen. Kein Export ohne weitere Bestätigungen.")
    print("Cloudflare Cron und ALLE anderen D1-Schreiber müssen zuvor separat angehalten")
    print("und auf in-flight Requests, Queues und manuelle Clients kontrolliert worden sein.")
    consent("WRITERS_CONFIRMED_STOPPED", "Nur nach vollständiger, selbst überprüfter Schreibpause:")
    consent("I_ACCEPT_ONE_TIME_D1_WRITE", "Nur für diesen einmaligen OAuth-Grant:")

    login_started = False
    try:
        # The private Codespace terminal must show the device URL/code to its owner.
        login_started = True
        command(["npx", "--no-install", "wrangler", "login", "--device",
                 "--browser=false", "--scopes", "d1:write"], env, timeout=400)
        token = oauth_token(env)
        binding = identity(token)
        print("Cloudflare-OAuth und EXAKTE kmn/EU-Identität geprüft.")
        consent("EXPORT_THIS_KMN_ONCE", "Produktiver D1-Export darf Anfragen vorübergehend blockieren.")
        config = scratch / "wrangler.export.toml"
        core.write_new(
            config,
            ('name = "kmn-one-time-only"\naccount_id = "' + ACCOUNT +
             '"\n[[d1_databases]]\nbinding = "DB"\ndatabase_name = "kmn"\n'
             'database_id = "' + DATABASE + '"\n').encode("ascii"))
        source = scratch / "export.sql"
        try:
            export_diag.run(
                ["npx", "--no-install", "wrangler", "d1", "export", "kmn",
                 "--remote", "--skip-confirmation", "--config", str(config),
                 "--output", str(source)],
                environment=env, binding=binding, timeout=900)
        except core.BackupError as exc:
            print(core.safe_failure(exc), file=sys.stderr)
            raise Refused("D1_EXPORT_FAILED") from None
        ensure(source.is_file() and not source.is_symlink()
               and 0 < source.stat().st_size <= core.MAX_FILE, "EXPORT_INCOMPLETE")
        os.chmod(source, 0o600)
        identity(token)  # Verify the same source after the native export.
        secret = key_from_operator()
        origin = {"repository": "MueschKi/krypto-master-network",
                  "run_id": "oauth-once-" + uuid.uuid4().hex, "commit": commit}
        prepared.verified_package(source, scratch, binding, origin, secret, OUTPUT)
        print("VERIFIED: verschlüsseltes Backup + zweimal unabhängige SQL/SQLite-Recovery.")
        print("Nur die Dateien in .kmn-oauth-backup-private privat herunterladen.")
        print("Dateien an zwei sicheren Orten aufbewahren, Passphrase getrennt sichern.")
        return True
    finally:
        if login_started:
            # Best effort revocation, not merely deletion of local credentials.
            try:
                command(["npx", "--no-install", "wrangler", "logout"], env,
                        capture=True, timeout=30)
                print("Wrangler OAuth-Logout ausgeführt.")
            except (Refused, Exception):
                print("WARNUNG: OAuth-Logout nicht bestätigt!", file=sys.stderr)
            print("OAuth-Zugriff zusätzlich im Cloudflare-Dashboard kontrollieren/widerrufen:")
            print("https://dash.cloudflare.com/profile/authorizations")


def main():
    if len(sys.argv) != 2 or sys.argv[1] != "--run":
        print("Nur interaktiv: VS Code → Tasks: Run Task → D1: 3 Einmal-Backup (OAuth).")
        print("Kein Login, Export oder Backup wurde gestartet.")
        return 2
    os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix="kmn-oauth-once-") as tmp:
            scratch = Path(tmp)
            env = isolated_environment(scratch)
            return 0 if perform(scratch, env) else 1
    except (Refused, core.BackupError) as exc:
        stage = exc.stage if isinstance(exc, Refused) else core.safe_failure(exc)
        print("FAILED " + stage, file=sys.stderr)
    except (KeyboardInterrupt, EOFError):
        print("FAILED OPERATOR_CANCELLED", file=sys.stderr)
    except BaseException:
        # Never reveal raw exception/HTTP/SQLite/GPG/private diagnostic contents.
        print("FAILED UNCLASSIFIED: no backup approval", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
