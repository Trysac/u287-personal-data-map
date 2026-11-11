# 0001 — Record architecture decisions

- Status: accepted
- Date: 2026-01-01

## Context

Design choices that are not obvious from the code should stay discoverable as the project grows.
Reviewers need to know why a limit or a default exists, and future changes should justify themselves
against the original reasoning.

## Decision

Record every significant design choice as a numbered ADR in `docs/decisions/`, using the filename
pattern `NNNN-short-title.md`. Each record states its context, the decision and the consequences.

## Consequences

- The reasoning behind defaults such as the 5 MiB input bound, the 32-level parenthesis limit and
  the priority order of `DEFAULT_RULES` is written down once instead of re-litigated per change.
- Adding an option or dependency requires a new ADR in the same pull request.
