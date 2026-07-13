"""Edge Agent CLI — interact with a running agent via HTTP."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


def _agent_url() -> str:
    cfg_path = Path.home() / ".edge-agent" / "config.yaml"
    raw = {}
    if cfg_path.exists():
        import yaml
        raw = yaml.safe_load(cfg_path.read_text()) or {}
        cfg_path2 = Path(raw.get("data_dir", str(Path.home() / ".edge-agent"))) / "agent.yaml"
        if cfg_path2.exists():
            raw2 = yaml.safe_load(cfg_path2.read_text()) or {}
            raw.update(raw2)
    return f"http://localhost:{raw.get('port', 8420)}"


def _api(path: str, method: str = "GET", body: dict | None = None) -> dict:
    base = _agent_url()
    url = f"{base}/api{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection failed: {e.reason}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args: argparse.Namespace) -> None:
    data = _api("/status")
    print(json.dumps(data, indent=2))


def cmd_health(args: argparse.Namespace) -> None:
    data = _api("/health")
    print(json.dumps(data, indent=2))


def cmd_config_get(args: argparse.Namespace) -> None:
    data = _api("/config")
    if args.key:
        print(data.get(args.key, ""))
    else:
        print(json.dumps(data, indent=2))


def cmd_config_set(args: argparse.Namespace) -> None:
    result = _api("/config", method="PUT", body={"config": {args.key: args.value}})
    print(json.dumps(result, indent=2))


def cmd_scan(args: argparse.Namespace) -> None:
    result = _api("/scan", method="POST", body={"file_id": args.file_id})
    print(json.dumps(result, indent=2))


def cmd_sync(args: argparse.Namespace) -> None:
    result = _api("/sync", method="POST")
    print(json.dumps(result, indent=2))


def cmd_pause(args: argparse.Namespace) -> None:
    result = _api("/agent/pause", method="POST")
    print(json.dumps(result, indent=2))


def cmd_resume(args: argparse.Namespace) -> None:
    result = _api("/agent/resume", method="POST")
    print(json.dumps(result, indent=2))


def cmd_metrics(args: argparse.Namespace) -> None:
    data = _api("/metrics")
    print(json.dumps(data, indent=2))


def cmd_files(args: argparse.Namespace) -> None:
    path = f"/files?limit={args.limit}"
    if args.status:
        path += f"&status={args.status}"
    data = _api(path)
    print(json.dumps(data, indent=2))


def cmd_folders(args: argparse.Namespace) -> None:
    data = _api("/folders")
    print(json.dumps(data, indent=2))


def cmd_logs(args: argparse.Namespace) -> None:
    path = f"/logs?limit={args.limit}"
    if args.level:
        path += f"&level={args.level}"
    data = _api(path)
    for entry in data:
        print(f"[{entry.get('level','')}] {entry.get('message','')}")


def cmd_capabilities(args: argparse.Namespace) -> None:
    data = _api("/capabilities")
    print(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge Agent CLI")
    sub = parser.add_subparsers(dest="command")

    p_status = sub.add_parser("status", help="Show agent status")
    p_status.set_defaults(func=cmd_status)

    p_health = sub.add_parser("health", help="Check agent health")
    p_health.set_defaults(func=cmd_health)

    p_config = sub.add_parser("config", help="Get or set config")
    p_config.add_argument("action", choices=["get", "set"])
    p_config.add_argument("key", nargs="?")
    p_config.add_argument("value", nargs="?")
    p_config.set_defaults(func=lambda a: cmd_config_get(a) if a.action == "get" and not a.key else cmd_config_set(a) if a.action == "set" else cmd_config_get(a))

    p_scan = sub.add_parser("scan", help="Scan a file by ID")
    p_scan.add_argument("file_id")
    p_scan.set_defaults(func=cmd_scan)

    p_sync = sub.add_parser("sync", help="Trigger sync to SaaS")
    p_sync.set_defaults(func=cmd_sync)

    p_pause = sub.add_parser("pause", help="Pause job processing")
    p_pause.set_defaults(func=cmd_pause)

    p_resume = sub.add_parser("resume", help="Resume job processing")
    p_resume.set_defaults(func=cmd_resume)

    p_metrics = sub.add_parser("metrics", help="Show agent metrics")
    p_metrics.set_defaults(func=cmd_metrics)

    p_files = sub.add_parser("files", help="List files")
    p_files.add_argument("--status")
    p_files.add_argument("--limit", type=int, default=50)
    p_files.set_defaults(func=cmd_files)

    p_folders = sub.add_parser("folders", help="List folders")
    p_folders.set_defaults(func=cmd_folders)

    p_logs = sub.add_parser("logs", help="Show recent logs")
    p_logs.add_argument("--level")
    p_logs.add_argument("--limit", type=int, default=50)
    p_logs.set_defaults(func=cmd_logs)

    p_cap = sub.add_parser("capabilities", help="Show agent capabilities")
    p_cap.set_defaults(func=cmd_capabilities)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
