#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

LIST_SPLIT_PATTERN = re.compile(r"\s*,\s*")
NUMBERED_PREFIX_PATTERN = re.compile(r"^\d+\.\s*")
PAREN_ALIAS_PATTERN = re.compile(r"^(?P<main>.+?)\((?P<alias>.+?)\)$")


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


def build_question_id(unit_id: str, part: str, offset: int) -> str:
    return f"{unit_id}:{part}:{offset}"


def parse_markdown_blocks(content: str) -> tuple[list[dict[str, object]], list[str], str | None]:
    lines = content.splitlines()

    items: list[dict[str, object]] = []
    warnings: list[str] = []
    title: str | None = None
    current_prompts: list[str] = []
    current_answers: list[str] = []
    source_line = 1
    active_prompt_index: int | None = None

    def flush_block() -> None:
        nonlocal current_prompts, current_answers, source_line, active_prompt_index
        if not current_prompts and not current_answers:
            return
        if current_prompts and current_answers:
            items.append(
                {
                    "rawPrompts": current_prompts.copy(),
                    "rawAnswers": current_answers.copy(),
                    "sourceLine": source_line,
                }
            )
        elif current_prompts:
            warnings.append(f"Line {source_line}: prompts without answer")
        else:
            warnings.append(f"Line {source_line}: answers without prompts")
        current_prompts = []
        current_answers = []
        active_prompt_index = None

    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            flush_block()
            continue

        if line.startswith("#") and title is None:
            title = line.lstrip("#").strip()
            continue

        if line.startswith("*"):
            if not current_prompts and not current_answers:
                source_line = index
            elif current_answers:
                flush_block()
                source_line = index
            current_prompts.append(line.lstrip("*").strip())
            active_prompt_index = len(current_prompts) - 1
            continue

        if line.startswith("->"):
            if not current_prompts and not current_answers:
                source_line = index
            current_answers.append(line[2:].strip())
            active_prompt_index = None
            continue

        if active_prompt_index is not None and current_prompts:
            current_prompts[active_prompt_index] = f"{current_prompts[active_prompt_index]} {line}".strip()
        elif current_answers:
            current_answers[-1] = f"{current_answers[-1]} {line}".strip()
        else:
            warnings.append(f"Line {index}: ignored line '{line}'")

    flush_block()
    return items, warnings, title


def clean_answer(answer: str) -> str:
    answer = NUMBERED_PREFIX_PATTERN.sub("", answer.strip())
    return re.sub(r"\s+", " ", answer)


def extract_aliases(answers: list[str]) -> list[str]:
    aliases: list[str] = []
    for answer in answers:
        match = PAREN_ALIAS_PATTERN.match(answer)
        if match:
            aliases.append(match.group("alias").strip())
    return aliases


def extract_keywords(answers: list[str]) -> list[str]:
    keywords: list[str] = []
    for answer in answers:
        pieces = LIST_SPLIT_PATTERN.split(answer)
        if len(pieces) > 1:
            keywords.extend(piece for piece in pieces if piece)
        else:
            keywords.append(answer)
    return keywords


def main() -> None:
    args = parse_args()

    repo_root = Path(args.repo_root).resolve()
    changed_files = read_changed_files(Path(args.changed_files_file))

    documents = []
    questions = []
    snapshot_hasher = hashlib.sha256()

    for file_path in iter_note_files(repo_root):
        relative_path = file_path.relative_to(repo_root).as_posix()
        content = file_path.read_text(encoding="utf-8")
        content_hash = sha256_text(content)
        parts = Path(relative_path).parts
        unit_id = parts[0] if len(parts) >= 2 else ""
        part = Path(relative_path).stem
        parsed_items, warnings, parsed_title = parse_markdown_blocks(content)
        title = parsed_title or extract_title(content, part)

        snapshot_hasher.update(relative_path.encode("utf-8"))
        snapshot_hasher.update(b"\0")
        snapshot_hasher.update(content_hash.encode("utf-8"))
        snapshot_hasher.update(b"\0")

        documents.append(
            {
                "documentId": relative_path,
                "unitId": unit_id,
                "part": part,
                "title": title,
                "sourcePath": relative_path,
            }
        )

        for offset, item in enumerate(parsed_items, start=1):
            answers = [clean_answer(answer) for answer in item["rawAnswers"] if str(answer).strip()]
            question_type = "list_answer" if len(answers) > 1 else "short_answer"
            questions.append(
                {
                    "questionId": build_question_id(unit_id, part, offset),
                    "unitId": unit_id,
                    "part": part,
                    "title": title,
                    "type": question_type,
                    "prompts": [prompt.strip() for prompt in item["rawPrompts"] if str(prompt).strip()],
                    "answers": answers,
                    "aliases": extract_aliases(answers),
                    "keywords": extract_keywords(answers),
                    "warnings": warnings,
                    "sourcePath": relative_path,
                    "sourceLine": item["sourceLine"],
                }
            )

    snapshot_key = snapshot_hasher.hexdigest()

    payload = {
        "manifest": {
            "bundleVersion": args.commit_sha,
            "sourceCommit": args.commit_sha,
            "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "contentHash": f"sha256:{snapshot_key}",
        },
        "documents": documents,
        "questions": questions,
    }

    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
