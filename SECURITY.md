# Security Policy

## Project Maturity

**DataVeil is early-stage software (v0.2.x).** It has not received a third-party
security audit. Do not treat it as a production-grade security boundary for
company code or real customer data until you have reviewed it yourself.

## Threat Model — What DataVeil Does and Does Not Protect

### What it helps with

- Reducing **accidental leakage** of sensitive strings (API keys, internal
  domains, connection strings, emails, phone numbers) inside prompts sent to
  LLM providers.
- Keeping provider API keys **out of tool configs**: keys live in an encrypted
  local vault (AES-256-GCM, Argon2id-derived key) instead of plaintext
  `settings.json` files.

### What it does NOT do

- **It cannot make an untrusted upstream trustworthy.** If you route traffic
  through a third-party relay/gateway you do not control, DataVeil only reduces
  what that relay sees — it does not make the relay safe. Keys already exposed
  to such a relay should be considered compromised and rotated.
- **Regex/rule-based detection is not exhaustive.** Novel formats, encoded
  secrets, or sensitive information expressed in prose can pass through
  undetected. Conversely, false positives can redact context the model needs.
- **It does not protect data already on disk** (shell history, env files, git
  history). Use `gitleaks`, pre-commit secret scanning, and `.env` hygiene
  alongside DataVeil, not instead of them.
- **The gateway process holds decrypted keys in memory** while running. Anyone
  who can execute code as your user can read them. Bind to `127.0.0.1` only
  (the default) and do not expose the port.

## Defaults Chosen for Safety

| Setting | Default | Rationale |
|---|---|---|
| Bind address | `127.0.0.1` | Never exposed beyond the local machine |
| Audit logging | **disabled** | Logs are a second copy of request metadata; opt-in only |
| OSS/S3 sync | **disabled** | Off-machine copies raise compliance stakes; opt-in only |
| Vault password | **no default** | Gateway refuses to start without env var / keychain / prompt |

## Vault Password Resolution

The gateway resolves the vault password in this order and **fails closed**:

1. `DV_VAULT_PASSWORD` environment variable
2. System keychain (stored via `dv vault save-password`, requires `pip install keyring`)
3. Interactive prompt (`dv start` in a terminal)
4. Otherwise: refuses to start. There is no default password.

## Recommendations Before Using with Sensitive Data

1. Read the ~1.5k lines of core code (`dv/vault`, `dv/privacy`, `dv/gateway`).
2. Keep audit logging and OSS sync disabled unless you need them.
3. Keep the gateway on `127.0.0.1`.
4. Layer defenses: pre-commit secret scanning (gitleaks), `.gitignore` for
   `.env`, and manual review of prompts containing customer identifiers.
5. Rotate any key that was ever configured in plaintext in a tool config.

## Reporting a Vulnerability

Please open a [GitHub Security Advisory](https://github.com/JediKinght9527/dataveil/security/advisories/new)
or a private issue. Do not disclose publicly until a fix is released.
