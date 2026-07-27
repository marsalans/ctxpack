# ctxpack

Context engineering CLI tool for AI coding assistants. `ctxpack` analyzes a project repository, selects the most relevant files for a developer task, and packs them into a single Markdown bundle fitting strictly within a token budget.

---

## What is ctxpack?

AI coding assistants are constrained by context window limits. `ctxpack` replaces developer guesswork with a deterministic context packer. Given a project folder, a task description, and a token budget, `ctxpack` packs the most relevant text files into one Markdown context bundle and outputs a JSON manifest detailing what was included, what was excluded, and why.

---

## Features

- **Zero Third-Party Dependencies:** Built exclusively with Python standard library (`argparse`, `os`, `sys`, `math`, `json`, `collections`, `re`).
- **Relevance Ranking Engine:** Ranks files by combining keyword overlap (`collections.Counter`), directory depth bonuses, and prioritized file extension weights.
- **Strict Token Budget Enforcement:** Guaranteed `used <= budget` under all conditions, even for single-digit token budgets.
- **Smart Truncation:** Intelligently slices oversized files to fit remaining budget while appending clean truncation notices.
- **Noise & Binary Filtering:** Automatically filters out noise directories (`.git/`, `node_modules/`, `__pycache__/`), lockfiles (`*.lock`), minified assets, and binary/unreadable files.
- **Self-Inclusion Guard:** Detects and excludes generated output files (`bundle.md`, `manifest.json`, `--out`, `--manifest` targets) to prevent feedback loops.
- **100% Deterministic:** Byte-identical outputs across repeated runs on identical inputs.
- **Clean CLI Interface:** Clean one-line `stderr` error messages with standard exit code mapping (`0` success, `1` invalid arguments, `2` path error).

---

## Installation

No `pip install` required. Requires **Python 3.10+**.

```bash
# Clone repository
git clone https://github.com/marsalans/ctxpack.git
cd ctxpack

# Run directly
python ctxpack.py --help
```

---

## Usage

```bash
ctxpack --path <folder> --task "<task description>" --budget <int> [--out <file>] [--manifest <file>]
```

| Flag | Behavior |
|---|---|
| `--path` | **Required.** Path to the project folder to analyze and pack. |
| `--task` | **Required.** Free-text description of the developer task. |
| `--budget` | **Required.** Maximum token limit for the entire bundle (must be positive integer). |
| `--out` | *Optional.* Write Markdown context bundle to file (default: `stdout`). |
| `--manifest` | *Optional.* Write JSON manifest accounting to file (default: summary to `stderr`). |

### Examples

#### Output bundle to stdout and print summary to stderr
```bash
python ctxpack.py --path . --task "Implement context packing CLI" --budget 4000
```

#### Write bundle to file and save JSON manifest
```bash
python ctxpack.py --path . --task "Build context packer" --budget 5000 --out bundle.md --manifest manifest.json
```

---

## Output

### Bundle Example (`bundle.md`)

```markdown
# Project Context Bundle

## Project Structure

```
  SPEC.md
  ctxpack.py
```

---

## File: ctxpack.py

#!/usr/bin/env python3
...
```

### Manifest Example (`manifest.json`)

```json
{
  "budget": 5000,
  "used": 5000,
  "included": [
    {
      "path": "SPEC.md",
      "tokens": 968,
      "reason": "relevance score: 45.0 (truncated)"
    },
    {
      "path": "ctxpack.py",
      "tokens": 4010,
      "reason": "relevance score: 55.0"
    }
  ],
  "excluded": [
    {
      "path": ".git",
      "reason": "noise directory"
    },
    {
      "path": "bundle.md",
      "reason": "generated output file"
    },
    {
      "path": "manifest.json",
      "reason": "generated output file"
    }
  ]
}
```

---

## Ranking strategy

Files are ranked using a composite relevance score:

1. **Keyword Overlap Score:** Tokenizes the task description and file contents into lowercase words using `re.findall(r"\w+", text)`. Computes word frequency overlap via `collections.Counter`:
   $$\text{Overlap Score} = \sum_{\text{word} \in \text{task}} \min(\text{task\_count}[\text{word}], \text{file\_count}[\text{word}]) \times 10$$
2. **Directory Depth Bonus:** Favors shallower relative paths:
   $$\text{Depth Bonus} = \max(0, 10 - \text{depth} \times 2)$$
3. **Extension Bonus:** Adds $+5$ points for prioritized source/documentation extensions (`.py`, `.md`, `.js`, `.ts`, `.json`, `.yaml`, `.yml`).
4. **Deterministic Tie-Breaking:** Sorted by `(-score, relative_path)` to guarantee deterministic ordering.

---

## Truncation strategy

When a high-ranking file's full token cost exceeds remaining budget:

1. Calculates overhead for section header (`## File: <path>\n\n`) and truncation notice (`\n\n[... Truncated due to budget limit ...]\n\n---\n\n`).
2. Calculates maximum available character content budget:
   $$\text{content\_budget} = \text{remaining\_budget} - \text{header\_tokens} - \text{truncation\_note\_tokens}$$
3. Takes character slice `content[:content_budget * 4]` and fine-tunes slice length so total entry tokens fit strictly within `remaining_budget`.
4. If `content_budget <= 0` (remaining budget cannot fit header + truncation note), excludes file with reason `"budget limit exceeded"`.

---

## Noise detection

`ctxpack` automatically filters non-essential files before ranking:

- **Noise Directories:** `.git/`, `__pycache__/`, `node_modules/`, `venv/`, `.venv/`, `dist/`, `build/`, `.idea/`, `.vscode/`.
- **Noise Files:** `*.lock`, `*.min.js`, `*.min.css`, `package-lock.json`, `yarn.lock`, `cargo.lock`, `poetry.lock`, `pnpm-lock.yaml`.
- **Binary & Non-Text Files:** Checked via UTF-8 decoding (`UnicodeDecodeError`) and null-byte (`\x00`) presence.
- **Generated Output Files:** Output targets specified by `--out` or `--manifest` (e.g., `bundle.md`, `manifest.json`) are excluded with reason `"generated output file"`.

---

## Project structure

```
ctxpack/
├── SPEC.md         # Technical specification document
├── ctxpack.py      # Core CLI tool implementation
├── README.md       # Project documentation & quickstart
├── GEMINI.md       # Agent instructions for Google Gemini Antigravity
├── CLAUDE.md       # Context engineering file for AI assistants
├── PROMPTS.md      # Key engineering prompts log
├── JOURNAL.md      # Hackathon reflection journal
├── manifest.json   # Sample generated manifest JSON
└── bundle.md       # Sample generated Markdown bundle
```

---

## Running tests

#### 1. General packing test
```bash
python ctxpack.py --path . --task "Build context engineering CLI" --budget 5000 --out bundle.md --manifest manifest.json
```

#### 2. Argument validation test (Exit code 1)
```bash
python ctxpack.py --path . --task "test" --budget -100
# Output: Error: --budget must be a positive integer. (Exit code 1)
```

#### 3. Path error test (Exit code 2)
```bash
python ctxpack.py --path ./invalid_folder --task "test" --budget 1000
# Output: Error: Path does not exist: ./invalid_folder (Exit code 2)
```

---

## Example screenshots

<img width="1152" height="100" alt="Screenshot 2026-07-27 205244" src="https://github.com/user-attachments/assets/b34984dd-ffc3-4eb6-ab26-fb9939687e6c" />
<img width="1146" height="622" alt="Screenshot 2026-07-27 205216" src="https://github.com/user-attachments/assets/e827eae4-05d4-41d7-b39f-49b1422c293d" />

### Terminal Summary Execution
```
$ python ctxpack.py --path . --task "context packing tool" --budget 5000 --out bundle.md --manifest manifest.json
ctxpack summary: Used 5000/5000 tokens (100.0%) | Included 2 files | Excluded 3 files
```

---

## Future improvements

- **Native `.gitignore` Parsing:** Parse `.gitignore` patterns natively using standard library path matching.
- **AST-Aware Code Slicing:** Perform AST parsing for Python files to slice at class/function boundaries rather than character offsets during truncation.
- **Parallelized Traversal:** Optimize traversal for mega-repositories containing > 10,000 files.
