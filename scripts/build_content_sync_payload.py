#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a repository snapshot payload for active-recall content sync."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--before-sha", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--changed-files-file", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def iter_note_files(repo_root: Path) -> list[Path]:
    note_files: list[Path] = []
    for unit_dir in sorted(repo_root.glob("unit_*")):
        if not unit_dir.is_dir():
            continue
        note_files.extend(sorted(path for path in unit_dir.rglob("*.md") if path.is_file()))
    return note_files


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_changed_files(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title
    return fallback


def main() -> None:
    args = parse_args()

    repo_root = Path(args.repo_root).resolve()
    changed_files = read_changed_files(Path(args.changed_files_file))

    documents = []
    snapshot_hasher = hashlib.sha256()

    for file_path in iter_note_files(repo_root):
        relative_path = file_path.relative_to(repo_root).as_posix()
        content = file_path.read_text(encoding="utf-8")
        content_hash = sha256_text(content)
        parts = Path(relative_path).parts
        unit_id = parts[0] if len(parts) >= 2 else ""
        part_id = Path(relative_path).stem
        title = extract_title(content, part_id)

        snapshot_hasher.update(relative_path.encode("utf-8"))
        snapshot_hasher.update(b"\0")
        snapshot_hasher.update(content_hash.encode("utf-8"))
        snapshot_hasher.update(b"\0")

        documents.append(
            {
                "path": relative_path,
                "unitId": unit_id,
                "partId": part_id,
                "title": title,
                "content": content,
                "contentSha256": content_hash,
            }
        )

    payload = {
        "source": args.source,
        "repository": args.repository,
        "ref": args.ref,
        "commitSha": args.commit_sha,
        "beforeSha": args.before_sha,
        "snapshotVersion": args.commit_sha,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "changedFiles": changed_files,
        "documentCount": len(documents),
        "documents": documents,
        "metadata": {
            "runId": args.run_id,
            "runAttempt": args.run_attempt,
            "actor": args.actor,
        },
        "snapshotKey": snapshot_hasher.hexdigest(),
    }

    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
