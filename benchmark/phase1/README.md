# Benchmark: Phase 1

**Task**: Feature addition to an existing Python project  
**Date**: 2026-02-18  
**LLM (all tools)**: `claude-sonnet-4-5-20250929`  
**Runs per tool**: 3  

Full report: [Dev.to article](https://dev.to/cognix-dev) | [Zenn article](https://zenn.dev/cognix)

---

## Results

| Metric | Cognix | Claude Code | Aider |
|--------|--------|-------------|-------|
| **Exec** | **100.0%** | **100.0%** | 87.5% |
| **Dep** | 100.0% | 100.0% | 100.0% |
| **Lint** | **0.00** | 4.79 | 1.69 |
| **Scope** | 100.0% | 100.0% | 100.0% |
| **Speed** | 863.7s | 390.8s | **190.6s** |

- **Exec**: fraction of `verify.py` tests passed (8 items, binary pass/fail each)
- **Lint**: ruff errors per 100 lines — lower is better
- **Speed**: wall-clock time from prompt to completion

---

## Structure

```
phase1/
├── prompt.md          # Task specification given to all tools
├── verify.py          # Automated evaluator (8 test items)
├── base/              # Unmodified base project (starting point)
└── results/
    ├── phase1_full_20260218_205351_clean.json  # Raw scores (all runs)
    ├── cognix/run1〜3/      # Generated code from Cognix
    ├── claude_code/run1〜3/ # Generated code from Claude Code
    └── aider/run1〜3/       # Generated code from Aider
```

---

## How to Reproduce

```bash
# Requirements: Python 3.9+, ruff
pip install ruff

# Evaluate any result
python benchmark/phase1/verify.py benchmark/phase1/results/cognix/run1
python benchmark/phase1/verify.py benchmark/phase1/results/claude_code/run1
python benchmark/phase1/verify.py benchmark/phase1/results/aider/run1
```

---

## Notes

- `cognix/run1` was re-run on 2026-02-20 (original file was overwritten). Scores are identical to the original run: exec=100%, lint=0.00.
- Local paths in JSON have been anonymized (`benchuser`).
