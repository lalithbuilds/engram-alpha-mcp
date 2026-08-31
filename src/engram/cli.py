import argparse
import sys
import os
from pathlib import Path
from .utils import foolproof_update_json

def setup_claude_desktop():
    if os.name == 'nt':
        config_path = Path(os.environ.get('APPDATA', '')) / 'Claude' / 'claude_desktop_config.json'
    else:
        config_path = Path.home() / 'Library' / 'Application Support' / 'Claude' / 'claude_desktop_config.json'
        
    def updater(data):
        if not isinstance(data.get("mcpServers"), dict):
            data["mcpServers"] = {}
        data["mcpServers"]["engram-mcp"] = {
            "command": sys.executable,
            "args": ["-m", "engram.server"],
            "env": {
                "PATH": os.environ.get("PATH", "")
            }
        }
        
    try:
        foolproof_update_json(str(config_path), updater)
        print("✅ Successfully configured Claude Desktop.")
        print(f"Path modified: {config_path}")
        print("Please restart Claude Desktop to apply changes.")
    except Exception as e:
        print(f"❌ Failed to setup Claude Desktop: {e}")

def main():
    parser = argparse.ArgumentParser(description="Engram MCP CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    setup_parser = subparsers.add_parser("setup", help="Auto-configure Claude Desktop")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup_claude_desktop()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
