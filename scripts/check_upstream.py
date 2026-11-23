# SPDX-License-Identifier: GPL-2.0-only
"""Compare all upstream trackers_*.txt files with the last published snapshot."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def upstream_commit(upstream_dir: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(upstream_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-dir", required=True, type=Path)
    parser.add_argument("--published-sources", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    upstream_files = sorted(args.upstream_dir.glob("trackers_*.txt"))
    if not upstream_files:
        raise SystemExit("No trackers_*.txt lists found in upstream checkout")

    new_hashes = {path.name: sha256(path) for path in upstream_files}
    old_hashes = {
        path.name: sha256(path)
        for path in sorted(args.published_sources.glob("trackers_*.txt"))
    }
    changed = args.force or new_hashes != old_hashes
    commit = upstream_commit(args.upstream_dir)

    lines = [
        f"changed={'true' if changed else 'false'}",
        f"upstream_sha={commit}",
        f"list_count={len(upstream_files)}",
    ]
    if args.github_output:
        args.github_output.parent.mkdir(parents=True, exist_ok=True)
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write("\n".join(lines) + "\n")

    print(f"Upstream commit: {commit}")
    print(f"Discovered lists: {len(upstream_files)}")
    print(f"Content changed: {'yes' if changed else 'no'}")
    if not changed:
        print("Skipping compilation; published tracker lists are already current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
