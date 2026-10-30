"""Probe-only safety tests. Every HTTP response and credential is synthetic."""
import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from test_d1_backup import ci, core, BINDING, ORIGIN, ROOT, KEY
from test_backup_diagnostics import ENV, listed, detail
import d1_read_probe as probe

CANARY = 'PRIVATE_CANARY https://signed.invalid/?token=SECRET SELECT private_table 🔒'
PROBE_ENV = {**ENV, 'BACKUP_CONFIRMATION':'READ_ONLY_PROBE_KMN'}


def envelope():
    return {'success':True,'errors':[],'result':[{'success':True,'results':[{'read_probe':1}],
            'meta':{'changed_db':False,'changes':0,'rows_written':0}}]}


def response(data=None, *, payload=None, status=200, content_type='application/json'):
    result = Mock()
    result.status = status
    result.headers = {'Content-Type':content_type}
    result.read.return_value = json.dumps(data if data is not None else envelope()).encode() if payload is None else payload
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    return result


class ReadProbeTransportTests(unittest.TestCase):
    def test_exact_single_request_fixed_host_endpoint_and_select(self):
        def fake(request, timeout):
            self.assertEqual(request.method,'POST')
            self.assertEqual(request.full_url,'https://api.cloudflare.com/client/v4/accounts/'+BINDING['account_id']+'/d1/database/'+BINDING['database_id']+'/query')
            self.assertEqual(json.loads(request.data),{'sql':probe.SQL,'params':[]})
            self.assertEqual(request.get_header('Authorization'),'Bearer '+PROBE_ENV['CLOUDFLARE_API_TOKEN'])
            self.assertEqual(timeout,20)
            return response()
        with patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(probe,'urlopen',side_effect=fake) as network:
            self.assertEqual(probe.run(BINDING),'VERIFIED stage=D1_READ_PROBE HTTP=200')
            network.assert_called_once()
        for forbidden in ('/export','/import','/raw','/query?','CREATE','PRAGMA','INSERT','UPDATE','DELETE','OFFSET',';'):
            self.assertNotIn(forbidden,probe.SQL)

    def test_401_403_429_5xx_and_redirect_are_classified_without_retry(self):
        for status,kind in [(401,'AUTH_DENIED'),(403,'AUTH_DENIED'),(429,'RATE_LIMIT'),(500,'API_UNAVAILABLE'),(503,'API_UNAVAILABLE'),(302,'HTTP_ERROR'),(404,'HTTP_ERROR')]:
            body={'success':False,'errors':[{'code':10000,'message':CANARY},{'code':True},{'code':CANARY},{'code':-1},{'code':999999999}]}
            error=HTTPError('https://private.invalid',status,CANARY,{'Content-Type':'application/json'},io.BytesIO(json.dumps(body).encode()))
            with patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(probe,'urlopen',side_effect=error) as network:
                with self.assertRaises(core.BackupError) as caught:probe.run(BINDING)
                self.assertEqual(core.safe_failure(caught.exception),f'FAILED stage=D1_READ_PROBE class={kind} HTTP={status} CF=10000')
                self.assertNotIn(CANARY,str(caught.exception));network.assert_called_once()

    def test_positive_http_without_valid_evidence_is_never_success(self):
        cases=[]
        for mutate in (lambda d:d.update(success=False),lambda d:d.update(errors=[{'code':10000,'message':CANARY}]),
                       lambda d:d.update(result=[]),lambda d:d.update(result=[d['result'][0],d['result'][0]]),
                       lambda d:d['result'][0].update(success=False),lambda d:d['result'][0].update(error=CANARY),lambda d:d['result'][0].update(results=[]),
                       lambda d:d['result'][0].update(results=[{'read_probe':1},{'read_probe':1}]),
                       lambda d:d['result'][0].update(results=[{'read_probe':True}]),lambda d:d['result'][0].update(results=[{'read_probe':1.0}]),
                       lambda d:d['result'][0].update(results=[{'read_probe':1,'private':CANARY}]),
                       lambda d:d['result'][0].update(meta={}),lambda d:d['result'][0]['meta'].update(changed_db=True),
                       lambda d:d['result'][0]['meta'].update(changes=1),lambda d:d['result'][0]['meta'].update(rows_written=1),
                       lambda d:d['result'][0]['meta'].update(changes=False),lambda d:d['result'][0]['meta'].update(rows_written=0.0)):
            data=envelope();mutate(data);cases.append(data)
        cases += [[],{},None,{'success':1,'errors':[],'result':[]}]
        for data in cases:
            with self.subTest(data_type=type(data).__name__),patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(probe,'urlopen',return_value=response(payload=json.dumps(data).encode())):
                with self.assertRaises(core.BackupError) as caught:probe.run(BINDING)
                self.assertIn('HTTP=200',core.safe_failure(caught.exception))
                self.assertNotIn(CANARY,core.safe_failure(caught.exception))

    def test_json_poison_encoding_content_type_and_huge_response_fail_closed(self):
        for payload,content_type in [(CANARY.encode(),'application/json'),(b'<html>PRIVATE_CANARY</html>','text/html'),
                                     (json.dumps(envelope()).encode(),'text/html'),(b'\xff','application/json'),
                                     (b'{"success":false,"success":true}','application/json'),
                                     (b'{"success":true,"value":NaN}','application/json'),
                                     (b'['*1000+b']'*1000,'application/json'),
                                     (b'x'*(probe.MAX_RESPONSE+1),'application/json')]:
            reply=response(payload=payload,content_type=content_type)
            with patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(probe,'urlopen',return_value=reply):
                with self.assertRaises(core.BackupError) as caught:probe.run(BINDING)
                kind='RESPONSE_LIMIT' if len(payload)>probe.MAX_RESPONSE else 'RESPONSE_INVALID'
                self.assertEqual(core.safe_failure(caught.exception),f'FAILED stage=D1_READ_PROBE class={kind} HTTP=200')
                reply.read.assert_called_once_with(probe.MAX_RESPONSE+1)

    def test_network_timeout_and_stream_abort_never_log_raw_details(self):
        for error,kind in [(TimeoutError(CANARY),'TIMEOUT'),(URLError(TimeoutError(CANARY)),'TIMEOUT'),
                           (URLError(CANARY),'NETWORK_ERROR'),(OSError(CANARY),'NETWORK_ERROR')]:
            with patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(probe,'urlopen',side_effect=error):
                with self.assertRaises(core.BackupError) as caught:probe.run(BINDING)
                self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=D1_READ_PROBE class='+kind)
        reply=response();reply.read.side_effect=OSError(CANARY)
        with patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(probe,'urlopen',return_value=reply):
            with self.assertRaises(core.BackupError) as caught:probe.run(BINDING)
            self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=D1_READ_PROBE class=NETWORK_ERROR')
            reply.__exit__.assert_called_once()

    def test_error_body_abort_and_html_do_not_hide_http_status(self):
        for content in (b'<html>'+CANARY.encode()+b'</html>',b'',json.dumps({'errors':[{'code':10000,'message':CANARY}]}).encode()):
            error=HTTPError('https://private.invalid',403,CANARY,{'Content-Type':'text/html'},io.BytesIO(content))
            with patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(probe,'urlopen',side_effect=error):
                with self.assertRaises(core.BackupError) as caught:probe.run(BINDING)
                self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=D1_READ_PROBE class=AUTH_DENIED HTTP=403')
        broken=Mock();broken.read.side_effect=TimeoutError(CANARY)
        error=HTTPError('https://private.invalid',403,CANARY,{'Content-Type':'application/json'},broken)
        with patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(probe,'urlopen',side_effect=error):
            with self.assertRaises(core.BackupError) as caught:probe.run(BINDING)
            self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=D1_READ_PROBE class=AUTH_DENIED HTTP=403')
            broken.close.assert_called_once()

    def test_missing_secret_invalid_identity_and_alternate_base_url_cannot_redirect(self):
        for binding,change in [({**BINDING,'account_id':'bad'},{}),({**BINDING,'database_id':'bad'},{}),
                               (BINDING,{'CLOUDFLARE_API_TOKEN':''}),({**BINDING,'jurisdiction':'weur'},{})]:
            with patch.dict(os.environ,{**PROBE_ENV,**change},clear=True),patch.object(probe,'urlopen') as network:
                with self.assertRaises(core.BackupError):probe.run(binding)
                network.assert_not_called()
        with patch.dict(os.environ,{**PROBE_ENV,'CLOUDFLARE_API_BASE_URL':'https://private.invalid'},clear=True),patch.object(probe,'urlopen',return_value=response()) as network:
            probe.run(BINDING)
            self.assertTrue(network.call_args.args[0].full_url.startswith('https://api.cloudflare.com/'))
        self.assertIsNone(probe.backup_preflight.NoRedirect().redirect_request(Mock(),Mock(),307,CANARY,{},'https://private.invalid'))

    def test_new_probe_classes_do_not_expand_existing_export_classification(self):
        error=core.BackupError(CANARY,stage='WRANGLER_EXPORT',failure_class='RATE_LIMIT',http=429)
        self.assertEqual(core.safe_failure(error),'FAILED stage=WRANGLER_EXPORT class=UNKNOWN')
        error=core.BackupError(CANARY,stage=probe.STAGE,failure_class=CANARY,http=403,cf_codes=[CANARY,True,10000])
        self.assertEqual(core.safe_failure(error),'FAILED stage=D1_READ_PROBE class=UNKNOWN HTTP=403 CF=10000')


class ReadProbeOperationTests(unittest.TestCase):
    def test_identity_gets_precede_exactly_one_select_no_backup_or_key(self):
        order=[]
        def get(request,**kwargs):
            order.append('GET');self.assertEqual(request.method,'GET')
            return response(data=listed() if '?' in request.full_url else detail())
        def post(request,**kwargs):order.append('POST');return response()
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{**PROBE_ENV,'RUNNER_TEMP':tmp},clear=True),patch.object(probe.backup_preflight,'urlopen',side_effect=get),patch.object(probe,'urlopen',side_effect=post),patch.object(ci,'backup') as backup,patch.object(ci,'recovery') as recovery,patch.object(core,'publish') as publish,patch.object(ci,'quiet') as child,patch.object(probe.backup_preflight,'tools_available') as tools,contextlib.redirect_stdout(io.StringIO()) as out:
            ci.main(['read-probe']);self.assertEqual(order,['GET','GET','POST'])
            self.assertEqual(out.getvalue(),'VERIFIED stage=D1_READ_PROBE HTTP=200\n')
            for blocked in (backup,recovery,publish,child,tools):blocked.assert_not_called()
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_main_manual_repo_and_independent_confirmation_before_any_network(self):
        for change in ({'GITHUB_EVENT_NAME':'push'},{'GITHUB_REF':'feature'},{'GITHUB_REPOSITORY':'other/repo'},
                       {'BACKUP_CONFIRMATION':'EXPORT_EXISTING_KMN'},{'BACKUP_CONFIRMATION':'DIAGNOSE_EXISTING_KMN'},
                       {'BACKUP_CONFIRMATION':'BACKUP_READ_ONLY_KMN'},{'BACKUP_CONFIRMATION':''}):
            with patch.dict(os.environ,{**PROBE_ENV,**change},clear=True),patch.object(ci,'remote_verify') as verify,patch.object(probe,'run') as run:
                with self.assertRaises(core.BackupError):ci.main(['read-probe'])
                verify.assert_not_called();run.assert_not_called()

    def test_failed_identity_never_posts_and_probe_never_falls_back_to_export(self):
        for replies in ([listed([])],[listed(),detail(jurisdiction='weur')],[listed(),detail(uuid='wrong')]):
            with patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(probe.backup_preflight,'get',side_effect=replies),patch.object(probe,'urlopen') as post,patch.object(ci,'export_sql') as export:
                with self.assertRaises(core.BackupError):ci.main(['read-probe'])
                post.assert_not_called();export.assert_not_called()
        with patch.dict(os.environ,PROBE_ENV,clear=True),patch.object(ci,'remote_verify'),patch.object(probe,'run',side_effect=probe.failure('AUTH_DENIED',http=403)),patch.object(ci,'export_sql') as export:
            with self.assertRaises(core.BackupError):ci.main(['read-probe'])
            export.assert_not_called()

    def test_no_backup_readonly_choice_and_successful_probe_is_not_recovery_provenance(self):
        with patch.object(probe,'urlopen') as network,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):ci.main(['backup-readonly'])
            network.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{**PROBE_ENV,'D1_BACKUP_PASSPHRASE':KEY,'MAINTENANCE_CONFIRMATION':'OWNER_CONFIRMED_MAINTENANCE'},clear=True),patch.object(ci,'backup') as backup:
            with self.assertRaises(core.BackupError):ci.main(['backup','--publish-dir',tmp+'/out'])
            backup.assert_not_called()
        from datetime import datetime, timezone
        run={'id':123,'conclusion':'success','event':'workflow_dispatch','head_branch':'main',
             'repository':{'full_name':ci.REPO},'path':ci.WORKFLOW,'head_sha':'b'*40,'created_at':datetime.now(timezone.utc).isoformat()}
        with patch.object(ci,'github_get',side_effect=[run,{'artifacts':[]}]):
            with self.assertRaisesRegex(core.BackupError,'ARTIFACT_UNAVAILABLE'):ci.source_run('123')

    def test_workflow_separate_environment_no_key_upload_tools_or_automatic_trigger(self):
        workflow=(ROOT/ci.WORKFLOW).read_text()
        job=workflow.split('  read-probe:')[1].split('  diagnose:')[0]
        self.assertIn('environment: cloudflare-backup',job)
        for gate in ('workflow_dispatch','refs/heads/main','READ_ONLY_PROBE_KMN'):self.assertIn(gate,job)
        for forbidden in ('D1_BACKUP_PASSPHRASE','MAINTENANCE_CONFIRMATION','upload-artifact','wrangler','setup-node','npm','kmn-ciphertext','backup-readonly'):self.assertNotIn(forbidden,job)
        self.assertIn('secrets.CLOUDFLARE_BACKUP_API_TOKEN',job)
        self.assertIn('permissions:\n  contents: read',workflow)
        self.assertIn('workflow_dispatch:',workflow)
        self.assertNotIn('schedule:',workflow);self.assertNotIn('pull_request:',workflow)
        self.assertNotIn('backup-readonly',workflow)

    def test_cli_errors_show_only_trusted_fields_and_never_write_files(self):
        for code in (200,403):
            with tempfile.TemporaryDirectory() as tmp:
                payload=envelope() if code==200 else {'success':False,'errors':[{'code':10000,'message':CANARY}]}
                program=(
                    'import sys,runpy;sys.path.insert(0,'+repr(str(ROOT/'cloudflare/scripts'))+');'
                    'import backup_preflight as p,d1_read_probe as q;from unittest.mock import Mock;'
                    'p.verify=lambda binding:None;r=Mock();r.status='+str(code)+';r.headers={"Content-Type":"application/json"};'
                    'r.read.return_value='+repr(json.dumps(payload).encode())+';'
                    'r.__enter__=Mock(return_value=r);r.__exit__=Mock(return_value=False);'
                    'q.urlopen=lambda *args,**kwargs:r;sys.argv=["d1_backup_ci.py","read-probe"];'
                    'runpy.run_path('+repr(str(ROOT/'cloudflare/scripts/d1_backup_ci.py'))+',run_name="__main__")'
                )
                result=subprocess.run([sys.executable,'-c',program],env={**PROBE_ENV,'PATH':os.defpath,'RUNNER_TEMP':tmp},capture_output=True,text=True,timeout=10)
                expected=('VERIFIED stage=D1_READ_PROBE HTTP=200\n' if code==200 else 'FAILED stage=D1_READ_PROBE class=AUTH_DENIED HTTP=403 CF=10000\n')
                self.assertEqual(result.returncode,0 if code==200 else 1)
                self.assertEqual(result.stdout+result.stderr,expected)
                for private in (CANARY,KEY,BINDING['database_id'],probe.SQL,PROBE_ENV['CLOUDFLARE_API_TOKEN']):self.assertNotIn(private,result.stdout+result.stderr)
                self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_fixed_select_never_reads_private_rows_or_mutates_schema_versions(self):
        for version in (2,3):
            with sqlite3.connect(':memory:') as db:
                for name in core.MIGRATIONS[:version]:db.executescript((ROOT/'cloudflare/migrations'/name).read_text())
                db.executescript('CREATE TABLE private_fixture(a TEXT,b INTEGER,c BLOB,d REAL,e TEXT,PRIMARY KEY(a,b)) WITHOUT ROWID;')
                db.execute('INSERT INTO private_fixture VALUES(?,?,?,?,?)',('quotes\'\n\x00🔒',2**63-1,b'\x00\xff',0.1,None))
                before=list(db.iterdump());reads=[]
                def authorize(action,table,*_):
                    if action==sqlite3.SQLITE_READ:reads.append(table)
                    if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK
                db.set_authorizer(authorize)
                self.assertEqual(db.execute(probe.SQL).fetchall(),[(1,)])
                db.set_authorizer(None)
                self.assertTrue(set(reads)<= {'sqlite_master','sqlite_schema'})
                self.assertEqual(list(db.iterdump()),before)
