"""Synthetic processes/output only. No Wrangler CLI, API calls or exports."""
import contextlib
import io
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import tomllib
import unittest
from unittest.mock import patch
from test_d1_backup import ci, core, BINDING, ROOT, KEY
import wrangler_export_diagnostics as diag

POISON = 'SECRET_CANARY https://signed.invalid/export.sql?token=SECRET_CANARY SELECT private_table; 🔒'
HEADER = ('✘ [ERROR] A request to the Cloudflare API (/accounts/' + BINDING['account_id']
          + '/d1/database/' + BINDING['database_id'] + '/export) failed.\n\n')


def formatted(data, exit_code=1, stderr=b''):
    return core.safe_failure(diag.classify(data, stderr, BINDING, exit_code))


class ExportClassifierTests(unittest.TestCase):
    def test_actual_api_envelope_preserves_numeric_codes_without_inventing_http(self):
        data=(HEADER+'  '+POISON+' HTTP 403 [code: 10000]\n\n').encode()
        self.assertEqual(formatted(data), 'FAILED stage=WRANGLER_EXPORT class=AUTH_DENIED EXIT=1 CF=10000')
        data=(HEADER+'  Rate limit HTTP 429 [code: 12345]\n').encode()
        self.assertEqual(formatted(data,17),'FAILED stage=WRANGLER_EXPORT class=API_ERROR EXIT=17 CF=12345')
        self.assertEqual(formatted(HEADER.encode()),'FAILED stage=WRANGLER_EXPORT class=API_ERROR EXIT=1')
        for code in ('-1','NaN','١٠٠٠٠','10000SECRET', '123456789'):
            self.assertEqual(formatted((HEADER+'  message [code: '+code+']\n').encode()),
                             'FAILED stage=WRANGLER_EXPORT class=API_ERROR EXIT=1')

    def test_download_status_is_separate_from_post_authorization(self):
        for status,kind in [(401,'DOWNLOAD_AUTH_DENIED'),(403,'DOWNLOAD_AUTH_DENIED'),(404,'DOWNLOAD_NOT_FOUND'),
                            (429,'DOWNLOAD_RATE_LIMIT'),(500,'DOWNLOAD_SERVER_ERROR'),(503,'DOWNLOAD_SERVER_ERROR'),
                            (599,'DOWNLOAD_SERVER_ERROR'),(400,'DOWNLOAD_HTTP_ERROR')]:
            data=f'✘ [ERROR] There was an error while downloading from the presigned URL with status code: {status}\n'.encode()
            self.assertEqual(formatted(data),f'FAILED stage=WRANGLER_EXPORT class={kind} EXIT=1 HTTP={status}')
        for text in ('HTTP 403','status code: 429','{"status":403,"code":10000}',
                     'There was an error while downloading from the presigned URL with status code: ４０３',
                     'There was an error while downloading from the presigned URL with status code: 999'):
            self.assertEqual(formatted(text.encode()),'FAILED stage=WRANGLER_EXPORT class=UNKNOWN EXIT=1')

    def test_foreign_routes_unscoped_codes_and_conflicting_messages_are_unknown(self):
        for text in (POISON+' [code: 10000]',HEADER.replace('/export','/query')+'  message [code: 10000]',
                     HEADER.replace(BINDING['database_id'],'other')+'  message [code: 10000]',
                     HEADER+'  message [code: 10000]\n✘ [ERROR] Unknown argument: remote'):
            self.assertEqual(formatted(text.encode()),'FAILED stage=WRANGLER_EXPORT class=UNKNOWN EXIT=1')
        # Codes in later error blocks are not attributed to the export request.
        text=HEADER+'A request to the Cloudflare API (/unrelated) failed.\n  message [code: 10000]'
        self.assertEqual(formatted(text.encode()),'FAILED stage=WRANGLER_EXPORT class=API_ERROR EXIT=1')

    def test_cli_and_config_failures_use_only_fixed_classes(self):
        for text,kind in [('✘ [ERROR] Unknown argument: skip-confirmation','CLI_SYNTAX'),
                          ('Unknown arguments: remote, output','CLI_SYNTAX'),
                          ('✘ [ERROR] Invalid TOML document: '+POISON,'CONFIG_INVALID'),
                          ('✘ [ERROR] Could not read file: /private/wrangler.export.toml','CONFIG_INVALID'),
                          ('✘ [ERROR] Processing /private/wrangler.export.toml configuration:','CONFIG_INVALID'),
                          ('Please specify a file path for --output, not a directory.','CONFIG_INVALID')]:
            self.assertEqual(formatted(text.encode()),f'FAILED stage=WRANGLER_EXPORT class={kind} EXIT=1')
        self.assertIn('class=UNKNOWN',formatted(b'Unknown argument: untrusted-flag'))

    def test_bounds_encoding_controls_ansi_and_stderr_are_safe(self):
        envelope=(HEADER+'  '+POISON+' [code: 9106]\n').encode()
        self.assertEqual(formatted(b'\x1b[31m'+envelope+b'\x1b[0m'),'FAILED stage=WRANGLER_EXPORT class=AUTH_DENIED EXIT=1 CF=9106')
        self.assertEqual(formatted(b'',stderr=envelope),'FAILED stage=WRANGLER_EXPORT class=AUTH_DENIED EXIT=1 CF=9106')
        for poisoned in (b'\xff'+envelope,b'\x00'+envelope,b'x'*(diag.MAX_LINE+1), '\u2028'.encode()+envelope):
            self.assertEqual(formatted(poisoned),'FAILED stage=WRANGLER_EXPORT class=UNKNOWN EXIT=1')
        self.assertEqual(formatted(b'x'*(diag.MAX_OUTPUT+1)),'FAILED stage=WRANGLER_EXPORT class=OUTPUT_LIMIT EXIT=1')

    def test_only_allowlisted_metadata_crosses_renderer_and_other_stages_are_unchanged(self):
        forged=core.BackupError(POISON,stage='WRANGLER_EXPORT',failure_class=POISON,exit_code=POISON,http=403,cf_codes=[POISON])
        self.assertEqual(core.safe_failure(forged),'FAILED stage=WRANGLER_EXPORT class=UNKNOWN')
        forged=core.BackupError(POISON,stage='SQL_IMPORT',failure_class='AUTH_DENIED',exit_code=1,http=403,cf_codes=[10000])
        self.assertEqual(core.safe_failure(forged),'FAILED stage=SQL_IMPORT')


class ExportProcessTests(unittest.TestCase):
    def run_fake(self, code, timeout=3):
        # Child inherits no production credential; code is a fixed synthetic program.
        return ci.quiet([sys.executable,'-c',code], environment={'PATH':os.defpath},timeout=timeout,export_binding=BINDING)

    def test_real_exit_codes_stdout_stderr_and_no_secret_logging(self):
        for exit_code in (1,2,17,255):
            code='import sys; print('+repr(POISON)+'); print('+repr(HEADER+'  '+POISON+' [code: 10000]')+',file=sys.stderr); sys.exit('+str(exit_code)+')'
            with contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(core.BackupError) as caught:self.run_fake(code)
            self.assertEqual(out.getvalue()+err.getvalue(),'')
            self.assertEqual(core.safe_failure(caught.exception),f'FAILED stage=WRANGLER_EXPORT class=AUTH_DENIED EXIT={exit_code} CF=10000')
            self.assertNotIn(POISON,str(caught.exception))
        self.assertEqual(self.run_fake('print('+repr(POISON)+')'),b'')

    def test_timeout_output_flood_and_closed_pipes_fail_closed(self):
        for code,kind in [('import time;time.sleep(10)','TIMEOUT'),
                          ('import os,time;os.close(1);os.close(2);time.sleep(10)','TIMEOUT'),
                          ('import os;os.write(1,b"x"*1000000)','OUTPUT_LIMIT')]:
            with self.assertRaises(core.BackupError) as caught:self.run_fake(code,timeout=3 if kind == 'OUTPUT_LIMIT' else 0.15)
            self.assertIn('class='+kind,core.safe_failure(caught.exception))

    def test_descendants_retaining_pipes_are_killed_on_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile=Path(tmp)/'pid'
            code='import subprocess,sys; p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"]);open('+repr(str(pidfile))+',"w").write(str(p.pid))'
            with self.assertRaises(core.BackupError) as caught:self.run_fake(code,timeout=1)
            self.assertIn('class=TIMEOUT',core.safe_failure(caught.exception))
            pid=int(pidfile.read_text())
            status=Path('/proc')/str(pid)/'stat'
            # SIGKILL delivery is asynchronous when the group leader has exited.
            deadline=time.monotonic()+1
            while status.exists() and status.read_text().split()[2]!='Z' and time.monotonic()<deadline:
                time.sleep(0.01)
            self.assertTrue(not status.exists() or status.read_text().split()[2]=='Z')

    def test_spawn_stream_failure_and_signal_exit_are_classified(self):
        with self.assertRaises(core.BackupError) as caught:
            diag.run(['/missing/fake-wrangler'],environment={},binding=BINDING,timeout=1)
        self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=WRANGLER_EXPORT class=SPAWN_FAILED')
        original_popen, original_read = diag.subprocess.Popen, diag.os.read
        started = False
        def popen(*args, **kwargs):
            nonlocal started
            proc = original_popen(*args, **kwargs)
            started = True
            return proc
        def read(*args):
            if started: raise OSError(POISON)
            return original_read(*args)
        with patch.object(diag.subprocess,'Popen',side_effect=popen),patch.object(diag.os,'read',side_effect=read):
            with self.assertRaises(core.BackupError) as caught:self.run_fake('print("synthetic",flush=True);import time;time.sleep(20)')
        self.assertIn('class=INTERRUPTED',core.safe_failure(caught.exception))
        with self.assertRaises(core.BackupError) as caught:self.run_fake('import os,signal;os.kill(os.getpid(),signal.SIGTERM)')
        self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=WRANGLER_EXPORT class=UNKNOWN EXIT=-15')

    def test_export_discards_debug_file_and_removes_passphrase_without_broadening_credentials(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(ci,'remote_verify'):
            def fake(command,**kwargs):
                env=kwargs['environment']; self.assertNotIn('D1_BACKUP_PASSPHRASE',env)
                self.assertEqual(env['WRANGLER_LOG'],'error');self.assertEqual(env['WRANGLER_LOG_SANITIZE'],'true')
                log=Path(env['WRANGLER_LOG_PATH']);self.assertTrue(log.is_symlink());self.assertEqual(os.readlink(log),os.devnull)
                log.write_text(POISON);self.assertEqual(log.read_bytes(),b'')
                self.assertEqual(kwargs['export_binding'],BINDING)
                self.assertIn('--skip-confirmation',command)
                config_path=Path(command[command.index('--config')+1])
                config=tomllib.loads(config_path.read_text())
                self.assertEqual(config['account_id'],BINDING['account_id'])
                self.assertEqual(config['d1_databases'],[{'binding':'DB','database_name':'kmn','database_id':BINDING['database_id']}])
                self.assertTrue(config_path.is_absolute());self.assertTrue(Path(command[-1]).is_absolute())
                Path(command[-1]).write_text('synthetic')
            with patch.object(ci,'quiet',side_effect=fake),patch.dict(os.environ,{'D1_BACKUP_PASSPHRASE':KEY}):ci.export_sql(BINDING,tmp)
            self.assertEqual({p.name for p in Path(tmp).iterdir()},{'export.sql','wrangler.export.toml','wrangler-discard.log'})

    def test_cli_export_failure_emits_only_safe_fields_and_cleans_plaintext(self):
        from test_backup_diagnostics import ENV
        with tempfile.TemporaryDirectory() as tmp:
            program = (
                'import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'cloudflare/scripts'))+');'
                'import backup_preflight as p,wrangler_export_diagnostics as d;'
                'p.verify=lambda binding:None;'
                'd.run=lambda *args,**kwargs:(_ for _ in ()).throw(d.classify('
                +repr((HEADER+'  '+POISON+' [code: 10000]\n').encode())+',b"",'
                +repr(BINDING)+',2));'
                'sys.argv=["d1_backup_ci.py","backup","--publish-dir",'+repr(tmp+'/out')+'];'
                'runpy.run_path('+repr(str(ROOT/'cloudflare/scripts/d1_backup_ci.py'))+',run_name="__main__")'
            )
            environment={**ENV,'PATH':os.defpath,'RUNNER_TEMP':tmp,'D1_BACKUP_PASSPHRASE':KEY,
                         'BACKUP_CONFIRMATION':'EXPORT_EXISTING_KMN','MAINTENANCE_CONFIRMATION':'OWNER_CONFIRMED_MAINTENANCE'}
            result=subprocess.run([sys.executable,'-c',program],env=environment,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,1)
            self.assertEqual(result.stdout,'')
            self.assertEqual(result.stderr,'FAILED stage=WRANGLER_EXPORT class=AUTH_DENIED EXIT=2 CF=10000\n')
            self.assertEqual(list(Path(tmp).iterdir()),[])
