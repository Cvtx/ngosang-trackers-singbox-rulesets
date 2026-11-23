# SPDX-License-Identifier: GPL-2.0-only
"""Build .srs files for every trackers_*.txt list in an upstream checkout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from tracker_rules import make_rule_set


def run_compile(binary: str, json_path: Path, srs_path: Path) -> None:
    command = [binary, "rule-set", "compile", "--output", str(srs_path), str(json_path)]
    print("+", " ".join(command))
    subprocess.run(command, check=True)
    if not srs_path.is_file() or srs_path.stat().st_size == 0:
        raise RuntimeError(f"Sing-box did not produce a valid file: {srs_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-dir", required=True, type=Path)
    parser.add_argument("--upstream-sha", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--sing-box", default="sing-box")
    args = parser.parse_args()

    upstream_dir = args.upstream_dir.resolve()
    repo_root = args.repo_root.resolve()
    upstream_files = sorted(upstream_dir.glob("trackers_*.txt"))
    if not upstream_files:
        raise SystemExit("No trackers_*.txt lists found in upstream checkout")

    staging = Path(tempfile.mkdtemp(prefix=".ruleset-build-", dir=repo_root))
    stats: dict[str, dict] = {}
    try:
        staged_sources = staging / "sources"
        staged_json = staging / "source-json"
        staged_rulesets = staging / "rulesets"
        for directory in (staged_sources, staged_json, staged_rulesets):
            directory.mkdir(parents=True)

        for source_path in upstream_files:
            name = source_path.stem
            raw = source_path.read_bytes()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise RuntimeError(f"{source_path.name} is not valid UTF-8") from exc

            rule_set, counts = make_rule_set(text.splitlines())
            json_path = staged_json / f"{name}.json"
            srs_path = staged_rulesets / f"{name}.srs"
            (staged_sources / source_path.name).write_bytes(raw)
            json_path.write_text(
                json.dumps(rule_set, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            run_compile(args.sing_box, json_path, srs_path)
            stats[source_path.name] = {
                **counts,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "srs_bytes": srs_path.stat().st_size,
            }
            print(
                f"{name}: {counts['unique_domains']} domains, "
                f"{counts['unique_ip_addresses']} IPs, {counts['compiled_rules']} rules"
            )

        # Replace generated directories only after every source has compiled.
        for directory_name, staged_directory in (
            ("sources", staged_sources),
            ("source-json", staged_json),
            ("rulesets", staged_rulesets),
        ):
            target = repo_root / directory_name
            backup = staging / f"old-{directory_name}"
            if target.exists():
                target.rename(backup)
            staged_directory.rename(target)
            if backup.exists():
                shutil.rmtree(backup)

        manifest = {
            "source_repository": "https://github.com/ngosang/trackerslist",
            "source_branch": "master",
            "source_commit": args.upstream_sha,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "sing_box_version": subprocess.run(
                [args.sing_box, "version"],
                check=False,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "lists": stats,
        }
        (repo_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    print(f"Built {len(stats)} Sing-box rule sets successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
