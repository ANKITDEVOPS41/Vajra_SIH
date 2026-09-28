# VAJRA Agent Guide

This file guides coding agents working in this repository. It does not install
skills; the local skill definitions are in `.agents/skills/`. Read a relevant
`SKILL.md` when the task calls for it, and follow the host agent's higher-priority
instructions.

## Start Here

- Read `README.md` and `data/manifests/DATA_MANIFEST.md` before pipeline work.
- Read `docs/PEER_REPOSITORY_AUDIT.md` before importing peer code or claims.
- The active API is `backend/app/main.py` through `backend/main.py`; the active
  frontend is `frontend/src/App.tsx`. `backend/legacy_main.py` is not mounted.
- Inspect `git status` first. This working tree may contain valuable uncommitted
  work. Never reset or overwrite it to make a task look clean.

## Scientific And Product Gates

- Preserve the location-first chain: issue-time observations, QC, detection,
  tracking, forecast geometry, spatial intersection, then ETA. An ETA requires
  a valid forecast-to-location intersection and explicit provenance.
- The bundled SEVIR VIL replay is an un-georeferenced U.S. pixel field. Never
  place it on the India map or compute a Jaydev Vihar ETA from it.
- The Bhubaneswar replay and its baseline ETA are `SIMULATED`. Keep that label
  visible in APIs, tests, and UI. Do not promote a prototype checkpoint or an
  unverified peer evaluation report to operational model skill.
- Require actual aligned data before claiming IR107/INSAT fusion. Metadata,
  synthetic fallback values, and matching array shapes are not proof of an
  observed, co-registered thermal channel.
- Hazard screens must expose method, threshold, evidence, and uncertainty
  status. Do not invent hail/cloudburst probabilities or calibrated confidence.
- Do not use observations after the forecast issue time in inference, QC, or
  training samples presented as issue-time-safe.

## Where To Work

- Keep active API schemas in `backend/app/schemas/`, pipeline services in
  `backend/app/services/`, and reusable science functions in
  `backend/app/science/`. Add focused tests in `backend/tests/`.
- Keep the location contract in `backend/app/schemas/location.py` and the
  intersection/ETA engine intact unless a requested change has focused tests.
- Preserve the working dashboard in `frontend/src/App.tsx`. Integrate peer UI
  only when it adds a tested, provenance-safe feature.
- Keep datasets, checkpoints, NumPy arrays, credentials, `node_modules/`, and
  `dist/` outside Git tracking. Check `.gitignore` before adding artifacts.

## Skill Routing

- New behavior or interface: `.agents/skills/brainstorming/SKILL.md`, then
  `.agents/skills/implement/SKILL.md` or
  `.agents/skills/test-driven-development/SKILL.md`.
- Unfamiliar module or architecture change:
  `.agents/skills/repo-intake-and-plan/SKILL.md` and
  `.agents/skills/codebase-design/SKILL.md`.
- Bug investigation: `.agents/skills/systematic-debugging/SKILL.md`.
- Git or peer-repository merge: `.agents/skills/git-guardrails/SKILL.md` and
  `.agents/skills/code-review/SKILL.md`.
- Frontend changes: `.agents/skills/frontend-design/SKILL.md`; finish with
  `.agents/skills/web-design-guidelines/SKILL.md` and browser verification.
- Before completion: `.agents/skills/verification-before-completion/SKILL.md`.
  Use only the skills that materially fit the task; the inventory is not a
  checklist to run every time.

## Verification

- Backend: `pytest backend/tests/ -q` from the repository root.
- Frontend: `npm run build` and `npm run lint` from `frontend/` when it changes.
- For map, replay, or location UI changes, exercise both baseline and learned
  modes in a real browser. Confirm the learned India ETA remains gated unless
  georeferencing and temporal alignment have been established.
- Report any tests not run, remaining evidence gaps, and changes to model/data
  provenance. Do not claim validation from a green unit-test suite alone.
