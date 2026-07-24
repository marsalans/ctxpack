# CLAUDE.md - Context Engineering & AI Guidance for ctxpack

> *Note: Development of this repository was driven using **Google Gemini Antigravity**. See [GEMINI.md](GEMINI.md) for primary agent context.*

## Overview
`ctxpack` is a zero-dependency Python 3.10+ command-line tool built via Spec-Driven Development (SDD). It recursively inspects a project workspace, ranks files according to task relevance, and packs them into a single Markdown context bundle fitting strictly within a specified token budget.

---

## 1. AI Development Workflow
1. **Spec-First Blueprint**: All architecture, CLI contracts, token counting rules, and exit code definitions are specified in `SPEC.md` prior to code generation.
2. **Incremental Development Cycles**: Features are built incrementally (walk -> rank -> truncate -> bundle -> manifest -> error handling).
3. **Prompt History Logging**: Every user prompt and assistant output is recorded in Prompt History Records (`history/prompts/ctxpack/`).

---

## 2. Context Provisioning Strategy
- **Ground Truth Ingestion**: Before requesting code edits, `SPEC.md`, `STUDENT_BRIEF.md`, and relevant module source code are provided directly in agent context.
- **Explicit Constraint Framing**: Prompts explicitly reinforce hard boundaries: Python stdlib only, exact formula `math.ceil(len(text)/4)`, strict exit codes (`0`, `1`, `2`), and single-line `stderr` error protocol.
- **File Reference Links**: Explicit file paths and line ranges are referenced in all prompt directives.

---

## 3. Iteration Process
- **Red-Green-Refactor Pipeline**:
  - *Red*: Define acceptance criteria and write edge-case CLI test commands.
  - *Green*: Implement minimum viable function logic to satisfy tests.
  - *Refactor*: Optimize token accounting, eliminate code redundancy, and ensure deterministic path sorting.

---

## 4. Verification Process
All AI-generated changes are validated through empirical runtime execution:
1. **Standard Execution Verification**:
   ```bash
   python ctxpack.py --path . --task "Context packing tool" --budget 5000 --out bundle.md --manifest manifest.json
   ```
2. **Exit Code Assertions**:
   - Exit `1` (Invalid Arguments / Bad Budget): `python ctxpack.py --path . --task "test" --budget -10`
   - Exit `2` (Path Not Found): `python ctxpack.py --path ./invalid_dir --task "test" --budget 1000`
3. **Determinism Diff Test**:
   Run `ctxpack` twice on identical inputs and diff outputs to guarantee 100% byte-identical output.

---

## 5. AI Output Auditing Protocol
- **Token Math Audit**: Re-calculate total bundle character length divided by 4 using `math.ceil(len(bundle) / 4)` to confirm `used <= budget`.
- **Bundle Overhead Audit**: Verify that Markdown headers, structure trees, and truncation notices are included inside the token budget calculations.
- **Feedback Loop Audit**: Confirm that output files (`--out`, `--manifest`, `bundle.md`, `manifest.json`) are excluded from file traversal.
- **Traceback Audit**: Ensure negative test cases output clean 1-line error messages to `stderr` with zero raw Python tracebacks.
