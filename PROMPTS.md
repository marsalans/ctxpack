# PROMPTS.md — Key Engineering Prompts & Prompt Engineering Evidence

This document records the 5 most important driving prompts used during the development of `ctxpack`. Each section demonstrates the prompt engineering iteration loop: initial goal, initial prompt, initial AI response, identified problem, improved prompt, final result, and prompt engineering lesson learned.

---

## Prompt 1: Initial Specification & CLI Contract Setup

- **Goal:**
  Design and write the initial technical specification `SPEC.md` strictly according to `STUDENT_BRIEF.md`.
- **Prompt:**
  > "Create a SPEC.md file for ctxpack based on STUDENT_BRIEF.md."
- **Response:**
  > Produced a generic overview document detailing basic CLI options, but omitted exact exit codes (`0`, `1`, `2`) and did not explain why the ranking strategy was chosen over alternatives.
- **Problem:**
  The AI ignored explicit exit code mapping rules and failed to document rejected alternatives required by the spec quality grading criteria.
- **Improved Prompt:**
  > "Analyze STUDENT_BRIEF.md and write a comprehensive SPEC.md detailing:
  > 1. Exact CLI contract and exit code mapping (0 success, 1 invalid args/bad budget, 2 path not found/unreadable).
  > 2. Token counting rule `math.ceil(len(text)/4)` applied to total bundle.
  > 3. Ranking strategy selection AND explicit defense of why AST/import graphs were rejected.
  > 4. Truncation policy, noise exclusion list, manifest JSON schema, and Definition of Done."
- **Result:**
  Generated a spec matching all hackathon criteria. Successfully committed as Commit #1 (`3315552`).
- **Lesson:**
  Always pin interface contracts, error taxonomy, and design trade-off requirements explicitly in the prompt.

---

## Prompt 2: CLI Argument Parsing & Error Taxonomy

- **Goal:**
  Implement argument parsing in `ctxpack.py` with custom error handling.
- **Prompt:**
  > "Implement argparse in ctxpack.py for --path, --task, --budget, --out, and --manifest."
- **Response:**
  > Added standard `argparse.ArgumentParser`. When invalid flags or missing required arguments were passed, `argparse` printed multi-line usage messages to `stderr` and called `sys.exit(2)`.
- **Problem:**
  Standard `argparse` exits with code `2` on bad arguments (instead of required exit code `1`) and dumps ugly multi-line usage text rather than a clean single-line error message.
- **Improved Prompt:**
  > "Create a CustomArgumentParser subclass extending argparse.ArgumentParser that overrides error(message) to output a clean, single-line error message to stderr (`Error: <message>\n`) and exit with code 1. Add validation ensuring --budget is a positive integer (> 0). Add separate path checks returning exit code 2 if --path does not exist or is not a directory."
- **Result:**
  All negative test cases output clean 1-line error messages with exact exit code mapping (`1` for bad flags/budget, `2` for missing path).
- **Lesson:**
  Override default library error handlers to enforce strict CLI exit code contracts.

---

## Prompt 3: Directory Traversal, Noise Exclusion & Determinism

- **Goal:**
  Implement recursive file discovery in `ctxpack.py` while excluding noise and binary files deterministically.
- **Prompt:**
  > "Write a walk_files function using os.walk to read text files in --path."
- **Response:**
  > Created a standard `os.walk()` loop that attempted to read every file. It threw `UnicodeDecodeError` on binary files and produced non-deterministic file orderings across different OS platforms.
- **Problem:**
  1. Failed to exclude noise directories (`.git/`, `node_modules/`, `__pycache__/`).
  2. Crashed on binary files instead of handling `UnicodeDecodeError` gracefully.
  3. Output order depended on raw OS directory traversal order (non-deterministic).
- **Improved Prompt:**
  > "Implement walk_files(target_path, out_file, manifest_file). Requirements:
  > 1. In os.walk, sort `dirs` and `files` alphabetically (`dirs.sort()`, `files.sort()`) before iteration to guarantee 100% determinism.
  > 2. Skip and record noise directories (`.git`, `node_modules`, `venv`, `__pycache__`) with reason 'noise directory'.
  > 3. Detect binary files using UTF-8 decoding checks (`UnicodeDecodeError`) and null-byte (`\x00`) checks, recording them with reason 'binary or unreadable file'.
  > 4. Sort final returned file lists deterministically by relative path."
- **Result:**
  Filesystem traversal operates deterministically across OS environments, gracefully handling binary executables without throwing tracebacks.
- **Lesson:**
  Explicitly instruct the AI to sort directory iteration vectors when determinism is required.

---

## Prompt 4: Ranking Engine & Smart Head Truncation

- **Goal:**
  Build relevance ranking and greedy bundle packing loop with budget-enforced truncation.
- **Prompt:**
  > "Rank files by keyword overlap and pack them into the budget."
- **Response:**
  > Ranked files using word frequency overlap, but calculated token budgets using integer division `len // 4` and ignored formatting overhead (headers, structure tree, section titles).
- **Problem:**
  1. Token calculation used `len // 4` instead of required `math.ceil(len / 4)`.
  2. Oversized files were skipped completely instead of truncated.
  3. Final bundle exceeded `--budget` because header and separator overhead was omitted from calculations.
- **Improved Prompt:**
  > "Implement rank_files() and build_bundle(). Requirements:
  > 1. Token count formula MUST be `math.ceil(len(text) / 4)`.
  > 2. Rank by composite score: keyword overlap (`collections.Counter`) + depth bonus + extension weight, with secondary sorting by path for tie-breaking.
  > 3. Calculate bundle overhead (headers, project structure overview, file title delimiters) and deduct from remaining budget FIRST.
  > 4. If an oversized file's content exceeds remaining content budget, slice head content (`content[:content_budget * 4]`) and append truncation notice (`\n[... Truncated due to budget limit ...]`).
  > 5. Fine-tune character slice length so `used <= budget` holds true under all conditions."
- **Result:**
  `used <= budget` holds strictly true across all test cases. Oversized files are smartly truncated with clean warning footers.
- **Lesson:**
  Always deduct structural formatting overhead from budget limits before packing variable content.

---

## Prompt 5: Self-Inclusion Feedback Loop Prevention

- **Goal:**
  Prevent `ctxpack` from ingesting its own output files during directory traversal.
- **Prompt:**
  > "Fix the issue where running ctxpack creates bundle.md and then packs bundle.md on the next run."
- **Response:**
  > Hardcoded `if f == "bundle.md": continue` in `walk_files()`.
- **Problem:**
  Hardcoding static names failed when users specified custom output paths via `--out my_custom_bundle.md` or `--manifest my_manifest.json`.
- **Improved Prompt:**
  > "Update walk_files() to accept `out_file` and `manifest_file` target paths. Normalize paths and exclude any relative path that matches `out_file`, `manifest_file`, or standard generated names (`bundle.md`, `manifest.json`) prior to content reading, recording them in manifest with reason 'generated output file'."
- **Result:**
  Dynamic output path matching completely eliminated recursive feedback loops, regardless of custom `--out` or `--manifest` arguments.
- **Lesson:**
  Avoid hardcoded static checks; design dynamic path matching for user-configurable output targets.
