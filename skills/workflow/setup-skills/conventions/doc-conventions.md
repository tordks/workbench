# Documentation conventions

1. **No meta-commentary.** Docs say what something does, and why a non-obvious decision holds — never
   issue or task IDs, PR or session narrative, or "why this change was made." That context belongs in
   the tracker, not in files that outlive the work.

2. **Single source of truth — minimize blast radius.** Each fact has one home; everywhere else refers
   to it by stable name, not by number or position. A fact restated where it can drift from its
   source is a defect, as is an unstable identifier (an ADR number, a line or position) cited away
   from the place that owns the decision.

3. **Docstrings stay in their own unit.** A docstring describes only its unit's contract — purpose,
   parameters, return, invariants, and the non-obvious *why*. It does not narrate a collaborator,
   caller, or downstream module. A fact that already has a home — a domain term in the glossary, a
   decision in an ADR, a shape in the contracts module — is referenced by stable name, never copied.
   Favour *why* over *what*; the code and types already state the *what*.

4. **No staleness.** A docstring or comment must still match the code it describes.
