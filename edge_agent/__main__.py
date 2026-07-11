"""Edge Agent entry point for sidecar binary.

Supports:
    api --port 8420     Start HTTP API server (used by Tauri sidecar)
    cli [args...]       Run CLI commands
"""

from __future__ import annotations

import argparse
import logging
import sys


def start_api(port: int) -> None:
    from edge_agent.api.server import create_app

    app = create_app()

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    parser = argparse.ArgumentParser(description="Edge Agent")
    sub = parser.add_subparsers(dest="command")

    api_parser = sub.add_parser("api", help="Start the HTTP API server")
    api_parser.add_argument("--port", type=int, default=8420, help="Port to bind")

    cli_parser = sub.add_parser("cli", help="Run CLI commands (pass through)")
    cli_parser.add_argument("args", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.command == "api":
        start_api(args.port)
    elif args.command == "cli":
        sys.argv = ["edge-agent"] + args.args
        from edge_agent.cli import main as cli_main
        cli_main()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
