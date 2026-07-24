"""MCP Server for native Claude Code integration."""
from __future__ import annotations

from typing import Any

from dv.privacy.engine import PrivacyEngine
from dv.vault.store import VaultStore


class DataVeilMCPServer:
    """Model Context Protocol server exposing DataVeil tools."""

    def __init__(self, vault: VaultStore, engine: PrivacyEngine):
        self.vault = vault
        self.engine = engine

    def tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "privacy_scan",
                "description": "Scan text for sensitive entities (PII, API keys, internal domains, etc.)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to scan for sensitive entities",
                        }
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "privacy_redact",
                "description": "Redact sensitive entities from text, replacing them with semantic placeholders",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to redact",
                        }
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "vault_status",
                "description": "Check DataVeil vault status, list profiles, and verify connectivity",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "vault_add_profile",
                "description": "Add a new encrypted API key profile to the vault",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "profile": {"type": "string", "description": "Profile name"},
                        "provider": {"type": "string", "description": "Provider (kimi/openai/anthropic)"},
                        "base_url": {"type": "string", "description": "API base URL"},
                        "api_key": {"type": "string", "description": "API key to encrypt"},
                    },
                    "required": ["profile", "provider", "base_url", "api_key"],
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict) -> dict:
        if name == "privacy_scan":
            return self._privacy_scan(arguments)
        if name == "privacy_redact":
            return self._privacy_redact(arguments)
        if name == "vault_status":
            return self._vault_status()
        if name == "vault_add_profile":
            return self._vault_add_profile(arguments)
        return {"error": f"Unknown tool: {name}"}

    def _privacy_scan(self, args: dict) -> dict:
        text = args.get("text", "")
        entities = self.engine.detector.detect(text)
        return {
            "entities_found": len(entities),
            "entities": [
                {
                    "type": e.entity_type,
                    "text": e.text,
                    "confidence": e.confidence,
                    "start": e.start,
                    "end": e.end,
                }
                for e in entities
            ],
        }

    def _privacy_redact(self, args: dict) -> dict:
        text = args.get("text", "")
        replaced, mapping = self.engine.process(text)
        return {
            "original_length": len(text),
            "redacted_length": len(replaced),
            "entities_redacted": len(mapping),
            "redacted_text": replaced,
            "mapping": mapping,
        }

    def _vault_status(self) -> dict:
        profiles = self.vault.list_profiles()
        return {
            "vault_path": str(self.vault.db_path),
            "profiles_count": len(profiles),
            "profiles": profiles,
            "status": "ready" if profiles else "empty",
        }

    def _vault_add_profile(self, args: dict) -> dict:
        profile = args["profile"]
        provider = args["provider"]
        base_url = args["base_url"]
        api_key = args["api_key"]
        self.vault.add_key(profile, provider, base_url, api_key)
        return {
            "status": "success",
            "profile": profile,
            "provider": provider,
            "message": f"Profile '{profile}' added to vault",
        }


# MCP Protocol handler (stdio/JSON-RPC)
class MCPProtocolHandler:
    """Handle MCP JSON-RPC messages over stdio."""

    def __init__(self, server: DataVeilMCPServer):
        self.server = server

    def handle_message(self, message: dict) -> dict:
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})

        if method == "initialize":
            return self._result(msg_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "dataveil", "version": "0.1.0"},
            })
        if method == "tools/list":
            return self._result(msg_id, {"tools": self.server.tools()})
        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = self.server.call_tool(tool_name, arguments)
            return self._result(msg_id, {"content": [{"type": "text", "text": str(result)}]})
        if method == "notifications/initialized":
            return None  # No response needed

        return self._error(msg_id, -32601, f"Method not found: {method}")

    def _result(self, msg_id: Any, result: Any) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def _error(self, msg_id: Any, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}
