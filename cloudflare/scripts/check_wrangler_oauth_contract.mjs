// Offline source extraction: never execute the bundle or its network/auth helpers.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const base = new URL('../', import.meta.url);
const pkg = JSON.parse(readFileSync(new URL('node_modules/wrangler/package.json', base)));
assert.equal(pkg.version, '4.156.0', 'Review OAuth policy on version change');
const lock = JSON.parse(readFileSync(new URL('package-lock.json', base)));
assert.equal(pkg.version, lock.packages['node_modules/wrangler'].version);
const source = readFileSync(new URL('node_modules/wrangler/wrangler-dist/cli.js', base), 'utf8');
function section(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a);
  assert.ok(a >= 0 && b > a, 'Pinned source changed: review required');
  return source.slice(a, b);
}
let calls = [], abort = false;
const ctx = vm.createContext({
  createCommand: x => x, getActiveProfile: () => 'default',
  listScopes: () => {}, sendMetricsEvent: () => {},
  CommandLineArgsError: Error,
  login: async (_config, options) => {
    calls.push(options);
    if (abort) throw new Error('synthetic authorization denied');
  },
});
vm.runInContext('var DefaultScopes;\n' + section('    DefaultScopes = {', '    DefaultScopeKeys ='), ctx, { timeout: 1000 });
vm.runInContext(section('function validateScopeKeys(scopes)', 'function getTemporaryAccountConfigFile'), ctx, { timeout: 1000 });
vm.runInContext('var oauthArgs, loginCommand;\n' + section('    oauthArgs = {', '    logoutCommand ='), ctx, { timeout: 1000 });
const { loginCommand: command, oauthArgs, DefaultScopes: scopes } = ctx;
assert.equal(command.args.device.type, 'boolean');
assert.equal(command.args.device.default, false);
assert.equal(oauthArgs.scopes.array, true);
assert.equal(oauthArgs.browser.type, 'boolean');
assert.ok(command.args['scopes-list']);
assert.ok(command.args['use-keyring']);
assert.deepEqual(Object.keys(scopes).filter(s => s.startsWith('d1:')), ['d1:write']);
assert.match(scopes['d1:write'], /See and change/);
const args = { device: true, browser: false, callbackHost: 'localhost', callbackPort: 8976 };
command.validateArgs(args);
assert.throws(() => command.validateArgs({ ...args, callbackPort: 9000 }));
assert.throws(() => command.validateArgs({ ...args, profile: 'backup' }));
await assert.rejects(command.handler({ ...args, scopes: ['d1:read'] }, { config: {} }));
assert.equal(calls.length, 0, 'Invalid scope must not start login');
// Mocked only: confirm explicit scope selection reaches the login helper unchanged.
await command.handler({ ...args, scopes: ['d1:write'] }, { config: {} });
assert.deepEqual(Array.from(calls[0].scopes), ['d1:write']);
abort = true;
await assert.rejects(command.handler({ ...args, scopes: ['d1:write'] }, { config: {} }));
assert.equal(calls.length, 2, 'No retry or scope fallback');
assert.match(section('async function requestDeviceAuthorization(', '  const headers = await buildDeviceAuthHeaders('), /offline_access/);
assert.match(source, /scopes: props\?\.scopes \?\? descriptor.getDefaultScopeKeys\(\)/);
console.log('Wrangler 4.156.0: device supported; D1 scope=d1:write; offline_access implicit; narrow export scope unavailable.');
