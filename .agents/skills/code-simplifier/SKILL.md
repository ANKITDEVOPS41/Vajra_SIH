---
name: code-simplifier
description: Takes recently modified code and makes it cleaner without changing behavior. Follows project conventions from CLAUDE.md. Source - anthropics/skills
---
# Code Simplifier
## Overview
Focused on one thing: take recently modified code and make it cleaner without changing what it does.
## Rules
- NEVER change behavior, only how behavior is expressed
- Will not refactor logic or suggest architecture changes
- Cleans up code you just wrote and moves on
- Follows project conventions from CLAUDE.md
## What It Catches
- Nested ternaries
- Functions doing three things at once
- Abstractions that do not make sense
- Overly compact logic
- Nested conditionals
## Source
- Repository: https://github.com/anthropics/skills
