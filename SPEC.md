# SPEC.md - ctxpack

## 1. CLI Contract (Exact)

```bash
ctxpack --path <folder> --task "<task description>" --budget <int> [--out <file>] [--manifest <file>]
```

- `--path`: Required - Folder to analyze.
- `--task`: Required - Description of developer task.
- `--budget`: Required - Maximum tokens for entire bundle (must be positive integer).
- `--out`: Optional - File path to write bundle (default: stdout).
- `--manifest`: Optional - File path to write JSON manifest (default: summary printed to stderr).

**Exit codes:**
- `0`: Success
- `1`: Invalid arguments
- `2`: Path not found or unreadable

---

## 2. Token Counting Rule (Exact)

```python
import math
tokens = math.ceil(len(text) / 4)
```

- The token budget applies to the **complete final bundle**, including any headers, file paths, separators, project tree structure, and truncation notices.
- Total bundle tokens must satisfy: `used <= budget`. Not by even one token may `--budget` be exceeded.

---

## 3. Ranking Strategy

- **Chosen Method:** Combined relevance score = Keyword overlap score (using `collections.Counter` matching task keywords vs file text tokens, normalized) + Directory depth bonus (shallower relative paths get higher priority) + File extension priority (`.py`, `.md`, `.js`, `.ts`, `.json`, `.yaml` prioritized over plain text).
- **Tie-breaker:** Secondary sorting by relative file path lexicographically (A to Z) to guarantee 100% deterministic output.
- **Why:** Balances semantic relevance with structural importance while staying within Python standard library constraints.
- **Rejected:** 
  - *Simple filename grep:* Too naive, misses relevant content.
  - *Import graph dependency tree:* Overly complex and too slow using stdlib alone.

---

## 4. Truncation Policy

- If a file's relevance score qualifies it for inclusion but its full token cost exceeds the remaining budget:
  1. Calculate available budget for file content: `content_budget = remaining_budget - header_tokens - truncation_note_tokens`.
  2. If `content_budget > 0`, include the leading `content_budget * 4` characters (head slice of file content) and append a truncation notice (`\n[... Truncated due to budget limit ...]`).
  3. If `content_budget <= 0` (budget cannot even fit header + truncation note), exclude the file entirely with reason `"budget limit exceeded"`.

---

## 5. Noise Detection & Error Handling

- **Noise Exclusion:** Automatically exclude noise directories and files: `.git/`, `__pycache__/`, `node_modules/`, `venv/`, `.venv/`, `*.lock`, `dist/`, `build/`, `*.min.js`, `*.min.css`. Record as excluded in manifest with reason `"noise directory"` or `"noise file"`.
- **Binary & Non-Text File Handling:** Detect non-text files using UTF-8 decoding checks (`UnicodeDecodeError` handling) or null-byte (`\x00`) presence. Exclude them gracefully with reason `"binary or unreadable file"`.
- **Error Handling:** All error paths (missing path, permission error, bad flags) output a clean, one-line error message to `stderr` with appropriate exit code (`1` or `2`), never dumping raw Python tracebacks.

---

## 6. Bundle Format

If budget permits, optional project tree overview is prepended, followed by formatted file sections:

```markdown
# Project Context Bundle

## File: path/to/file.py

<file content here>

---
```

---

## 7. Manifest Schema (Exact)

```json
{
  "budget": 8000,
  "used": 7912,
  "included": [
    {
      "path": "src/agent.py",
      "tokens": 812,
      "reason": "high keyword relevance"
    }
  ],
  "excluded": [
    {
      "path": "package-lock.json",
      "reason": "noise file"
    }
  ]
}
```

---

## 8. Definition of Done

- [ ] Satisfies all MUST requirements from brief.
- [ ] 100% Deterministic (identical inputs produce byte-identical bundle & manifest).
- [ ] Budget strictly enforced (`used <= budget`).
- [ ] Clean one-line error messages with exact exit codes (0, 1, 2); no raw tracebacks.
- [ ] Passes hidden edge cases (empty inputs, oversized single file, zero/tiny budget, binary files).
