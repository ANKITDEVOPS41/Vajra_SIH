---
name: test-driven-development
description: Strict RED-GREEN-REFACTOR TDD cycle. NEVER writes implementation before a failing test. Source - obra/superpowers
---
# Test-Driven Development
## The Cycle
1. RED - Write a failing test first
2. GREEN - Write minimum code to pass
3. REFACTOR - Clean up while keeping tests green
## Rules
- NEVER write implementation before a failing test
- Each test tests ONE thing
- Tests must be deterministic and fast
- Test behavior, not implementation details
## Anti-Patterns
- Writing tests after implementation
- Patching tests to pass instead of fixing code
- Skipping refactor step
- Over-mocking
- Testing private methods directly
## Source
- Repository: https://github.com/obra/superpowers
