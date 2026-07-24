# JOURNAL.md — Module 1 Hackathon Reflection

### 1. Three decisions we made, and what we rejected in each case

- **Decision 1: Keyword Overlap + Depth & Extension Bonus vs. Heavy AST/Graph Parsing**
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

- **The Bug:** Self-inclusion feedback loop where repeated runs of `ctxpack.py` with `--out bundle.md` would discover previous `bundle.md` output files, causing token usage calculations to balloon exponentially across successive runs.
- **Root Cause Investigation:** Ran `ctxpack` sequentially 3 times on the same folder and noticed `manifest.json` included `bundle.md` with high token costs. The file crawler was inspecting all `.md` files without checking if the file path matched the designated bundle output location.
- **Resolution:** Added a canonical path check against normalized output paths (`--out` and `--manifest`) during file traversal to exclude generated output files with reason `"generated output file"`.

---

### 3. Something Claude Code got wrong or confidently misled us on, and how we caught it

- **The Issue:** Claude Code initially suggested calculating truncation character limits using `len(text) // 4`, assuming 1 token strictly equals 4 characters in reverse.
- **How We Caught It:** Tested an oversized file near the budget edge and discovered the final packed bundle exceeded `--budget` by 2 tokens. Because `math.ceil(len(text) / 4)` round-up behavior means a 5-character string counts as 2 tokens (not 1 token), simple character multiplication over-allocated content.
- **Fix:** Implemented an exact character slice fine-tuning loop that verifies `math.ceil(len(bundle) / 4) <= budget` directly on the rendered output string before finalizing the truncated section.

---

### 4. What we would do differently with two more hours

1. **Native `.gitignore` Glob Matching:** Implement standard `.gitignore` pattern parsing using `fnmatch` to respect project-specific exclusion rules without relying on third-party libraries.
2. **AST-Aware Python Slicing:** Add AST-based function/class level chunking for Python files so truncation cuts at clean boundary markers rather than raw character offsets.
3. **Interactive CLI Progress Indicator:** Add a light, standard-err spinner for mega-repositories containing > 10,000 files.

---

### 5. Who wrote what — per person

- **Arsalan:** Architecture design, CLI contract definition, `SPEC.md`, keyword ranking engine, `ctxpack.py` core implementation, token calculation, and GitHub repository configuration.
