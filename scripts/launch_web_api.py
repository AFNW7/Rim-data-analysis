from __future__ import annotations

import argparse
from pathlib import Path

from rim_data_analysis.web_api import run_web_api


def main() -> int:
    parser = argparse.ArgumentParser(prog="rim-analysis-web-api")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    return run_web_api(host=args.host, port=args.port, repo_root=Path.cwd())


if __name__ == "__main__":
    raise SystemExit(main())
