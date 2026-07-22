# DataVeil Architecture

## Overview

DataVeil is a **local privacy gateway** that sits between your AI tools and LLM providers. It ensures sensitive data never leaves your machine in plaintext.

## Layered Design

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Privacy Engine                                     │
│  - Detect: Regex + NER + Code-Aware patterns                 │
│  - Tokenize: Semantic placeholders                           │
│  - Rehydrate: Stream restoration                             │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Gateway                                            │
│  - FastAPI HTTP proxy                                        │
│  - Multi-provider routing                                    │
│  - SSE streaming support                                     │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Vault                                              │
│  - AES-256-GCM encrypted key storage                         │
│  - Argon2id password derivation                              │
│  - Multi-profile (Work/Personal/Team)                        │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User Input
    ↓
[Privacy Engine] Detect & Replace → <PLACEHOLDER_N>
    ↓
[Gateway] Forward to LLM provider with encrypted key
    ↓
LLM Response (SSE stream)
    ↓
[Privacy Engine] Rehydrate placeholders → Original data
    ↓
User sees clean response
```

## Module Breakdown

### `dv/gateway/`
FastAPI application handling HTTP proxying. Single catch-all route forwards requests to configured upstream LLM providers.

### `dv/privacy/`
- `detector.py`: Multi-layer entity recognition
- `tokenizer.py`: Semantic placeholder generation
- `rehydrator.py`: SSE/JSON stream restoration
- `rules/`: Pluggable detection rules

### `dv/vault/`
- `crypto.py`: Argon2id + AES-256-GCM primitives
- `store.py`: SQLite-backed encrypted storage
- `profile.py`: Multi-profile key management

### `dv/audit/`
Structured JSON Lines logging with optional OSS export.

### `dv/cli/`
Command-line interface for vault management and gateway control.

### `dv/mcp/`
Model Context Protocol server for native Claude Code integration.

## Security Model

1. **At Rest**: All keys encrypted with AES-256-GCM, key derived from user password via Argon2id.
2. **In Transit**: TLS to upstream providers (their responsibility).
3. **In Memory**: Keys only decrypted during active requests, not logged.
4. **Audit**: Request metadata logged, payloads optionally scrubbed.

## Roadmap

- [x] MVP: Local gateway + vault + basic privacy engine
- [ ] VS Code / Cursor extension
- [ ] Team vault with OSS sync
- [ ] Rust core rewrite for performance
- [ ] Enterprise: SSO, RBAC, SIEM integration
