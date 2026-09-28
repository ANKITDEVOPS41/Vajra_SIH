---
name: vercel-react-best-practices
description: React and Next.js performance optimization from Vercel Engineering. Source - vercel-labs/agent-skills (743K+ installs)
---
# Vercel React Best Practices
## When to Use
- Writing React components or Next.js pages
- Data fetching, bundle optimization, performance improvements
## Core Principles
1. Component Structure - proper composition and separation of concerns
2. Hook Usage - correct hooks without mystery side effects
3. Prop Interfaces - well-defined, typed interfaces
4. Data Fetching - server-side when possible
5. Error Boundaries - robust error handling
6. Bundle Size - minimize and optimize
7. Server Components - leverage RSC effectively
8. Streaming - Suspense for better UX
9. Caching - appropriate strategies
## Anti-Patterns
- Components that work in isolation but break in context
- Unnecessary re-renders
- Client-side fetching when server-side is possible
- Missing error boundaries
- Prop drilling when context is appropriate
## Source
- Repository: https://github.com/vercel-labs/agent-skills
