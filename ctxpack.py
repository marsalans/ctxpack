#!/usr/bin/env python3
"""
ctxpack - Context engineering CLI tool for AI coding assistants.
Packs relevant project files into a single context bundle within a token budget.
"""

import argparse
import collections
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

NOISE_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    ".idea",
    ".vscode",
}

NOISE_FILE_EXACT = {
    "package-lock.json",
    "yarn.lock",
    "cargo.lock",
    "poetry.lock",
    "pnpm-lock.yaml",
}

GENERATED_OUTPUT_NAMES = {
    "bundle.md",
    "manifest.json",
    "ctxpack_bundle.md",
    "ctxpack_manifest.json",
}

PRIORITIZED_EXTENSIONS = {".py", ".md", ".js", ".ts", ".json", ".yaml", ".yml"}


def is_noise_file(filename: str) -> bool:
    """Check if a filename matches standard noise patterns."""
    name_lower = filename.lower()
    if name_lower in NOISE_FILE_EXACT:
        return True
    if (
        name_lower.endswith(".lock")
        or name_lower.endswith(".min.js")
        or name_lower.endswith(".min.css")
        or name_lower.endswith(".pyc")
        or name_lower.endswith(".pyo")
    ):
        return True
    return False


def tokenize_words(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    return re.findall(r"\w+", text.lower())


class CustomArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser that outputs clean one-line errors and exits with code 1."""

    def error(self, message: str) -> None:
        sys.stderr.write(f"Error: {message}\n")
        sys.exit(1)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse and validate command line arguments.
    Exit codes:
      1 - Invalid arguments (missing required flags, invalid budget, etc.)
      2 - Path error (path does not exist or is not a directory)
    """
    parser = CustomArgumentParser(
        description="ctxpack: Context engineering bundle generator",
        prog="ctxpack",
    )

    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Folder to analyze and pack",
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Description of the developer task",
    )
    parser.add_argument(
        "--budget",
        type=int,
        required=True,
        help="Maximum tokens for the entire bundle (must be positive integer)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="File path to write bundle (default: stdout)",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="File path to write JSON manifest (default: summary to stderr)",
    )

    parsed_args = parser.parse_args(args)

    # Validate budget > 0
    if parsed_args.budget <= 0:
        sys.stderr.write("Error: --budget must be a positive integer.\n")
        sys.exit(1)

    # Validate path exists and is a directory
    if not os.path.exists(parsed_args.path):
        sys.stderr.write(f"Error: Path does not exist: {parsed_args.path}\n")
        sys.exit(2)

    if not os.path.isdir(parsed_args.path):
        sys.stderr.write(f"Error: Path is not a directory: {parsed_args.path}\n")
        sys.exit(2)

    return parsed_args


def count_tokens(text: str) -> int:
    """
    Exact token counting rule per SPEC:
    tokens = math.ceil(len(text) / 4)
    """
    if not text:
        return 0
    return math.ceil(len(text) / 4)


def walk_files(
    target_path: str,
    out_file: Optional[str] = None,
    manifest_file: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Recursively inspect files under target_path using os.walk.
    Skips noise directories, noise files, and generated output files (e.g. bundle.md, manifest.json).
    Only considers readable text files (handling UTF-8 decode errors & null bytes).
    Returns (candidate_files, excluded_files) sorted deterministically by relative path.
    """
    candidates: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []

    for root, dirs, files in os.walk(target_path):
        dirs.sort()
        files.sort()

        # Identify and prune noise directories
        to_remove = []
        for d in dirs:
            if d in NOISE_DIR_NAMES or d.endswith(".egg-info"):
                full_dir_path = os.path.join(root, d)
                rel_dir_path = os.path.relpath(full_dir_path, target_path).replace(
                    "\\", "/"
                )
                excluded.append({"path": rel_dir_path, "reason": "noise directory"})
                to_remove.append(d)

        for d in to_remove:
            dirs.remove(d)

        for f in files:
            full_file_path = os.path.join(root, f)
            rel_file_path = os.path.relpath(full_file_path, target_path).replace(
                "\\", "/"
            )

            # Exclude generated output files or specified --out / --manifest files
            if (
                (out_file and rel_file_path == out_file)
                or (manifest_file and rel_file_path == manifest_file)
                or f.lower() in GENERATED_OUTPUT_NAMES
            ):
                excluded.append(
                    {"path": rel_file_path, "reason": "generated output file"}
                )
                continue

            if is_noise_file(f):
                excluded.append({"path": rel_file_path, "reason": "noise file"})
                continue

            try:
                with open(full_file_path, "r", encoding="utf-8") as file_obj:
                    content = file_obj.read()

                # Check for null bytes (binary file check)
                if "\x00" in content:
                    excluded.append(
                        {"path": rel_file_path, "reason": "binary file"}
                    )
                else:
                    tokens = count_tokens(content)
                    candidates.append(
                        {
                            "path": rel_file_path,
                            "content": content,
                            "tokens": tokens,
                        }
                    )
            except UnicodeDecodeError:
                excluded.append(
                    {"path": rel_file_path, "reason": "binary or unreadable file"}
                )
            except OSError as e:
                excluded.append(
                    {"path": rel_file_path, "reason": f"unreadable file ({e})"}
                )

    # Sort deterministically by relative path
    candidates.sort(key=lambda x: x["path"])
    excluded.sort(key=lambda x: x["path"])

    return candidates, excluded


def rank_files(candidates: List[Dict[str, Any]], task: str) -> List[Dict[str, Any]]:
    """
    Rank candidate files by relevance to task description.
    Sorts descending by score, tie-break ascending by path.
    """
    task_words = tokenize_words(task)
    task_counter = collections.Counter(task_words)

    scored_candidates = []
    for file_info in candidates:
        content_words = tokenize_words(file_info["content"])
        file_counter = collections.Counter(content_words)

        overlap_score = 0
        for word, task_freq in task_counter.items():
            if word in file_counter:
                overlap_score += min(task_freq, file_counter[word]) * 10

        depth = file_info["path"].count("/")
        depth_bonus = max(0, 10 - depth * 2)

        _, ext = os.path.splitext(file_info["path"])
        ext_bonus = 5 if ext.lower() in PRIORITIZED_EXTENSIONS else 0

        total_score = float(overlap_score + depth_bonus + ext_bonus)

        scored_item = dict(file_info)
        scored_item["score"] = total_score
        scored_candidates.append(scored_item)

    scored_candidates.sort(key=lambda x: (-x["score"], x["path"]))
    return scored_candidates


def generate_project_tree(candidates: List[Dict[str, Any]]) -> str:
    """
    Generate a clean project tree representation of candidate files for the bundle header.
    Only candidate text files considered for inclusion are listed.
    """
    paths = sorted([c["path"] for c in candidates])
    if not paths:
        return ""

    lines = ["## Project Structure", "", "```"]
    for p in paths:
        lines.append(f"  {p}")
    lines.extend(["```", "", "---", ""])
    return "\n".join(lines)


def build_bundle(
    ranked_files: List[Dict[str, Any]], candidates: List[Dict[str, Any]], budget: int
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """
    Build markdown context bundle satisfying total token budget constraint.
    Greedily includes top ranked files. Handles truncation if full file exceeds budget.
    Guarantees bundle token count NEVER exceeds budget even for tiny budget values.
    """
    initial_header = "# Project Context Bundle\n\n"
    initial_tokens = count_tokens(initial_header)

    # Handle extremely small budget where even initial header exceeds budget
    if initial_tokens > budget:
        char_limit = max(0, budget * 4)
        bundle_text = initial_header[:char_limit]
        while count_tokens(bundle_text) > budget and len(bundle_text) > 0:
            bundle_text = bundle_text[:-1]
        used_tokens = count_tokens(bundle_text)
        excluded_files = [{"path": f["path"], "reason": "budget limit exceeded"} for f in ranked_files]
        return bundle_text, [], excluded_files, used_tokens

    bundle_text = initial_header
    used_tokens = initial_tokens

    # Include project tree overview if budget > 300 tokens
    if budget > 300:
        tree_text = generate_project_tree(candidates)
        tree_tokens = count_tokens(tree_text)
        if tree_text and used_tokens + tree_tokens + 50 <= budget:
            bundle_text += tree_text
            used_tokens += tree_tokens

    included: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []

    for file_info in ranked_files:
        path = file_info["path"]
        content = file_info["content"]
        score = file_info.get("score", 0.0)

        header = f"## File: {path}\n\n"
        full_entry = f"{header}{content}\n\n---\n\n"
        full_entry_tokens = count_tokens(full_entry)

        # 1. Full file fits in remaining budget
        if used_tokens + full_entry_tokens <= budget:
            bundle_text += full_entry
            used_tokens += full_entry_tokens
            included.append(
                {
                    "path": path,
                    "tokens": full_entry_tokens,
                    "reason": f"relevance score: {score:.1f}",
                }
            )
            continue

        # 2. File does not fit full - try truncation if remaining budget permits
        header_tokens = count_tokens(header)
        truncation_note = "\n\n[... Truncated due to budget limit ...]\n\n---\n\n"
        note_tokens = count_tokens(truncation_note)
        remaining_budget = budget - used_tokens

        content_budget = remaining_budget - header_tokens - note_tokens

        if content_budget > 0:
            char_budget = content_budget * 4
            truncated_content = content[:char_budget]
            truncated_entry = f"{header}{truncated_content}{truncation_note}"

            # Fine-tune slice to guarantee no budget overflow
            while (
                count_tokens(truncated_entry) > remaining_budget
                and char_budget > 0
            ):
                char_budget -= 4
                truncated_content = content[: max(0, char_budget)]
                truncated_entry = f"{header}{truncated_content}{truncation_note}"

            entry_tokens = count_tokens(truncated_entry)
            if char_budget > 0 and used_tokens + entry_tokens <= budget:
                bundle_text += truncated_entry
                used_tokens += entry_tokens
                included.append(
                    {
                        "path": path,
                        "tokens": entry_tokens,
                        "reason": f"relevance score: {score:.1f} (truncated)",
                    }
                )
                continue

        # 3. Exclude if cannot fit full or truncated
        excluded.append({"path": path, "reason": "budget limit exceeded"})

    return bundle_text, included, excluded, used_tokens


def generate_manifest(
    budget: int,
    used: int,
    included: List[Dict[str, Any]],
    excluded: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate dictionary following exact manifest schema from SPEC.
    """
    cleaned_included = []
    for item in included:
        cleaned_included.append(
            {
                "path": item["path"],
                "tokens": item["tokens"],
                "reason": item.get("reason", "high relevance score"),
            }
        )

    cleaned_excluded = []
    for item in excluded:
        cleaned_excluded.append(
            {
                "path": item["path"],
                "reason": item.get("reason", "budget limit exceeded"),
            }
        )

    cleaned_included.sort(key=lambda x: x["path"])
    cleaned_excluded.sort(key=lambda x: x["path"])

    return {
        "budget": budget,
        "used": used,
        "included": cleaned_included,
        "excluded": cleaned_excluded,
    }


def main(args: Optional[List[str]] = None) -> None:
    """
    Main entry point for ctxpack CLI.
    """
    parsed_args = parse_args(args)

    out_rel = None
    if parsed_args.out:
        try:
            out_rel = os.path.relpath(parsed_args.out, parsed_args.path).replace("\\", "/")
        except ValueError:
            out_rel = parsed_args.out.replace("\\", "/")

    manifest_rel = None
    if parsed_args.manifest:
        try:
            manifest_rel = os.path.relpath(parsed_args.manifest, parsed_args.path).replace("\\", "/")
        except ValueError:
            manifest_rel = parsed_args.manifest.replace("\\", "/")

    # 1. Inspect directory for candidate text files vs noise/binary/generated files
    candidates, walk_excluded = walk_files(
        parsed_args.path, out_file=out_rel, manifest_file=manifest_rel
    )

    # 2. Rank candidates by relevance score
    ranked_candidates = rank_files(candidates, parsed_args.task)

    # 3. Build context bundle while adhering strictly to budget
    bundle_text, included, packing_excluded, used_tokens = build_bundle(
        ranked_candidates, candidates, parsed_args.budget
    )

    all_excluded = walk_excluded + packing_excluded

    # 4. Generate manifest structure
    manifest = generate_manifest(
        parsed_args.budget, used_tokens, included, all_excluded
    )

    # 5. Output bundle (write to --out if specified, else stdout)
    if parsed_args.out:
        try:
            with open(parsed_args.out, "w", encoding="utf-8") as f:
                f.write(bundle_text)
        except OSError as e:
            sys.stderr.write(f"Error writing bundle to '{parsed_args.out}': {e}\n")
            sys.exit(2)
    else:
        sys.stdout.write(bundle_text)

    # 6. Output manifest (write to --manifest if specified)
    if parsed_args.manifest:
        try:
            with open(parsed_args.manifest, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
                f.write("\n")
        except OSError as e:
            sys.stderr.write(
                f"Error writing manifest to '{parsed_args.manifest}': {e}\n"
            )
            sys.exit(2)

    # 7. Always print informative summary line to stderr
    pct = (used_tokens / parsed_args.budget * 100.0) if parsed_args.budget > 0 else 0.0
    sys.stderr.write(
        f"ctxpack summary: Used {used_tokens}/{parsed_args.budget} tokens ({pct:.1f}%) | "
        f"Included {len(included)} files | Excluded {len(all_excluded)} files\n"
    )

    sys.exit(0)


if __name__ == "__main__":
    main()
