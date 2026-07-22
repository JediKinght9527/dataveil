# DataVeil

Privacy-first local gateway for LLM APIs. Protect your sensitive data before it leaves your machine.

## Features

- **Zero Key Exposure**: All LLM API keys are encrypted locally. Your tools (Claude Code, Cursor, Codex) never hold the real key.
- **Code-Aware PII Detection**: Automatically detects internal domains, API keys, project names, and personal information in prompts.
- **Transparent Replacement**: Replaces sensitive data with semantic placeholders (`<INTERNAL_DOMAIN_1>`, `<API_KEY_1>`) so LLMs still understand context.
- **Stream Rehydration**: Real-time restoration of original data in SSE streaming responses.
- **Multi-Provider**: Works with Kimi, OpenAI, Anthropic, Azure OpenAI via a single local endpoint.
- **Audit Logging**: Optional request-level audit logs with OSS sync for team compliance.

## Quick Start

```bash
# Install
pip install dataveil

# Add your API key to the encrypted vault
dv vault add --profile work --provider kimi

# Start the gateway
dv start

# Point your tool to http://localhost:8787/v1
# No API key needed in tool config!
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design.

## License

MIT
