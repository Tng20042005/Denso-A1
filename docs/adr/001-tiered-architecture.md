# ADR-001: T0 core, T1 baseline, T2 deferred

- Status: Accepted for prototype
- Date: 2026-10-07

## Decision

Implement T0 physics-informed injection and T1 simple augmentation first. Keep
learned T2 generators out of scope until G3 shows a valid baseline comparison.

## Rationale

The project has no DENSO fault data and the plan prioritizes experimental
validity over model complexity. T0 is parameterized and auditable; T1 is a
budget-matched control.

## Consequences

The current result is a reproducibility and mechanism artifact. It cannot
support a DENSO-specific claim.
