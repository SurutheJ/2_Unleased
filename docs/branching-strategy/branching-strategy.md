# Branching Strategy

## Branches

- **`main`** — always deployable. Nothing gets committed to `main`
  directly; it only receives merges from feature branches once they're
  working and reviewed.
- **`feature/<short-description>`** — one branch per feature or task,
  e.g. `feature/production-config`, `feature/listing-search`,
  `feature/inquiry-flow`. Branched off the latest `main`.
- **`fix/<short-description>`** — for bug fixes, same pattern as feature
  branches.

## Workflow

1. Pull the latest `main`:
   ```
   git checkout main
   git pull origin main
   ```
2. Create a branch for the task:
   ```
   git checkout -b feature/your-feature-name
   ```
3. Commit early and often with meaningful messages (what changed and why,
   not just "fix stuff").
4. Push the branch and open a Pull Request into `main`:
   ```
   git push -u origin feature/your-feature-name
   ```
5. At least one other teammate reviews the PR before it's merged —
   catches bugs early and keeps everyone aware of what's changing.
6. Merge into `main` (prefer a regular merge or squash-merge to keep
   history readable), then delete the feature branch.

## Commit message convention

Short summary line (~50 chars), imperative mood, optionally followed by
a blank line and more detail:

```
Add visit-slot booking endpoint

Seekers can now book an open VisitSlot on an accepted inquiry.
Rejects double-booking with a 409 if the slot was taken concurrently.
```

Prefixes we use loosely: `Add`, `Fix`, `Refactor`, `Docs`, `Chore`.

## Why this matters for this project

This exact pattern — branch off `main`, commit, merge back — is what
`feature/production-config` in this repo demonstrates: the settings
split, `.env` setup, and docs in this PR were all done on that branch
and merged into `main` rather than committed straight to `main`.
