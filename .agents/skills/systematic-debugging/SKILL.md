---
name: systematic-debugging
description: 4-phase root cause debugging with root-cause-tracing, defense-in-depth, condition-based-waiting. Source - obra/superpowers
---
# Systematic Debugging
## Phase 1 Reproduce
- Create minimal reproducible case
- Document exact steps, expected vs actual
## Phase 2 Isolate
- Narrow scope, binary search through code/commits
## Phase 3 Root Cause
- Root-cause-tracing: trace execution path
- Defense-in-depth: look for multiple failure points
- Condition-based-waiting: proper sync for timing issues
- Understand WHY not just WHERE
## Phase 4 Fix and Verify
- Fix root cause not symptom, write regression test
## Source
- Repository: https://github.com/obra/superpowers
