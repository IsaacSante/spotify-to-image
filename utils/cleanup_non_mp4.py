#!/usr/bin/env python3
"""
cleanup_non_mp4.py

Deletes all files in the given directory (or current directory if none specified)
that do not have a .mp4 extension.
"""

import sys
from pathlib import Path

def cleanup(directory: Path):
    for path in directory.iterdir():
        # only consider files (skip directories), and delete if suffix isn't .mp4
        if path.is_file() and path.suffix.lower() != ".mp4":
            try:
                path.unlink()
                print(f"Deleted: {path.name}")
            except Exception as e:
                print(f"Error deleting {path.name}: {e}", file=sys.stderr)

def main():
    # use first CLI arg as target directory, else current working directory
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    if not target.is_dir():
        print(f"Error: {target!r} is not a directory.", file=sys.stderr)
        sys.exit(1)
    cleanup(target)

if __name__ == "__main__":
    main()
