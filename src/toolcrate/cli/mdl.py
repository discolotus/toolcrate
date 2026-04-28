"""Small built-in metadata utility used as ToolCrate's mdl-tool fallback."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydub.utils import mediainfo


def read_metadata(path: Path) -> Dict[str, Any]:
    info = mediainfo(str(path))
    tags = info.get("TAG", {}) if isinstance(info.get("TAG"), dict) else {}
    return {
        "path": str(path),
        "format": info.get("format_name"),
        "duration": info.get("duration"),
        "bit_rate": info.get("bit_rate"),
        "sample_rate": info.get("sample_rate"),
        "channels": info.get("channels"),
        "tags": tags,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ToolCrate metadata utility")
    parser.add_argument(
        "files",
        nargs="*",
        help="Audio files to inspect. The `info` subcommand is accepted for compatibility.",
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    args = parser.parse_args(argv)

    files = args.files
    if files and files[0] == "info":
        files = files[1:]

    if not files:
        parser.error("at least one audio file is required")

    results = []
    for file_name in files:
        path = Path(file_name).expanduser()
        if not path.exists():
            raise SystemExit(f"file not found: {path}")
        results.append(read_metadata(path))

    indent = 2 if args.pretty else None
    payload = results[0] if len(results) == 1 else results
    print(json.dumps(payload, indent=indent, sort_keys=args.pretty))
    return 0


if __name__ == "__main__":
    sys.exit(main())
