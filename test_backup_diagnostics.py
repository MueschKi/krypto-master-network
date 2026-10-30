"""Offline regression tests: no production credentials, sockets or D1 rows."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError
from test_d1_backup import ci, core, BINDING, ROOT, KEY, ORIGIN
import backup_preflight as pre

CANARY = 'PRIVATE_FIXTURE_CANARY https://signed.invalid/?token=secret SELECT private'
ENV = {'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main',
       'GITHUB_REPOSITORY':ci.REPO,'GITHUB_RUN_ID':'123','GITHUB_SHA':'b'*40,
       'CLOUDFLARE_ACCOUNT_ID':BINDING['account_id'],'KMN_D1_DATABASE_ID':BINDING['database_id'],
       'CLOUDFLARE_API_TOKEN':'synthetic_'+'x'*32,'BACKUP_CONFIRMATION':'DIAGNOSE_EXISTING_KMN'}


def response(data):
    result = Mock(); result.status = 200; result.read.return_value = json.dumps(data).encode()
    result.__enter__ = Mock(return_value=result); result.__exit__ = Mock(return_value=False)
    return result


def listed(items=None):
    return {'success':True,'result':items if items is not None else [{'name':'kmn','uuid':BINDING['database_id']}],
            'result_info':{'page':1,'total_pages':1}}


def detail(**change):
    return {'success':True,'result':{'name':'kmn','uuid':BINDING['database_id'],'jurisdiction':'eu',**change}}


class SafeDiagnosticsTests(unittest.TestCase):
    def test_all_stages_render_only_allowlisted_fields(self):
        self.assertEqual(len(core.STAGES),14)
        for stage in core.STAGES:
            with self.subTest(stage=stage):
                with self.assertRaises(core.BackupError) as raised:
                    with core.at_stage(stage): raise RuntimeError(CANARY)
                self.assertEqual(core.safe_failure(raised.exception),'FAILED stage='+stage+(' class=UNKNOWN' if stage in ('WRANGLER_EXPORT', 'D1_READ_PROBE') else ''))
        for error in (RuntimeError(CANARY),core.BackupError(CANARY),core.BackupError(CANARY,stage=CANARY)):
            self.assertEqual(core.safe_failure(error),'FAILED stage=ENV_CONTEXT')
        error=core.BackupError(CANARY,stage='D1_LIST',http=403,cf_codes=[10000,'secret',True,{},-1,999999999])
        self.assertEqual(core.safe_failure(error),'FAILED stage=D1_LIST HTTP=403 CF=10000')
        self.assertEqual(core.safe_failure(core.BackupError(CANARY,stage='SQL_IMPORT',http=403)),'FAILED stage=SQL_IMPORT')

    def test_http_denials_numeric_codes_only_for_all_get_stages(self):
        for stage in ('ENV_CONTEXT','D1_LIST','D1_DETAIL_EU'):
            for status in (401,403):
                payload={'errors':[{'code':10000,'message':CANARY},{'code':CANARY},{'code':True}]}
                error=HTTPError('https://private.invalid',status,CANARY,{},io.BytesIO(json.dumps(payload).encode()))
                with patch.dict(os.environ,ENV,clear=True),patch.object(pre,'urlopen',side_effect=error):
                    with self.assertRaises(core.BackupError) as caught:pre.get('/user/tokens/verify',stage)
                self.assertEqual(core.safe_failure(caught.exception),f'FAILED stage={stage} HTTP={status} CF=10000')

    def test_unknown_json_oversize_and_stream_abort_are_safe(self):
        for payload in (b'not json '+CANARY.encode(),b'[]',b'{}',b'x'*(pre.LIMIT+1)):
            reply=response({});reply.read.return_value=payload
            with patch.dict(os.environ,ENV,clear=True),patch.object(pre,'urlopen',return_value=reply):
                with self.assertRaises(core.BackupError) as caught:pre.get('/user/tokens/verify','ENV_CONTEXT')
                self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=ENV_CONTEXT HTTP=200')
        reply=response({});reply.read.side_effect=OSError(CANARY)
        with patch.dict(os.environ,ENV,clear=True),patch.object(pre,'urlopen',return_value=reply):
            with self.assertRaises(core.BackupError) as caught:pre.get('/user/tokens/verify','ENV_CONTEXT')
            self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=ENV_CONTEXT')

    def test_exact_identity_and_jurisdiction_fail_closed(self):
        cases=[([listed([])],'D1_LIST'),([listed([{'name':'kmn','uuid':'wrong'}])],'D1_LIST'),
               ([listed(),detail(uuid='wrong')],'D1_DETAIL_EU'),([listed(),detail(jurisdiction='weur')],'D1_DETAIL_EU'),
               ([listed(),detail(jurisdiction=None)],'D1_DETAIL_EU'),([listed(),detail(name='other')],'D1_DETAIL_EU'),
               ([{'success':True,'result':{},'result_info':{}}],'D1_LIST')]
        for replies,stage in cases:
            with patch.dict(os.environ,ENV,clear=True),patch.object(pre,'get',side_effect=replies):
                with self.assertRaises(core.BackupError) as caught:pre.verify(BINDING)
                self.assertEqual(core.safe_failure(caught.exception),'FAILED stage='+stage)

    def test_pagination_never_silently_accepts_duplicate(self):
        first=listed();first['result_info']['total_pages']=2
        second=listed();second['result_info']={'page':2,'total_pages':2}
        with patch.dict(os.environ,ENV,clear=True),patch.object(pre,'get',side_effect=[first,second]):
            with self.assertRaises(core.BackupError):pre.verify(BINDING)

    def test_diagnose_only_gets_and_never_exports_encrypts_uploads(self):
        requests=[]
        def fake(request,**kwargs):
            requests.append(request)
            self.assertEqual(request.method,'GET'); self.assertIsNone(request.data)
            if request.full_url.endswith('/verify'):return response({'success':True,'result':{'status':'active'}})
            if '?' in request.full_url:return response(listed())
            return response(detail())
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{**ENV,'RUNNER_TEMP':tmp},clear=True),patch.object(pre,'urlopen',side_effect=fake),patch.object(pre,'tools_available'),patch.object(ci,'export_sql') as export,patch.object(core,'pack') as pack,patch.object(core,'publish') as publish,contextlib.redirect_stdout(io.StringIO()) as output:
            ci.main(['diagnose']);self.assertEqual(list(Path(tmp).iterdir()),[])
            export.assert_not_called();pack.assert_not_called();publish.assert_not_called()
        self.assertEqual(len(requests),3);self.assertNotIn(CANARY,output.getvalue())

    def test_diagnose_gates_and_missing_secrets_before_network(self):
        for change in ({'BACKUP_CONFIRMATION':''},{'GITHUB_REF':'feature'},{'GITHUB_EVENT_NAME':'push'},
                       {'CLOUDFLARE_API_TOKEN':''},{'KMN_D1_DATABASE_ID':'wrong'},{'CLOUDFLARE_ACCOUNT_ID':''}):
            with patch.dict(os.environ,{**ENV,**change},clear=True),patch.object(pre,'urlopen') as network:
                with self.assertRaises(core.BackupError):ci.main(['diagnose'])
                network.assert_not_called()

    def test_export_interrupt_empty_and_restore_failures_classified(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(ci,'remote_verify'),patch.object(ci,'quiet',side_effect=TimeoutError(CANARY)):
            with self.assertRaises(core.BackupError) as caught:ci.export_sql(BINDING,tmp)
            self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=WRANGLER_EXPORT class=UNKNOWN')
        with tempfile.TemporaryDirectory() as tmp,patch.object(ci,'remote_verify'),patch.object(ci,'quiet'):
            with self.assertRaises(core.BackupError) as caught:ci.export_sql(BINDING,tmp)
            self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=EXPORT_EMPTY')
        for decrypt,stage in ((False,'GPG_ENCRYPT'),(True,'GPG_DECRYPT')):
            with tempfile.TemporaryDirectory() as tmp,patch.object(core.subprocess,'run',side_effect=OSError(CANARY)):
                with self.assertRaises(core.BackupError) as caught:core.gpg(Path(tmp)/'source',Path(tmp)/'target',KEY,tmp,decrypt=decrypt)
                self.assertEqual(core.safe_failure(caught.exception),'FAILED stage='+stage)

    def test_workflow_diagnose_separate_no_secret_or_debug_artifact(self):
        workflow=(ROOT/ci.WORKFLOW).read_text();job=workflow.split('  diagnose:')[1].split('  backup:')[0]
        for required in ('cloudflare-backup','workflow_dispatch','refs/heads/main','DIAGNOSE_EXISTING_KMN','if: always()'):self.assertIn(required,job)
        for forbidden in ('upload-artifact','D1_BACKUP_PASSPHRASE','--remote','deploy','d1 export'):self.assertNotIn(forbidden,job)
        self.assertIn('FAILED stage=ARTIFACT_UPLOAD',workflow)
        self.assertNotIn('ACTIONS_STEP_DEBUG',workflow)

    def test_wrapper_version_check_never_receives_credentials(self):
        version=json.loads((ROOT/'cloudflare/package-lock.json').read_text())['packages']['node_modules/wrangler']['version']
        def run(command,**kwargs):
            for key in ('CLOUDFLARE_API_TOKEN','D1_BACKUP_PASSPHRASE','GH_TOKEN'):self.assertNotIn(key,kwargs['env'])
            return subprocess.CompletedProcess(command,0,version,'')
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,ENV,clear=True),patch.object(pre.subprocess,'run',side_effect=run):pre.tools_available(tmp)

    def test_real_local_failure_sites_use_correct_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'bad.sql';source.write_text('not SQL '+CANARY)
            calls=[('SQL_IMPORT',lambda:core.import_sql(source,root/'db')),
                   ('SCHEMA_MISMATCH',lambda:core.summary(root/'empty.sqlite')),
                   ('ARTIFACT_LIMIT',lambda:core.recover(root/'missing','0'*64,root,BINDING,ORIGIN,KEY)),
                   ('ARTIFACT_UPLOAD',lambda:core.publish(root/'missing',root/'out')),
                   ('SECRET_FORMAT',lambda:core.identity('invalid','invalid'))]
            for stage,call in calls:
                with self.assertRaises(core.BackupError) as caught:call()
                self.assertEqual(core.safe_failure(caught.exception),'FAILED stage='+stage)
        with tempfile.TemporaryDirectory() as tmp,patch.object(core,'import_sql'),patch.object(core,'summary',side_effect=core.BackupError(CANARY,stage='RESTORE_PARITY')):
            with self.assertRaises(core.BackupError) as caught:core.pack('synthetic',tmp,BINDING,ORIGIN,KEY)
            self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=RESTORE_PARITY')

    def test_wrapper_failure_and_inactive_token_are_safe(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(pre.subprocess,'run',side_effect=OSError(CANARY)):
            with self.assertRaises(core.BackupError) as caught:pre.tools_available(tmp)
            self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=ENV_CONTEXT')
        with patch.object(pre,'get',return_value={'result':{'status':'disabled','message':CANARY}}):
            with self.assertRaises(core.BackupError) as caught:pre.token_status()
            self.assertEqual(core.safe_failure(caught.exception),'FAILED stage=ENV_CONTEXT')

    def test_export_consent_is_required_even_with_automatic_confirmation_flag(self):
        env={**ENV,'D1_BACKUP_PASSPHRASE':KEY,'BACKUP_CONFIRMATION':'EXPORT_EXISTING_KMN',
             'MAINTENANCE_CONFIRMATION':'OWNER_CONFIRMED_MAINTENANCE'}
        for change in ({'BACKUP_CONFIRMATION':'DIAGNOSE_EXISTING_KMN'},{'MAINTENANCE_CONFIRMATION':''}):
            with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{**env,**change},clear=True),patch.object(ci,'export_sql') as export:
                with self.assertRaises(core.BackupError):ci.main(['backup','--publish-dir',tmp+'/out'])
                export.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp,patch.object(ci,'remote_verify'):
            def fake(command,**kwargs):
                self.assertIn('--skip-confirmation',command)
                Path(command[-1]).write_text('synthetic')
            with patch.object(ci,'quiet',side_effect=fake):ci.export_sql(BINDING,tmp)

    def test_http_redirects_cannot_forward_authorization(self):
        self.assertIsNone(pre.NoRedirect().redirect_request(Mock(),Mock(),302,CANARY,{},'https://evil.invalid'))

    def test_documented_total_count_pagination_and_unknown_metadata(self):
        first=listed([]); first['result_info']={'page':1,'per_page':1,'total_count':2}
        second=listed(); second['result_info']={'page':2,'per_page':1,'total_count':2}
        with patch.dict(os.environ,ENV,clear=True),patch.object(pre,'get',side_effect=[first,second,detail()]):pre.verify(BINDING)
        first['result_info']={'page':1}
        with patch.dict(os.environ,ENV,clear=True),patch.object(pre,'get',return_value=first):
            with self.assertRaises(core.BackupError):pre.verify(BINDING)
