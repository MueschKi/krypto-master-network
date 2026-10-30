"""Bounded signals from pinned Wrangler, never raw output or a debug artifact.

Text is evidence of a CLI message, not proof of Cloudflare permissions. In 4.156.0
APIError rendering omits HTTP status: never infer it from a Cloudflare error code.
Download HTTP errors refer to the signed URL, not the POST export authorization.
"""
import os
import re
import selectors
import signal
import subprocess
import time
import encrypted_d1 as core

MAX_OUTPUT = 65_536  # combined stdout + stderr, including ANSI bytes
MAX_LINE = 4096
SGR = re.compile(rb'\x1b\[[0-9;]{0,32}m')


def error(kind, *, exit_code=None, http=None, cf_codes=()):
    return core.BackupError('WRANGLER_EXPORT', stage='WRANGLER_EXPORT',
                            failure_class=kind, exit_code=exit_code, http=http, cf_codes=cf_codes)


def classify(stdout, stderr, binding, exit_code):
    if len(stdout) + len(stderr) > MAX_OUTPUT:
        return error('OUTPUT_LIMIT', exit_code=exit_code)
    findings = []
    for raw in (stdout, stderr):
        # Decode strictly; invalid bytes or controls never create a trusted signal.
        try:
            text = SGR.sub(b'', raw).decode('utf-8', errors='strict')
        except UnicodeError:
            return error('UNKNOWN', exit_code=exit_code)
        lines = [line.rstrip('\r') for line in text.split('\n')]
        if any(len(line) > MAX_LINE for line in lines):
            return error('UNKNOWN', exit_code=exit_code)
        if any(ord(c) < 32 and c not in '\n\r\t' for c in text):
            return error('UNKNOWN', exit_code=exit_code)
        # Exact known resource; other API endpoints, whoami notes, bare code/HTTP
        # numbers, URLs, SQL, and JSON supplied by remote error messages are ignored.
        resource = '/accounts/' + binding['account_id'] + '/d1/database/' + binding['database_id'] + '/export'
        header = 'A request to the Cloudflare API (' + resource + ') failed.'
        for index, line in enumerate(lines):
            message = re.sub(r'^[ \t]*(?:✘[ \t]*)?\[ERROR\][ \t]*', '', line, flags=re.ASCII).strip(' \t\r')
            if message == header:
                codes = []
                for note in lines[index + 1:index + 17]:
                    if '[ERROR]' in note or (note.strip(' \t\r') and not note.startswith('  ')):
                        break
                    match = re.fullmatch(r'  [^\x00-\x1f]{0,4000} \[code: ([0-9]{1,8})\]', note, re.ASCII)
                    if match:
                        codes.append(int(match[1]))
                kind = 'AUTH_DENIED' if set(codes) & {9106, 10000} else 'API_ERROR'
                findings.append((kind, None, tuple(sorted(set(codes)))))
            match = re.fullmatch(r'There was an error while downloading from the presigned URL with status code: ([0-9]{3})', message, re.ASCII)
            if match and 100 <= int(match[1]) <= 599:
                status = int(match[1])
                kind = {401:'DOWNLOAD_AUTH_DENIED',403:'DOWNLOAD_AUTH_DENIED',404:'DOWNLOAD_NOT_FOUND',429:'DOWNLOAD_RATE_LIMIT'}.get(status)
                kind = kind or ('DOWNLOAD_SERVER_ERROR' if status >= 500 else 'DOWNLOAD_HTTP_ERROR')
                findings.append((kind, status, ()))
            if re.fullmatch(r'Unknown arguments?: (?:skip-confirmation|remote|config|output)(?:, (?:skip-confirmation|remote|config|output))*', message, re.ASCII):
                findings.append(('CLI_SYNTAX', None, ()))
            if message == 'Please specify a file path for --output, not a directory.':
                findings.append(('CONFIG_INVALID', None, ()))
            missing_config = re.fullmatch(r'Could not read file: (?:[^\x00-\x1f]{1,4000}/)?wrangler\.export\.toml', message, re.ASCII)
            invalid_config = re.fullmatch(r'Processing (?:[^\x00-\x1f]{1,4000}/)?wrangler\.export\.toml configuration:', message, re.ASCII)
            if message.startswith('Invalid TOML document: ') or missing_config or invalid_config:
                # Only a fixed classification; never quote the config path or text.
                findings.append(('CONFIG_INVALID', None, ()))
    # Ambiguous/poisoned messages do not win by priority or guessed HTTP mappings.
    unique = set(findings)
    if len(unique) != 1:
        return error('UNKNOWN', exit_code=exit_code)
    kind, http, codes = unique.pop()
    return error(kind, exit_code=exit_code, http=http, cf_codes=codes)


def stop(process):
    # Also kill descendants retaining inherited pipe handles after the parent exits.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def run(command, *, environment, binding, timeout):
    try:
        selector = selectors.DefaultSelector()
    except OSError:
        raise error('SPAWN_FAILED') from None
    with selector:
        buffers = [bytearray(), bytearray()]
        total = 0
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       env=environment, start_new_session=True)
        except OSError:
            raise error('SPAWN_FAILED') from None
        with process:
            deadline = time.monotonic() + timeout
            try:
                for index, pipe in enumerate((process.stdout, process.stderr)):
                    os.set_blocking(pipe.fileno(), False)
                    selector.register(pipe, selectors.EVENT_READ, index)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        stop(process)
                        raise error('TIMEOUT', exit_code=process.returncode)
                    for key, _ in selector.select(min(remaining, 0.1)):
                        chunk = os.read(key.fileobj.fileno(), min(8192, MAX_OUTPUT - total + 1))
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        total += len(chunk)
                        if total > MAX_OUTPUT:
                            stop(process)
                            raise error('OUTPUT_LIMIT', exit_code=process.returncode)
                        buffers[key.data].extend(chunk)
                # A child can close both pipes and continue running.
                try:
                    process.wait(timeout=max(0.001, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    stop(process)
                    raise error('TIMEOUT', exit_code=process.returncode) from None
            except core.BackupError:
                raise
            except BaseException:
                stop(process)
                raise error('INTERRUPTED', exit_code=process.returncode) from None
            if process.returncode != 0:
                raise classify(*buffers, binding, process.returncode)
        return b''
