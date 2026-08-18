"""CLI entry point: python -m codegraph.ingest <repo_path>

Prints all symbols as a JSON array to stdout.
"""
import dataclasses
import json
import sys
from pathlib import Path

from .walker import ingest_repo


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m codegraph.ingest <repo_path>", file=sys.stderr)
        sys.exit(1)

    repo = Path(sys.argv[1])
    if not repo.is_dir():
        print(f"Error: {repo} is not a directory", file=sys.stderr)
        sys.exit(1)

    symbols = ingest_repo(repo)
    print(json.dumps([dataclasses.asdict(s) for s in symbols], indent=2))


if __name__ == "__main__":
    main()
