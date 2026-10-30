# Agent guide — Krypto Master Network

## Scope and deployment boundaries
This public repository contains two independent historical Python paper-trading accounts and a **read-only** Cloudflare Phase-A market observer. Do not conflate the two.

- Cloudflare source: `cloudflare/` (Wrangler `cloudflare/wrangler.toml`, D1 migrations under `cloudflare/migrations/`).
- Existing account sources: `daten/master_paper_state.json` and `daten/master_trailing_state.json` — never reset, replace or migrate to an active writer without a separately approved cutover and verification.
- Existing GitHub scheduled paper trading and MTF workflows remain active; never create a second account writer.
- No live Kraken order endpoints, no Kraken API keys and no crypto-withdrawal privileges. Live trading requires a separate explicit owner authorization and review (Issue #10); paper cloud migration is Issue #9.
- Do not add any secret, Cloudflare token, API credential, private account SQL dump or password to this public repository, logs, PRs or screenshots.
- Do not deploy Workers, execute remote D1 migrations, create Cloudflare resources, set/rotate secrets or trigger remote actions without an explicit user authorization for the specific operation. **Simply merging code does not authorize a deployment.**
- Do not upgrade or activate paid Cloudflare plans. Respect Free limits and measure production CPU use before stating it is suitable for long-term operation.

## Codex + Cloudflare environment
The user wants Codex to access their own Cloudflare account through the official Cloudflare integration. Cloudflare's current Codex guide:
https://developers.cloudflare.com/agent-setup/codex/

1. In **Codex** (not this repository), the owner installs the Cloudflare plugin via `/plugins` or the Codex desktop Plugins pane. It provides Cloudflare Skills and Cloudflare MCP servers.
2. When first prompted, the owner completes the Cloudflare **OAuth** consent flow and chooses the minimum permissions necessary for D1/Workers. Never request a token or password in a chat or PR.
3. If the plugin is unavailable, Codex CLI alternatives are `codex mcp add cloudflare --url https://mcp.cloudflare.com/mcp` and `codex mcp list`, followed by in-session `/mcp` and the user-owned OAuth login. Do not pretend to have installed user-level integrations from repository changes.
4. When working on Cloudflare, use the official `wrangler`, `workers-best-practices` and `cloudflare` skills and the connected documentation/MCP tools, if available; if not, explain the missing authorization.

## Next authorized review path
- Pull Request #12 completed Phase A and is already merged. The app has **not** been deployed to Cloudflare.
- Pull Request #13 adds an **opt-in GitHub Actions deployment path** with `validate` and `deploy`; it is separate from connecting Codex to Cloudflare.
- Before any deployment: test Python + TS + Workers/D1 fixtures, run dry-run, review D1 resource ownership, verify all paid features are disabled, and obtain a distinct explicit deployment confirmation.
- After deployment: observe actual Cloudflare Free CPU per scheduled/HTTP invocation, D1 quotas, late/missed intervals, public access controls, and real iPhone UX. Remote personal paper account snapshots must remain inaccessible until authentication hardening is separately approved.

## Tests
- Python: `python -m unittest discover -q` (repo root).
- Cloudflare: `cd cloudflare && npm ci && npm run check && npm test && npx wrangler deploy --dry-run`.
- Mobile UI: `cd cloudflare && npm run test:mobile` with Playwright browsers installed.
