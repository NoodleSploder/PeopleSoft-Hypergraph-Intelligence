You are continuing development on the **DeathStar / PeopleSoft Explorer** project.

Before changing code, read these files in the repository root:

1. `ARCHITECTURE.md`
   - Use this for the overall system architecture, design principles, provider contracts, naming conventions, and long-term platform direction.

2. `ROADMAP.md`
   - Use this to stay aligned with current implementation status and remaining work.
   - Do not turn this file into a changelog.
   - Keep it concise and status-oriented.

3. `DEVELOPMENT_DIARY.md`
   - Use this as the chronological engineering journal.
   - Record meaningful code changes, discoveries, fixes, verification steps, blockers, and next steps here.

Your job is to continue development while keeping all three documents synchronized.

## Documentation rules

When you complete meaningful work:

- Update `ROADMAP.md` if current status or remaining work changed.
- Append a dated entry to `DEVELOPMENT_DIARY.md` describing:
  - What was changed
  - Why it was changed
  - Files/modules touched
  - Database/table discoveries
  - API/UI behavior added or changed
  - Bugs fixed
  - Verification performed
  - Blockers or limitations
  - Recommended next step
- Update `ARCHITECTURE.md` only when a design principle, provider contract, subsystem boundary, or architectural rule changes.

Do not duplicate large blocks between the files.

Use this separation:

- `ARCHITECTURE.md` = system design and rules
- `ROADMAP.md` = current status and future work
- `DEVELOPMENT_DIARY.md` = chronological engineering history

## Development priorities

Continue from the current roadmap. Prioritize:

1. Component UOM completion
2. Page UOM completion
3. Portal Registry / Content Reference Explorer
4. Portal security explanation
5. Scheduled graph snapshots and retention pruning
6. Runtime graph visualization
7. Richer Knowledge Graph UI
8. SQL object explorer, if metadata grants allow it

Respect blockers already recorded in the roadmap and diary.

## Coding rules

- Preserve the existing architecture.
- Prefer provider-based connectors.
- Keep all database access grant-aware.
- Gracefully degrade when PeopleSoft tables or Oracle views are not accessible.
- Do not assume every PeopleTools environment has the same table structure.
- Use metadata helpers such as `has_table()`, `has_column()`, `select_existing_columns()`, and existing warning models where available.
- Do not hardcode schema assumptions unless verified.
- Keep REST APIs read-only unless the project explicitly defines otherwise.
- Keep object pages canonical and UOM-driven where possible.
- Add warnings instead of crashing when metadata is unavailable.
- Avoid breaking existing endpoints.

## Verification expectations

After code changes:

- Run available syntax checks/tests.
- Start or reload the API if appropriate.
- Verify affected endpoints with `curl`.
- Verify affected admin pages in the browser where possible.
- Confirm graceful degradation for missing grants.
- Record verification results in `DEVELOPMENT_DIARY.md`.

## Working style

Work in small, coherent slices.

For each slice:

1. Inspect relevant existing code.
2. Identify the intended architecture from `ARCHITECTURE.md`.
3. Implement the smallest complete vertical slice.
4. Verify it.
5. Update `ROADMAP.md` and `DEVELOPMENT_DIARY.md`.
6. Leave the repository in a runnable state.

Do not make broad rewrites unless necessary.

When unsure, prefer the existing project patterns over inventing new ones.