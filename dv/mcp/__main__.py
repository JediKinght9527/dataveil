"""MCP Server stdio entry point."""
import json
import sys

from dv.config import get_config
from dv.mcp.server import DataVeilMCPServer, MCPProtocolHandler
from dv.privacy.engine import PrivacyEngine
from dv.vault.store import VaultStore


def main() -> None:
    """Run MCP server over stdio."""
    config = get_config()
    vault = VaultStore(
        db_path=config.vault.path,
        password=config.vault.keyring_account,  # TODO: proper unlock
    )
    engine = PrivacyEngine()
    server = DataVeilMCPServer(vault=vault, engine=engine)
    handler = MCPProtocolHandler(server)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            response = handler.handle_message(message)
            if response:
                print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            error = handler._error(None, -32700, "Parse error")
            print(json.dumps(error), flush=True)


if __name__ == "__main__":
    main()
