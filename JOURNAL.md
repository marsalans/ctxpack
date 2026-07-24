# JOURNAL.md — Module 1 Hackathon Reflection

---

### 1. Three decisions we made, and what we rejected in each case

- **Decision 1: Keyword Overlap + Depth & Extension Bonus vs. AST/Graph Parsing**
  - *Chosen:* Tokenized word frequency overlap (`collections.Counter`), directory depth bonus, and prioritized file extension weights.
  - *Rejected:* AST-based import dependency graph parsing. Standard library AST parsing works well for Python, but breaks on multi-language repositories (JavaScript, Rust, Go) and adds heavy overhead.
- **Decision 2: Smart Head Truncation Slicing vs. Complete File Exclusion**
  - *Chosen:* Include partial head slice of oversized files (`content[:content_budget * 4]`) with a `[... Truncated due to budget limit ...]` footer if remaining budget permits header + notice overhead.
  - *Rejected:* Skipping oversized files entirely. Skipping high-relevance source files leaves out critical project context when budget is tight.
- **Decision 3: Dynamic Output Exclusion vs. Static Filename Blacklisting**
  - *Chosen:* Dynamically resolving canonical paths for `--out` and `--manifest` targets alongside default names (`bundle.md`, `manifest.json`) and excluding them prior to ranking.
  - *Rejected:* Static name hardcoding only. Hardcoding static names fails when a user specifies custom output paths like `--out my_context.md`.

---

### 2. The hardest bug we hit, and how we found the root cause

- **The Bug:** Self-inclusion feedback loop where repeated runs of `ctxpack` with `--out bundle.md` would discover previous `bundle.md` output files, causing token usage calculations to balloon exponentially across successive runs.
- **Root Cause Investigation:** Ran `ctxpack` sequentially 3 times on the same folder and noticed `manifest.json` included `bundle.md` with high token costs. The file crawler was inspecting all `.md` files without checking if the file path matched the designated bundle output location.
- **Resolution:** Added a canonical path check against normalized output paths (`--out` and `--manifest`) during file traversal to exclude generated output files with reason `"generated output file"`.

---

### 3. Something the AI got wrong or confidently misled us on, and how we caught it

*Note: Question 3 is highlighted as the most critical evaluation question. During pair programming with the AI assistant, we identified and corrected 4 distinct AI traps:*

#### Trap 1: Self-Inclusion Feedback Loop (`bundle.md` / `manifest.json`)
- **What AI Proposed:** The AI implemented `os.walk()` to collect all readable `.md` files without filtering out output targets.
- **Why It Failed:** When running `python ctxpack.py --path . --task "test" --budget 5000 --out bundle.md`, the AI included the generated `bundle.md` from the previous run into the new bundle, causing exponential context recursion.
- **How We Caught It:** Audited `manifest.json` after running `ctxpack` twice and saw `bundle.md` listed under `included` with 4,000+ tokens.
- **Fix:** Implemented `GENERATED_OUTPUT_NAMES` and dynamically matched `--out` / `--manifest` arguments during directory traversal to exclude them with reason `"generated output file"`.

#### Trap 2: Non-Deterministic Directory Traversal (`os.walk`)
- **What AI Proposed:** Relying on standard `os.walk(target_path)` iteration without explicit file or directory sorting.
- **Why It Failed:** `os.walk()` returns files in filesystem directory-entry order, which varies across operating systems (Windows vs Linux vs macOS) and filesystems (NTFS vs ext4).
- **How We Caught It:** Ran `ctxpack` on two separate machines and compared SHA-256 hashes of `bundle.md`. The files differed despite identical code and inputs.
- **Fix:** Injected explicit alphabetical sorting (`dirs.sort()`, `files.sort()`) inside the `os.walk()` loop and secondary path lexicographical tie-breakers in `rank_files()`.

#### Trap 3: Incorrect Token Accounting & Integer Division (`len // 4`)
- **What AI Proposed:** Using simple integer division `len(text) // 4` to estimate token counts.
- **Why It Failed:** The specification MANDATES `math.ceil(len(text) / 4)`. Integer division undercounts tokens by 1 token whenever string length is not a multiple of 4 (e.g. 5 chars = 2 tokens under ceil, but 1 token under `//`).
- **How We Caught It:** Inspected edge cases with small 5-character strings and verified that `// 4` produced invalid token estimates.
- **Fix:** Enforced `math.ceil(len(text) / 4)` across all helper functions.

#### Trap 4: Forgetting Bundle & Formatting Overhead in Budget Math
- **What AI Proposed:** Calculating budget consumption strictly on raw file contents, assuming bundle headers (`# Project Context Bundle`), file title delimiters (`## File: <path>`), and visual tree structures were "free".
- **Why It Failed:** The total rendered Markdown bundle exceeded `--budget` by up to 250 tokens on every run.
- **How We Caught It:** Ran `count_tokens(final_bundle_text)` on the output file and discovered `used` exceeded `--budget`.
- **Fix:** Deducted Markdown header overhead, tree structure tokens, and file delimiter tokens from `--budget` *before* allocating content tokens to individual files.

---

### 4. What we would do differently with two more hours

1. **Native `.gitignore` Glob Matching:** Implement standard `.gitignore` pattern parsing using `fnmatch` to respect project-specific exclusion rules without relying on third-party libraries.
2. **AST-Aware Python Slicing:** Add AST-based function/class level chunking for Python files so truncation cuts at clean boundary markers rather than raw character offsets.
3. **Interactive CLI Progress Indicator:** Add a light, standard-err spinner for mega-repositories containing > 10,000 files.

---

### 5. Who wrote what — per person

- **Arsalan:** Architecture design, CLI contract definition, `SPEC.md`, keyword ranking engine, `ctxpack.py` core implementation, token calculation, and GitHub repository configuration.
