---
name: dispatching-parallel-agents
description: Concurrent subagent workflows for parallel execution. Source - obra/superpowers (199K+ installs)
---
# Dispatching Parallel Agents
## Overview
Coordinates multiple subagents to work on independent tasks concurrently, maximizing throughput.
## Guidelines
- Tasks must be truly independent
- Each agent gets a clean context
- Results are aggregated and reviewed
- Failures in one agent do not block others
## Source
- Repository: https://github.com/obra/superpowers
