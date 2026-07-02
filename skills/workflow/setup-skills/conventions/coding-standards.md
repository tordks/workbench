# Coding standards

## Design

1. **Separation of concerns.** Each module owns one concern and is the only place that concern is
   implemented. Cross-cutting machinery — frameworks, orchestration, transport, I/O — is kept out of
   the code that expresses domain logic.
2. **Orthogonality.** Independent things stay independent: changing one decision must not force
   lockstep edits elsewhere. Small blast radius is how orthogonality is measured; when two modules
   must always change together, suspect a missing seam.
3. **Deep modules / information hiding.** Prefer a simple interface over a large implementation: hide
   each hard decision behind a narrow interface so callers depend on *what* a module does, not *how*.
4. **DRY — one source of truth, not one copy of text.** Every *fact* has a single authoritative home;
   everything else points to it by stable name. Code that is incidentally identical but changes for
   different reasons is not duplication; collapsing it couples two concerns.
5. **YAGNI.** Build for the requirement in front of you. Indirection with a single implementation, a
   config knob nobody sets, an abstraction "for later" — blast radius with no payoff. Delete them.

## Code

1. **One contract definition, reused across boundaries.** Define each data shape once and reuse it
   across module, storage, and API boundaries rather than re-declaring it per layer.
2. **Generated over hand-authored at boundaries.** Where a contract crosses a language or process
   boundary, generate the far side from the canonical source and check it in; fail CI if it is stale.
3. **Keep the framework at the edge.** Domain logic is plain, independently-callable functions.
   Coupling to a framework or orchestrator lives in thin wrappers at the boundary, never in the core.
4. **Dependencies are passed in, not reached for.** Inject collaborators as arguments so they are
   visible in signatures and substitutable. Avoid module-level globals and monkeypatching.
5. **Determinism is designed in.** Anything feeding an identity or cache key serializes canonically.
   Impure inputs — the clock, randomness — are injected, not reached for ambiently.
6. **Strict typing, enforced.** Static types are checked in CI.
7. **Match the surrounding idiom.** New code reads like the code around it — comment density, naming,
   and structure follow the file it lands in.

Mechanical style — line length, import order, formatting, lint rules — follows the repo's own
formatter and linter config; it is not restated here.
