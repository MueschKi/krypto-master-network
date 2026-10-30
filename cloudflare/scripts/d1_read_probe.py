"""One fixed SELECT with the existing read token. No general SQL transport.

Never a snapshot or recovery proof. The caller must check manual-main consent and
GET identity first. No retry, pagination, row dump, file, subprocess or artifact.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener
import backup_preflight
import encrypted_d1 as core

STAGE = 'D1_READ_PROBE'
MAX_RESPONSE = 16_384
# Read sqlite_master, return only a constant; no private names/counts/rows leave D1.
SQL = "SELECT 1 AS read_probe FROM sqlite_master WHERE type = 'table' LIMIT 1"
BODY = json.dumps({'sql': SQL, 'params': []}, separators=(',', ':')).encode('ascii')
urlopen = build_opener(backup_preflight.NoRedirect).open


def failure(kind, *, http=None, codes=()):
    return core.BackupError(STAGE, stage=STAGE, failure_class=kind, http=http, cf_codes=codes)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def _constant(_):
    raise ValueError('non-JSON constant')


def _json(payload, content_type):
    if content_type.split(';', 1)[0].strip().lower() != 'application/json':
        raise ValueError('content type')
    return json.loads(payload.decode('utf-8'), object_pairs_hook=_object, parse_constant=_constant)


def _codes(data):
    if isinstance(data, dict) and isinstance(data.get('errors'), list):
        return [e.get('code') for e in data['errors'] if isinstance(e, dict)]
    return []


@core.staged(STAGE)
def run(binding):
    # Validate again at the transport boundary; no arbitrary host/UUID/token/SQL.
    verified = core.identity(binding['account_id'], binding['database_id'])
    if binding != verified:
        raise failure('RESULT_INVALID')
    backup_preflight.credentials()
    request = Request(
        'https://api.cloudflare.com/client/v4/accounts/' + verified['account_id']
        + '/d1/database/' + verified['database_id'] + '/query',
        data=BODY, method='POST',
        headers={'Authorization':'Bearer ' + os.environ['CLOUDFLARE_API_TOKEN'],
                 'Accept':'application/json', 'Content-Type':'application/json'},
    )
    try:
        with urlopen(request, timeout=20) as response:
            status = response.status
            content_type = response.headers.get('Content-Type', '')
            payload = response.read(MAX_RESPONSE + 1)
    except HTTPError as exc:
        status = exc.code
        content_type = exc.headers.get('Content-Type', '') if exc.headers else ''
        try:
            payload = exc.read(MAX_RESPONSE + 1)
        except (TimeoutError, OSError):
            payload = b''
        finally:
            exc.close()
    except TimeoutError:
        raise failure('TIMEOUT') from None
    except URLError as exc:
        raise failure('TIMEOUT' if isinstance(exc.reason, TimeoutError) else 'NETWORK_ERROR') from None
    except OSError:
        raise failure('NETWORK_ERROR') from None
    if type(status) is not int or not 100 <= status <= 599:
        raise failure('RESPONSE_INVALID')
    if len(payload) > MAX_RESPONSE:
        raise failure('RESPONSE_LIMIT', http=status)
    try:
        data = _json(payload, content_type)
    except (ValueError, UnicodeError, RecursionError):
        data = None
    if status != 200:
        kind = {401:'AUTH_DENIED',403:'AUTH_DENIED',429:'RATE_LIMIT'}.get(status)
        kind = kind or ('API_UNAVAILABLE' if status >= 500 else 'HTTP_ERROR')
        raise failure(kind, http=status, codes=_codes(data))
    if not isinstance(data, dict) or data.get('success') is not True or data.get('errors') != []:
        raise failure('RESPONSE_INVALID', http=status, codes=_codes(data))
    results = data.get('result')
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise failure('RESULT_INVALID', http=status)
    result = results[0]
    meta = result.get('meta')
    # Optional API fields are required here as fail-closed evidence for a SELECT.
    # They are checked in memory and never logged. No counts are printed.
    if (result.get('success') is not True or result.get('error') not in (None, '')
            or result.get('results') != [{'read_probe': 1}]
            or type(result['results'][0].get('read_probe')) is not int
            or not isinstance(meta, dict) or meta.get('changed_db') is not False
            or type(meta.get('changes')) is not int or meta['changes'] != 0
            or type(meta.get('rows_written')) is not int or meta['rows_written'] != 0):
        raise failure('RESULT_INVALID', http=status)
    return 'VERIFIED stage=D1_READ_PROBE HTTP=200'
