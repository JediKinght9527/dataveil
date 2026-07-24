# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/yourname/dataveil/releases/tag/v0.1.0
