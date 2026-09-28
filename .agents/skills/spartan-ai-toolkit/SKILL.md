---
name: spartan-ai-toolkit
description: Quality gates - typecheck, lint, test, review in sequence. Will not move to next step if previous fails. Source - spartan-stratos/spartan-ai-toolkit
---
# Spartan AI Toolkit
## Overview
Quality gates that run typecheck then lint then test then review in strict sequence. If previous step fails, next step does not run.
## Why It Matters
Without quality gates, AI will write code, notice a failing test, patch the test to pass, and declare done. With this toolkit, that path does not exist.
## Stack Profiles
Go, Python, Java, Kotlin, React, TypeScript, and more. Pick yours for stack-specific conventions.
## Install
```
npx @c0x12c/ai-toolkit@latest --local
```
## Source
- Repository: https://github.com/spartan-stratos/spartan-ai-toolkit
