"""MCP Server for native Claude Code integration."""
from __future__ import annotations

from typing import Any


class DataVeilMCPServer:
    """Model Context Protocol server exposing DataVeil tools."""

    def __init__(self, vault, engine):
        self.vault = vault
        self.engine = engine

    def tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "privacy_scan",
                "description": "Scan text for sensitive entities",
                "inputSchema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            },
            {
                "name": "vault_status",
                "description": "Check vault status and profiles",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    def call_tool(self, name: str, arguments: dict) -> dict:
        if name == "privacy_scan":
            text = arguments.get("text", "")
            replaced, mapping = self.engine.process(text)
            return {
                "entities_found": len(mapping),
                "replaced": replaced,
                "mapping": mapping,
            }
        if name == "vault_status":
            return {
                "profiles": self.vault.list_profiles(),
            }
        return {"error": f"Unknown tool: {name}"}
