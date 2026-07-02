# Testing conventions

1. **Test where behavior emerges.** The primary surface is the level at which behavior actually
   arises from components working together, not isolated units. Most defects live in *wiring* — how
   parts compose — not in algorithms. Reserve isolated unit tests for components with real internal
   logic or pure functions.

2. **Fake only the costly boundary.** Substitute exactly the dependencies that are expensive, remote,
   or nondeterministic; run everything else for real. A test that fakes anything beyond that boundary
   is mocking away the code it is meant to verify. Each layer fakes one seam — no more.

3. **Prefer real, ephemeral infrastructure over fakes.** Where a real dependency can be run cheaply in
   a throwaway instance (a container, an in-process harness, a temp directory), do that instead of a
   stand-in. A fake that drifts from production behavior is worse than no test.

4. **Fakes are explicit and per-test.** Configure a fake in the test that uses it, with the exact
   scenario that test needs. Build canned data with functions that return fresh instances — never
   shared mutable fixtures, which let tests alias one another's state.

5. **Unhappy paths are part of the contract.** Failure, skipped, and cancelled behavior are tested
   alongside the happy path, not deferred.

6. **Pragmatic test-first.** Write the test first wherever there is a *contract* or a *branch*; there,
   red-green-refactor pins the contract before the code exists. Test incidental glue and chrome
   afterward. Do not ritually TDD boilerplate.
