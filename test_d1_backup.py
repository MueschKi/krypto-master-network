"""Only local synthetic exports and fake APIs; never uses Cloudflare credentials."""
import contextlib
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT/'cloudflare/scripts'
sys.path.insert(0,str(SCRIPTS))
import encrypted_d1 as core
import d1_backup_ci as ci

BINDING = core.identity('a'*32, '12345678-1234-4234-8234-123456789abc')
ORIGIN = {'repository':ci.REPO,'run_id':'123','commit':'b'*40}
KEY = 'synthetic-local-test-passphrase-'+'x'*32


def fixture(directory, version=2):
    db = sqlite3.connect(':memory:')
    for name in core.MIGRATIONS[:version]:
        db.executescript((ROOT/'cloudflare/migrations'/name).read_text())
    db.execute('CREATE TABLE d1_migrations(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,applied_at TEXT)')
    for name in core.MIGRATIONS[:version]: db.execute("INSERT INTO d1_migrations(name,applied_at) VALUES(?,'fixture')",(name,))
    db.execute("INSERT INTO runs(id,scheduled,started,status) VALUES('one',1,1,'OK')")
    db.execute("INSERT INTO jobs(symbol,timeframe,candle_close,owner,lease_until,status) VALUES('BTC/EUR','15m',1,'one',2,'OK')")
    db.execute("INSERT INTO analyses VALUES('BTC/EUR','15m',1,1,'one','{\"synthetic\":true}')")
    db.execute("INSERT INTO coverage_gaps VALUES('BTC/EUR','15m',0,1,1,1)")
    db.execute("INSERT INTO candle_batches VALUES('BTC/EUR','15m',1,1,'[[0,1,2,1,1,1]]')")
    # Synthetic private-like canary must never be in logs or public files.
    db.execute("INSERT INTO account_snapshots VALUES('master7','fixture','hash','PRIVATE_FIXTURE_CANARY')")
    sql = Path(directory)/'export.sql'
    sql.write_text('\n'.join(db.iterdump()))
    db.close()
    return sql


class EncryptedBackupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.sql = fixture(cls.root)
        cls.cipher, cls.proof = core.pack(cls.sql,cls.root,BINDING,ORIGIN,KEY)
        cls.checksum = core.storage_snapshot.digest(cls.cipher)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_authenticated_roundtrip_and_all_tables_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = core.recover(self.cipher,self.checksum,tmp,BINDING,ORIGIN,KEY)
            self.assertEqual(proof,self.proof)
            for table in ('analyses','jobs','runs','coverage_gaps','candle_batches','account_snapshots'):
                self.assertGreater(proof['summary']['tables'][table]['rows'],0)
            self.assertEqual(core.summary(Path(tmp)/'sql-restored.sqlite'),core.summary(Path(tmp)/'snapshot-restored.sqlite'))

    def test_published_files_are_only_ciphertext_and_nonsensitive_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'published';core.publish(self.cipher,target)
            self.assertEqual({p.name for p in target.iterdir()},{'backup.tar.gz.gpg','ciphertext.sha256'})
            for p in target.iterdir():
                self.assertEqual(p.stat().st_mode&0o777,0o600)
                self.assertNotIn(b'PRIVATE_FIXTURE_CANARY',p.read_bytes())
            with self.assertRaises(core.BackupError):core.publish(self.cipher,target)

    def test_wrong_missing_key_corruption_and_hash_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i,key in enumerate(('', 'wrong'*12)):
                scratch = root/str(i);scratch.mkdir()
                with self.assertRaises(core.BackupError):core.recover(self.cipher,self.checksum,scratch,BINDING,ORIGIN,key)
                self.assertFalse((scratch/'sql-restored.sqlite').exists())
            scratch=root/'hash';scratch.mkdir()
            with self.assertRaises(core.BackupError):core.recover(self.cipher,'0'*64,scratch,BINDING,ORIGIN,KEY)
            damaged=root/'damaged.gpg';data=bytearray(self.cipher.read_bytes());data[len(data)//2]^=1;damaged.write_bytes(data)
            scratch=root/'damaged';scratch.mkdir()
            # Replacing the public checksum does not bypass GPG authentication.
            with self.assertRaises(core.BackupError):core.recover(damaged,core.storage_snapshot.digest(damaged),scratch,BINDING,ORIGIN,KEY)
            self.assertFalse((scratch/'sql-restored.sqlite').exists())

    def test_wrong_database_or_commit_is_not_recovery_evidence(self):
        for key,value in [('database_id','22345678-1234-4234-8234-123456789abc'),('jurisdiction','weur')]:
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(core.BackupError,'PROVENANCE_MISMATCH'):
                    core.recover(self.cipher,self.checksum,tmp,{**BINDING,key:value},ORIGIN,KEY)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(core.BackupError,'PROVENANCE_MISMATCH'):
                core.recover(self.cipher,self.checksum,tmp,BINDING,{**ORIGIN,'commit':'c'*40},KEY)

    def test_existing_local_restore_target_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'decrypted.tar.gz';target.write_bytes(b'keep')
            with self.assertRaises(core.BackupError):core.recover(self.cipher,self.checksum,tmp,BINDING,ORIGIN,KEY)
            self.assertEqual(target.read_bytes(),b'keep')

    def test_empty_export_wrong_schema_and_external_file_sql_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,text in enumerate(('', "ATTACH DATABASE '/tmp/forbidden-kmn.sqlite' AS other;", 'PRAGMA writable_schema=ON;')):
                source=root/f'{i}.sql';source.write_text(text)
                with self.assertRaises(core.BackupError):core.import_sql(source,root/f'{i}.sqlite')
            source=root/'schema.sql';source.write_text('CREATE TABLE unrelated(id);')
            core.import_sql(source,root/'schema.sqlite')
            with self.assertRaises(core.BackupError):core.summary(root/'schema.sqlite')

    def test_both_pre_and_post_0003_schema_versions_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sql=fixture(root,3);core.import_sql(sql,root/'three.sqlite')
            self.assertEqual(core.summary(root/'three.sqlite')['migrations'],list(core.MIGRATIONS))

    def test_internal_proof_hashes_and_table_counts_detect_manipulation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sql=fixture(root);core.import_sql(sql,root/'db.sqlite')
            before=core.summary(root/'db.sqlite')
            with sqlite3.connect(root/'db.sqlite') as db:db.execute("UPDATE analyses SET payload='tampered'")
            self.assertNotEqual(core.summary(root/'db.sqlite'),before)


class BackupOrchestrationTests(unittest.TestCase):
    def test_database_list_and_eu_must_match_before_export(self):
        with patch.object(ci.backup_preflight, 'verify', side_effect=core.BackupError('D1_LIST', stage='D1_LIST')) as verify:
            with self.assertRaises(core.BackupError): ci.remote_verify(BINDING)
            verify.assert_called_once_with(BINDING)

    def test_export_uses_exact_uuid_private_config_no_mutation_commands(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(ci,'remote_verify') as verify:
            def export(command,**kwargs):
                self.assertEqual(command[:7],['npx','--no-install','wrangler','d1','export','kmn','--remote'])
                self.assertNotIn('D1_BACKUP_PASSPHRASE',kwargs['environment'])
                config=Path(command[command.index('--config')+1]).read_text()
                self.assertIn(BINDING['database_id'],config)
                self.assertIn(BINDING['account_id'],config)
                Path(command[-1]).write_text('synthetic')
            with patch.object(ci,'quiet',side_effect=export):
                self.assertEqual(ci.export_sql(BINDING,tmp).read_text(),'synthetic')
            self.assertEqual(verify.call_count,2)

    def test_failed_export_or_failed_recovery_never_publishes(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(core,'publish') as publish:
            with patch.object(ci,'export_sql',side_effect=RuntimeError('PRIVATE_FIXTURE_CANARY')):
                with self.assertRaises(RuntimeError):ci.backup(BINDING,ORIGIN,KEY,Path(tmp)/'out',tmp)
            publish.assert_not_called()
            source=fixture(tmp)
            with patch.object(ci,'export_sql',return_value=source),patch.object(core,'pack',return_value=(source,{})),patch.object(core,'recover',side_effect=core.BackupError('RESTORE_PARITY_FAILED')):
                with self.assertRaises(core.BackupError):ci.backup(BINDING,ORIGIN,KEY,Path(tmp)/'out',tmp)
            publish.assert_not_called()

    def test_source_run_must_be_successful_manual_main_workflow_and_fresh(self):
        run={'id':123,'conclusion':'success','event':'workflow_dispatch','head_branch':'main',
             'repository':{'full_name':ci.REPO},'path':ci.WORKFLOW,'head_sha':'b'*40,
             'created_at':datetime.now(timezone.utc).isoformat()}
        artifact={'artifacts':[{'name':ci.ARTIFACT,'expired':False,'size_in_bytes':2000}]}
        with patch.object(ci,'github_get',side_effect=[run,artifact]):self.assertEqual(ci.source_run('123'),ORIGIN)
        for changed in ({'head_branch':'feature'},{'event':'pull_request'},{'conclusion':'failure'},
                        {'path':'other.yml'},{'created_at':(datetime.now(timezone.utc)-timedelta(days=8)).isoformat()}):
            with patch.object(ci,'github_get',return_value={**run,**changed}):
                with self.assertRaises(core.BackupError):ci.source_run('123')
        with patch.object(ci,'github_get',side_effect=[run,{'artifacts':[]}]):
            with self.assertRaises(core.BackupError):ci.source_run('123')

    def test_recovery_has_no_cloudflare_credentials_and_no_export(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(ci,'source_run',return_value=ORIGIN),patch.object(ci,'export_sql') as export,patch.object(core,'recover') as recover:
            def download(command,**kwargs):
                self.assertNotIn('CLOUDFLARE_API_TOKEN',kwargs['environment'])
                self.assertNotIn('D1_BACKUP_PASSPHRASE',kwargs['environment'])
                target=Path(command[-1]);(target/'backup.tar.gz.gpg').write_bytes(b'cipher')
                (target/'ciphertext.sha256').write_text('0'*64)
            with patch.dict(os.environ,{'CLOUDFLARE_API_TOKEN':'synthetic','D1_BACKUP_PASSPHRASE':KEY}),patch.object(ci,'quiet',side_effect=download):ci.recovery(BINDING,KEY,'123',tmp)
            export.assert_not_called();recover.assert_called_once()

    def test_missing_secret_consent_wrong_branch_and_temp_cleanup(self):
        environment={'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':ci.REPO,'GITHUB_RUN_ID':'123','GITHUB_SHA':'b'*40,
                     'CLOUDFLARE_ACCOUNT_ID':'a'*32,'KMN_D1_DATABASE_ID':BINDING['database_id'],
                     'BACKUP_CONFIRMATION':'EXPORT_EXISTING_KMN','MAINTENANCE_CONFIRMATION':'OWNER_CONFIRMED_MAINTENANCE',
                     'D1_BACKUP_PASSPHRASE':KEY}
        for change in ({'GITHUB_EVENT_NAME':'pull_request'},{'D1_BACKUP_PASSPHRASE':''},{'GITHUB_REF':'refs/heads/feature'},{'BACKUP_CONFIRMATION':''},{'MAINTENANCE_CONFIRMATION':''}):
            with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{**environment,**change},clear=True),patch.object(ci,'backup') as backup:
                with self.assertRaises(core.BackupError):ci.main(['backup','--publish-dir',tmp+'/out'])
                backup.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{**environment,'RUNNER_TEMP':tmp},clear=True),patch.object(ci,'backup',side_effect=RuntimeError('private')):
            with self.assertRaises(RuntimeError):ci.main(['backup','--publish-dir',tmp+'/out'])
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_workflow_is_main_manual_only_ciphertext_and_cleanup_on_failure(self):
        workflow=(ROOT/ci.WORKFLOW).read_text()
        self.assertIn('workflow_dispatch:',workflow)
        self.assertNotIn('schedule:',workflow);self.assertNotIn('pull_request:',workflow)
        self.assertIn("github.ref == 'refs/heads/main'",workflow)
        self.assertIn('retention-days: 7',workflow)
        self.assertNotIn('cache: npm',workflow)
        upload=workflow.split('uses: actions/upload-artifact@v4')[1].split('- name: Cleanup')[0]
        self.assertIn('backup.tar.gz.gpg',upload);self.assertNotIn('.sql',upload);self.assertNotIn('.sqlite',upload)
        self.assertIn('if: always()',workflow)
        recovery=workflow.split('  recovery:')[1]
        self.assertNotIn('CLOUDFLARE_API_TOKEN:',recovery)
        deploy=(ROOT/'.github/workflows/cloudflare-manual-deploy.yml').read_text()
        self.assertIn('Deployment blocked',deploy)
        self.assertNotIn('wrangler d1 migrations apply',deploy)
        self.assertNotIn('npx wrangler deploy --config',deploy)

    def test_cli_errors_never_print_private_exception_or_sql(self):
        environment={**os.environ,'GITHUB_REF':'invalid','D1_BACKUP_PASSPHRASE':KEY}
        proc=subprocess.run([sys.executable,str(SCRIPTS/'d1_backup_ci.py'),'backup'],env=environment,capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0)
        self.assertNotIn(KEY,proc.stdout+proc.stderr);self.assertNotIn('Traceback',proc.stderr)

class AdversarialEnvelopeTests(unittest.TestCase):
    def test_forged_internal_hash_or_manifest_is_rejected_after_decryption(self):
        import tarfile
        for changed in ('sql_sha256','summary','snapshot_sha256'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);source=fixture(root)
                _,proof=core.pack(source,root,BINDING,ORIGIN,KEY)
                if changed=='summary':proof['summary']['tables']['analyses']['rows']+=1
                else:proof[changed]='0'*64
                (root/'proof.json').write_text(json.dumps(proof))
                archive=root/'forged.tar.gz'
                with tarfile.open(archive,'x:gz') as tar:
                    for name in sorted(core.MEMBERS):tar.add(root/name,arcname=name)
                cipher=root/'forged.gpg';core.gpg(archive,cipher,KEY,root)
                check=root/'check';check.mkdir()
                with self.assertRaises(core.BackupError):core.recover(cipher,core.storage_snapshot.digest(cipher),check,BINDING,ORIGIN,KEY)

    def test_authenticated_archive_still_cannot_traverse_or_extract_links(self):
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'malicious.tar.gz'
            with tarfile.open(archive,'x:gz') as tar:
                item=tarfile.TarInfo('../escape');item.size=1;tar.addfile(item,io.BytesIO(b'x'))
            cipher=root/'malicious.gpg';core.gpg(archive,cipher,KEY,root)
            scratch=root/'scratch';scratch.mkdir()
            with self.assertRaises(core.BackupError):core.recover(cipher,core.storage_snapshot.digest(cipher),scratch,BINDING,ORIGIN,KEY)
            self.assertFalse((root/'escape').exists())

    def test_gpg_gets_no_key_argument_and_requires_authentication_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'cipher';source.write_bytes(b'not-real')
            def fake(command,**kwargs):
                self.assertNotIn(KEY,command)
                self.assertNotIn('D1_BACKUP_PASSPHRASE',kwargs['env'])
                self.assertEqual(kwargs['input'],(KEY+'\n').encode())
                Path(command[command.index('--output')+1]).write_bytes(b'unauthenticated')
                return subprocess.CompletedProcess(command,0,b'[GNUPG:] DECRYPTION_OKAY\n',b'')
            with patch.object(core.subprocess,'run',side_effect=fake),patch.dict(os.environ,{'D1_BACKUP_PASSPHRASE':KEY}):
                with self.assertRaises(core.BackupError):core.gpg(source,root/'plain',KEY,root,decrypt=True)
            self.assertFalse((root/'plain').exists())

class SubprocessSafetyTests(unittest.TestCase):
    def test_failed_and_aborted_subprocess_has_no_data_in_exception(self):
        for script,timeout in [("import sys; print('PRIVATE_FIXTURE_CANARY');sys.exit(1)",5),
                               ("import time;time.sleep(10)",0.05)]:
            with self.assertRaises(core.BackupError) as error:
                ci.quiet([sys.executable,'-c',script],timeout=timeout)
            self.assertNotIn('PRIVATE_FIXTURE_CANARY',str(error.exception))

    def test_empty_successful_export_still_fails_before_encryption(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(ci,'remote_verify'),patch.object(ci,'quiet'):
            with self.assertRaisesRegex(core.BackupError,'EXPORT_EMPTY'):ci.export_sql(BINDING,tmp)
