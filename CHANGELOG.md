# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-25

### Security (breaking behavior changes)
- **Fixed critical vault unlock flaw**: the gateway previously used the config
  field `keyring_account` (default `"vault"`) directly as the decryption
  password and never read the system keychain. The gateway now resolves the
  password via `DV_VAULT_PASSWORD` env → system keychain → interactive prompt,
  and **refuses to start** with no password source. There is no default password.
- **Audit logging is now disabled by default** (opt-in via `audit.enabled=true`).
  Audit logs are a second copy of request metadata and should be a conscious choice.
- Added `VaultStore.verify_password()`: wrong passwords are rejected at startup
  and in every `dv vault` command instead of failing later at decrypt time.
- `dv start` now warns when binding to anything other than `127.0.0.1`.

### Added
- `dv vault save-password`: store the vault password in the system keychain
  (requires `pip install dataveil[keychain]`).
- `SECURITY.md`: explicit threat model, limitations, and safe-usage guidance.
- README "Security & Limitations" section.

### Fixed
- `dv init` no longer claims to support Cursor/Codex auto-configuration; it
  configures Claude Code and clearly marks other tools as manual-setup-only.
  Backups and the restore script now only cover files actually modified.
- Replaced template `yourname/dataveil` links with the real repository URL.
- Removed README references to a `dv audit query` CLI that does not exist yet.

## [0.1.0] - 2026-07-23

### Added
- **Vault**: AES-256-GCM encrypted API key storage with Argon2id key derivation
- **Privacy Engine**: Code-aware PII detection (internal domains, API keys, SQL connection strings, JWT, SSH keys, .env files)
- **Semantic Placeholders**: Replace sensitive data with `<TYPE_N>` tokens that preserve LLM context understanding
- **SSE Stream Rehydration**: Real-time restoration of original data in streaming responses
- **Gateway**: FastAPI proxy with OpenAI ↔ Anthropic format conversion
- **CLI**: `dv vault add/list/rm`, `dv start/stop/status`, `dv init`
- **Config System**: YAML config, environment variable override, project-level `.dataveilrc`
- **Audit Logging**: Daily rotation, 30-day retention, API key scrubbing, query interface
- **Sync Engine**: Incremental upload with client-side encryption (OSS/S3/COS/MinIO)
- **MCP Server**: Native Claude Code integration with 4 tools (privacy_scan, privacy_redact, vault_status, vault_add_profile)
- **Custom Rules**: YAML DSL for user-defined detection patterns
- **Docker**: Multi-stage Dockerfile, docker-compose.yml, health checks
- **CI/CD**: GitHub Actions (pytest, ruff, mypy, Docker build, PyPI release)
- **Performance**: Vault config TTL cache, httpx connection pooling, `/health` and `/metrics` endpoints
- **Tests**: 53 tests covering unit, integration, and E2E scenarios

### Security
- All API keys encrypted at rest with AES-256-GCM
- Key derivation via Argon2id (time_cost=3, memory_cost=64MB, parallelism=4)
- Client-side encryption before OSS upload
- Audit log scrubbing to prevent secondary leakage

[0.1.0]: https://github.com/JediKinght9527/dataveil/releases/tag/v0.1.0
