---
name: gsd-core
description: Git Ship Done - Context engineering and spec-driven development framework. Solves context rot via fresh-context subagents. Source - open-gsd/gsd-core
---
# GSD Core - Git Ship Done
## What is GSD Core
A context-engineering and spec-driven development framework that drives AI coding agents through a disciplined phase loop. Solves context rot by running heavy work in fresh-context subagents.
## Five Step Loop (per milestone)
1. Discuss - capture implementation decisions before planning
2. Plan - research, decompose, verify plan fits fresh context window
3. Execute - run plans in parallel waves, each executor gets clean 200k-token context
4. Verify - walk through what was built, diagnose and fix
5. Ship - create PR, archive the phase, repeat
## Quickstart
```
npx @opengsd/gsd-core@latest
```
## Source
- Repository: https://github.com/open-gsd/gsd-core
