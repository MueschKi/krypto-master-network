"""Bounded, GET-only metadata checks. Never print responses or third-party errors.

REST list/detail is deliberate: Wrangler d1 list can require unrelated scopes.
No fallback token, scope extension, export, SQL query, or data-row read exists here.
"""
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


urlopen = build_opener(NoRedirect).open
import encrypted_d1 as core

LIMIT = 1_000_000


def get(suffix, stage):
    # suffix is constructed only by this module, from validated identifiers.
    with core.at_stage(stage):
        token = os.getenv('CLOUDFLARE_API_TOKEN', '')
        core.require(bool(re.fullmatch(r'[A-Za-z0-9_-]{20,256}', token)), 'SECRET_FORMAT')
        request = Request('https://api.cloudflare.com/client/v4' + suffix,
                          headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'}, method='GET')
        try:
            with urlopen(request, timeout=20) as response:
                status, payload = response.status, response.read(LIMIT + 1)
        except HTTPError as exc:
            status = exc.code
            try:
                payload = exc.read(LIMIT + 1)
            except Exception:
                payload = b''
            finally:
                exc.close()
        except Exception:
            raise core.BackupError(stage, stage=stage) from None
        data = None
        if len(payload) <= LIMIT:
            try:
                data = json.loads(payload)
            except (ValueError, UnicodeError):
                pass
        codes = []
        if isinstance(data, dict) and isinstance(data.get('errors'), list):
            codes = [e.get('code') for e in data['errors'] if isinstance(e, dict)]
        if status != 200 or not isinstance(data, dict) or data.get('success') is not True:
            raise core.BackupError(stage, stage=stage, http=status, cf_codes=codes)
        return data


def credentials():
    with core.at_stage('SECRET_FORMAT'):
        core.require(bool(re.fullmatch(r'[A-Za-z0-9_-]{20,256}', os.getenv('CLOUDFLARE_API_TOKEN', ''))), 'SECRET_FORMAT')


def token_status():
    data = get('/user/tokens/verify', 'ENV_CONTEXT')
    with core.at_stage('ENV_CONTEXT'):
        core.require(isinstance(data.get('result'), dict) and data['result'].get('status') == 'active', 'ENV_CONTEXT')


def verify(binding):
    credentials()
    prefix = '/accounts/' + binding['account_id'] + '/d1/database'
    with core.at_stage('D1_LIST'):
        matches = []
        for page in range(1, 101):
            data = get(prefix + '?per_page=100&page=' + str(page), 'D1_LIST')
            result, info = data.get('result'), data.get('result_info')
            core.require(isinstance(result, list) and all(isinstance(db, dict) for db in result), 'D1_LIST')
            matches.extend(db for db in result if db.get('name') == 'kmn')
            core.require(len(matches) <= 1, 'D1_LIST')
            # The documented API exposes count/page/per_page/total_count;
            # accept explicit total_pages too, but never infer EOF from a short page.
            core.require(isinstance(info, dict) and info.get('page') == page, 'D1_LIST')
            pages = info.get('total_pages')
            if pages is None:
                count, per_page = info.get('total_count'), info.get('per_page')
                core.require(type(count) is int and 0 <= count <= 10000
                             and type(per_page) is int and 1 <= per_page <= 100, 'D1_LIST')
                pages = (count + per_page - 1) // per_page
            core.require(type(pages) is int and 0 <= pages <= 100, 'D1_LIST')
            if page >= pages:
                break
        core.require(len(matches) == 1 and matches[0].get('uuid') == binding['database_id'], 'D1_LIST')
    with core.at_stage('D1_DETAIL_EU'):
        data = get(prefix + '/' + binding['database_id'], 'D1_DETAIL_EU')
        info = data.get('result')
        core.require(isinstance(info, dict) and info.get('name') == 'kmn'
                     and info.get('uuid') == binding['database_id'] and info.get('jurisdiction') == 'eu', 'D1_DETAIL_EU')


@core.staged('ENV_CONTEXT')
def tools_available(scratch):
    # Only the locked local wrapper, no npx download and no authenticated command.
    expected = json.loads((Path(__file__).parent.parent/'package-lock.json').read_text())['packages']['node_modules/wrangler']['version']
    environment = {k: v for k, v in os.environ.items() if k not in
                   ('CLOUDFLARE_API_TOKEN', 'D1_BACKUP_PASSPHRASE', 'GH_TOKEN')}
    environment.update(WRANGLER_SEND_METRICS='false', WRANGLER_LOG_PATH=str(Path(scratch)/'private.log'))
    result = subprocess.run(['npx', '--no-install', 'wrangler', '--version'], env=environment,
                            capture_output=True, text=True, timeout=30)
    core.require(result.returncode == 0 and re.search(r'(?<![\d.])' + re.escape(expected) + r'(?![\d.])', result.stdout), 'ENV_CONTEXT')
    result = subprocess.run(['gpg', '--version'], env=environment, capture_output=True, timeout=10)
    core.require(result.returncode == 0, 'ENV_CONTEXT')
