# DataVeil

[![CI](https://github.com/yourname/dataveil/workflows/CI/badge.svg)](https://github.com/yourname/dataveil/actions)
[![Coverage](https://codecov.io/gh/yourname/dataveil/branch/main/graph/badge.svg)](https://codecov.io/gh/yourname/dataveil)
[![PyPI version](https://badge.fury.io/py/dataveil.svg)](https://badge.fury.io/py/dataveil)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Privacy-first local gateway for LLM APIs.** Protect your sensitive data before it leaves your machine.

![DataVeil Demo](docs/images/demo.gif)

## Why DataVeil?

Every time you paste code into Claude Code, Cursor, or ChatGPT, you might be leaking:
- Internal company domains (`internal-api.company.com`)
- API keys and secrets (`sk-live-...`)
- Customer data in comments (`// TODO: fix for client ABC`)
- SQL connection strings (`mysql://user:pass@host/db`)
- SSH private keys and JWT tokens

**DataVeil sits between your AI tools and LLM providers**, automatically detecting and replacing sensitive data with semantic placeholders — so your secrets never leave your machine.

## Features

- 🔒 **Zero Key Exposure**: All LLM API keys encrypted locally. Tools never hold the real key.
- 🧠 **Code-Aware Detection**: Recognizes SQL connection strings, JWT tokens, SSH keys, `.env` variables, internal URLs — not just generic PII.
- 💬 **Context-Preserving**: Replaces secrets with semantic placeholders (`<INTERNAL_DOMAIN_1>`, `<API_KEY_1>`) so LLMs still understand your code.
- 🌊 **Stream Rehydration**: Real-time restoration of original data in SSE streaming responses.
- 🔌 **Multi-Provider**: Works with Kimi, OpenAI, Anthropic, Azure OpenAI via a single local endpoint.
- 📊 **Audit Logging**: Request-level logs with daily rotation and optional OSS sync for compliance.
- 🛠️ **Plugin-First**: Claude Code skill, MCP server, VS Code extension (coming soon).
- ⚙️ **Custom Rules**: Define your own detection patterns with YAML DSL.

## Quick Start

### Installation

```bash
pip install dataveil
```

### One-Command Setup

```bash
# Initialize DataVeil for your tools
dv init
```

This will:
1. Detect installed AI tools (Claude Code, Cursor, Codex)
2. Backup your current configuration
3. Point your tools to `http://localhost:8787` (DataVeil gateway)
4. Remove API keys from tool configs (they're now in DataVeil's encrypted vault)

### Manual Setup (if you prefer)

**Step 1: Add your API key to the encrypted vault**

```bash
dv vault add --profile work --provider kimi
# Enter your API key when prompted
# Create a vault password (remember this!)
```

**Step 2: Start the gateway**

```bash
dv start
# 🔒 DataVeil Gateway starting at http://127.0.0.1:8787
```

**Step 3: Configure your tool**

<details>
<summary><b>Claude Code</b></summary>

Edit `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8787",
    "ANTHROPIC_MODEL": "kimi-k2.6"
  }
}
```

Remove `ANTHROPIC_AUTH_TOKEN` — DataVeil holds it now.
</details>

<details>
<summary><b>Cursor</b></summary>

Edit Cursor settings → Models → OpenAI API Base:

```
http://127.0.0.1:8787/v1
```

Leave API Key empty.
</details>

<details>
<summary><b>Codex CLI</b></summary>

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
export OPENAI_API_KEY=""  # Leave empty
```
</details>

## How It Works

```
Your Prompt
    ↓
[DataVeil] Detects: "email me at marco@company.com"
    ↓
[DataVeil] Replaces: "email me at <EMAIL_1>"
    ↓
LLM Provider (sees only placeholders)
    ↓
[DataVeil] Rehydrates: "email me at marco@company.com"
    ↓
You see the original, unredacted response
```

**The LLM never sees your real data. You never lose context.**

## Advanced Usage

### Custom Detection Rules

Create `~/.dataveil/rules.yaml`:

```yaml
rules:
  - name: internal-project
    pattern: "PROJECT_[A-Z]+"
    entity_type: internal_project
    confidence: 0.9
    description: "Internal project codenames"

  - name: customer-name
    pattern: "(?:Acme|Globex|Initech)\\s+(?:Corp|Inc|Ltd)"
    entity_type: customer_name
    confidence: 0.95
```

### Team Sync (Pro)

Sync your encrypted vault and audit logs to OSS for team collaboration:

```yaml
# ~/.dataveil/config.yaml
sync:
  enabled: true
  provider: aliyun-oss
  bucket: my-team-vault
  endpoint: oss-cn-hangzhou.aliyuncs.com
  access_key: ${OSS_ACCESS_KEY}
  secret_key: ${OSS_SECRET_KEY}
  encrypt: true
  interval_seconds: 300
```

### Audit Queries

```bash
# View recent requests
dv audit query --limit 10

# Filter by status code
dv audit query --status 500

# Export to OSS
dv audit sync
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Your Tools (Claude Code / Cursor / Codex / VS Code)       │
│  → http://localhost:8787                                    │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  DataVeil Gateway (FastAPI)                                 │
│  ├─ Privacy Engine: Detect → Replace → Rehydrate           │
│  ├─ Vault: AES-256-GCM encrypted key storage               │
│  └─ Audit: Structured logging with rotation                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  LLM Providers (Kimi / OpenAI / Anthropic / Azure)         │
│  → Sees only semantic placeholders                          │
└─────────────────────────────────────────────────────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design.

## FAQ

<details>
<summary><b>Does DataVeil slow down my requests?</b></summary>

Typical overhead is 5-15ms per request (detection + replacement). Streaming responses add negligible latency. Run `python scripts/benchmark.py` to measure on your machine.
</details>

<details>
<summary><b>What if the placeholder confuses the LLM?</b></summary>

Our semantic placeholders (`<EMAIL_1>`, `<API_KEY_1>`) are designed to preserve context. LLMs understand these as "an email address" or "an API key". In rare cases, you can switch to `strict` mode which uses generic `[REDACTED]` instead.
</details>

<details>
<summary><b>Is my vault password safe?</b></summary>

Yes. Your password is never stored. It's used to derive an encryption key via Argon2id (memory-hard, GPU-resistant). Even if someone steals your `vault.db`, they can't decrypt it without your password.
</details>

<details>
<summary><b>Can I use DataVeil with my own LLM?</b></summary>

Yes! Any OpenAI-compatible or Anthropic-compatible API works. Just add your provider's base URL and API key to the vault.
</details>

<details>
<summary><b>What data does DataVeil collect?</b></summary>

Nothing. DataVeil runs entirely on your machine. Audit logs are stored locally (or in your own OSS bucket if you enable sync). We have no servers, no telemetry, no tracking.
</details>

## Roadmap

- [x] Core gateway with privacy engine
- [x] Encrypted vault with multi-profile support
- [x] CLI and MCP server for Claude Code
- [x] Docker deployment
- [x] CI/CD with automated testing
- [ ] **VS Code / Cursor extension** (in progress)
- [ ] **Web dashboard** for audit visualization
- [ ] **Rust core** for 10x performance
- [ ] **Team collaboration** (shared vault, RBAC)
- [ ] **More providers** (Gemini, Groq, local models via Ollama)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Areas we need help:
- More detection rules (Go, Rust, Java-specific secrets)
- IDE plugins (VS Code, JetBrains)
- Documentation and tutorials
- Performance optimization (Rust core)

## License

[MIT](LICENSE) — use it anywhere, for anything.

## Acknowledgments

- Inspired by [Microsoft Presidio](https://github.com/microsoft/presidio) and [CloakPipe](https://github.com/rohansx/cloakpipe)
- Built with [FastAPI](https://fastapi.tiangolo.com/), [cryptography](https://cryptography.io/), and [argon2-cffi](https://argon2-cffi.readthedocs.io/)

---

**Made with ❤️ for developers who care about privacy.**
