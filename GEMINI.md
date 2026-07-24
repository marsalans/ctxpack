# GEMINI.md - Context & Instructions for Google Gemini Antigravity

## Project Overview
`ctxpack` is a zero-dependency Python 3.10+ command-line tool built via Spec-Driven Development (SDD) using Google Gemini Antigravity. It recursively inspects a project workspace, ranks files according to task relevance, and packs them into a single Markdown context bundle fitting strictly within a specified token budget.

## Architectural Mandates & System Rules
1. **Python Standard Library Only:** Exclusively use standard library modules (`argparse`, `os`, `sys`, `math`, `json`, `collections`, `re`). Zero external dependencies (`pip install`).
2. **Exact Token Counting Rule:**
   ```python
   tokens = math.ceil(len(text) / 4)
   ```
   The budget applies to the **entire** final bundle output (including headers, project structure tree, file delimiters, and truncation notices). `used <= budget` must strictly hold true.
3. **Spec-Driven & Deterministic Execution:** File discovery, sorting, ranking tie-breakers, and manifest creation must produce 100% byte-identical output given identical inputs.
4. **Strict CLI Error Handling & Exit Codes:**
   - Exit Code `0`: Success.
   - Exit Code `1`: Invalid CLI arguments or invalid flag values.
   - Exit Code `2`: Path does not exist or is unreadable.
   - All errors write a clean, single-line error message to `stderr`. Never emit raw Python tracebacks.
5. **Noise & Self-Inclusion Exclusion:** Exclude `.git/`, `node_modules/`, `__pycache__/`, `venv/`, lockfiles (`*.lock`), minified assets (`*.min.js`), binary/unreadable files, and designated output targets (`--out` and `--manifest`).

## Development & Test Commands
- **Standard Execution:**
  `python ctxpack.py --path . --task "Context packing tool" --budget 5000 --out bundle.md --manifest manifest.json`
- **Invalid Argument Test (Exit 1):**
  `python ctxpack.py --path . --task "Test" --budget -50`
- **Path Not Found Test (Exit 2):**
  `python ctxpack.py --path ./non_existent_dir --task "Test" --budget 1000`
