// Execute only extracted functions from the locked bundle in a VM without
// process/require/fetch. No CLI invocation, network, or database export.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const base = new URL('../', import.meta.url);
const pkg = JSON.parse(readFileSync(new URL('node_modules/wrangler/package.json', base)));
assert.equal(pkg.version, '4.156.0', 'Review the contract on a Wrangler upgrade');
const source = readFileSync(new URL('node_modules/wrangler/wrangler-dist/cli.js', base), 'utf8');
function section(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a);
  assert.ok(a >= 0 && b > a, 'Pinned source markers must exist');
  return source.slice(a, b);
}
let requests = [], exports = 0;
const config = { account_id: 'a'.repeat(32), d1_databases: [{ binding: 'DB', database_name: 'kmn', database_id: '12345678-1234-4234-8234-123456789abc' }] };
const context = vm.createContext({
  __name: x => x, __name2: x => x,
  DEFAULT_MIGRATION_TABLE: 'd1_migrations',
  hasUuid: db => Boolean(db?.uuid),
  oauthFlow: { isTemporaryAllowed: () => false, getActiveTemporaryAccount: () => undefined },
  loginOrRefreshIfRequired2: async () => ({ loggedIn: true }),
  validateAccountId: id => id,
  descriptor: { getConfigFileLabel: () => 'config' },
  fetchAllAccounts2: () => { throw new Error('Unexpected account lookup'); },
  fetchResult2: async (_config, resource, init) => {
    assert.equal(resource, `/accounts/${config.account_id}/d1/database/${config.d1_databases[0].database_id}/export`);
    assert.equal(init.method, 'POST');
    requests.push(JSON.parse(init.body));
    return { success: true, status: requests.length === 1 ? 'pending' : 'complete',
      messages: [], at_bookmark: 'synthetic-bookmark' };
  },
  fs14: { statSync: () => undefined },
  createCommand: command => command,
  exportRemotely: async (...args) => { exports++; assert.equal(args[1], 'kmn'); },
  confirm2: () => { throw new Error('Unexpected interactive prompt'); },
});
vm.runInContext(section('  function getActiveAccountId(config2)', '  __name(getActiveAccountId,'), context, { timeout: 1000 });
vm.runInContext(section('  async function getOrSelectAccountId2(config2)', '  __name(getOrSelectAccountId2,'), context, { timeout: 1000 });
vm.runInContext(section('  async function requireAuth2(config2)', '  __name(requireAuth2,'), context, { timeout: 1000 });
vm.runInContext(section('function getDatabaseInfoFromConfig(config2', 'var getDatabaseByNameOrBinding,'), context, { timeout: 1000 });
vm.runInContext('var getDatabaseByNameOrBinding;\n' + section('    getDatabaseByNameOrBinding =', '    getDatabaseInfoFromIdOrName2 ='), context, { timeout: 1000 });
vm.runInContext(section('async function pollExport(', 'var import_undici24,'), context, { timeout: 1000 });
vm.runInContext('var d1ExportCommand;\n' + section('    d1ExportCommand = createCommand({', '    __name(exportLocal,'), context, { timeout: 1000 });
assert.equal(await context.requireAuth2(config), config.account_id);
const db = await context.getDatabaseByNameOrBinding(config, config.account_id, 'kmn');
assert.equal(db.uuid, config.d1_databases[0].database_id);
assert.equal(requests.length, 0, 'UUID binding must avoid REST lookup');
assert.equal(context.d1ExportCommand.args['skip-confirmation'].type, 'boolean');
await context.d1ExportCommand.handler({ remote:true, name:'kmn', output:'synthetic.sql', schema:true, data:true, skipConfirmation:true }, { config });
assert.equal(exports, 1);
const dump = { no_schema:false, no_data:false, tables:[] };
await context.pollExport({}, config, config.account_id, db, dump, undefined);
assert.equal(requests.length, 2);
assert.equal(requests[0].output_format, 'polling');
assert.equal(requests[0].current_bookmark, undefined);
assert.equal(requests[1].current_bookmark, 'synthetic-bookmark');
assert.deepEqual(requests[0].dump_options, dump);
console.log('Wrangler 4.156.0 offline export contract: OK');
