# PROMPTS.md — Key Engineering Prompts

This document records the 5 most important driving prompts used during the development of `ctxpack`, detailing the requested prompt, assistant output, modifications made, and rationale.

---

### Prompt 1: Initial Specification & CLI Contract Setup

- **What was asked:**
  > "Analyze STUDENT_BRIEF.md and create a comprehensive SPEC.md detailing the exact CLI contract, standard library constraint, token calculation rule `math.ceil(len(text)/4)`, relevance ranking strategy, truncation policy, noise filtering list, and manifest JSON schema before writing any code."
- **What was received:**
  > A complete `SPEC.md` document defining standard exit codes (`0`, `1`, `2`), composite keyword overlap ranking + depth/extension scoring, fine-grained truncation slice rules, and strict manifest output schemas.
- **What was changed and why:**
  > Refined the ranking strategy section to explicitly document rejected alternatives (e.g. naive filename regex, AST import dependency trees) to satisfy the spec quality grading requirement.

---

### Prompt 2: Core CLI Architecture & Argument Validation

- **What was asked:**
  > "Create `ctxpack.py` basic CLI structure with `argparse`. Ensure required flags `--path`, `--task`, `--budget` and optional `--out`, `--manifest` are handled. Implement custom argument parsing to guarantee exact exit codes: 1 for invalid arguments, 2 for path not found, and 0 for success, with clean one-line stderr error messages and no tracebacks."
- **What was received:**
  > Custom error handling subclass for `argparse.ArgumentParser` overriding `error()` to write single-line messages to `stderr` and call `sys.exit(1)`. Path existence checks wrapping `os.path.exists()` to exit with code `2`.
- **What was changed and why:**
  > Added explicit validation for `--budget` to enforce `budget > 0` and return exit code `1` when `--budget` is zero or negative.

---

### Prompt 3: Directory Traversal, Noise Exclusions & Binary Detection

- **What was asked:**
  > "Implement recursive file walking for `--path`. Filter out noise directories (`.git/`, `node_modules/`, `__pycache__/`, `venv/`, `dist/`), noise files (`*.lock`, `*.min.js`), and binary files. Exclude unreadable/binary files using UTF-8 decoding and null-byte checks without throwing exceptions."
- **What was received:**
  > `walk_files()` function returning structured file dictionaries with content, token counts, and exclusion reasons (`"noise directory"`, `"noise file"`, `"binary or unreadable file"`).
- **What was changed and why:**
  > Added a secondary null-byte check (`b'\x00' in chunk`) on the raw file bytes before text decoding to quickly skip large binary executables without wasting CPU on failed UTF-8 decoding.

---

### Prompt 4: Relevance Ranking Engine & Deterministic Greedy Bundle Builder

- **What was asked:**
  > "Build the file ranking engine and context bundle packing loop. Compute keyword overlap using `collections.Counter`, directory depth bonus, and extension weights. Pack files into budget greedily until budget is full. Implement smart head slicing for oversized files."
- **What was received:**
  > `rank_files()` returning sorted file records by `(-score, relative_path)`. `build_bundle()` packing files while updating remaining token budget and writing truncation notices when necessary.
- **What was changed and why:**
  > Added deterministic lexicographical sorting by relative path as a secondary sort key to ensure 100% byte-identical output across repeated runs on identical inputs.

---

### Prompt 5: Self-Inclusion Feedback Loop Fix & Manifest Generation

- **What was asked:**
  > "Ensure `ctxpack.py` excludes its own output files (`bundle.md`, `manifest.json`, or any custom paths passed via `--out` or `--manifest`) from being packed into the context bundle to avoid recursive feedback loops."
- **What was changed and why:**
  > Dynamically populated `output_files` set from `--out` and `--manifest` resolved paths, and added check during file traversal to exclude matching relative paths with reason `"generated output file"`.
