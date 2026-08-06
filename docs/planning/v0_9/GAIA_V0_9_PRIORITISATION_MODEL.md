# GAIA v0.9 Prioritisation Model

## Deterministic Factors

- severity;
- urgency;
- user impact;
- release impact;
- safety impact;
- dependency impact;
- confidence;
- effort;
- reversibility;
- evidence freshness.

## Scoring Principle

The score must be explainable. A user should be able to read why one item outranks another.

## Suggested Output Fields

- priority tier;
- numeric score;
- rationale;
- supporting evidence;
- blockers;
- dependencies;
- reasons not to proceed yet.

## Anti-Patterns

- opaque model-only scoring;
- hidden weight changes;
- recommendations without evidence;
- recommendations that ignore risk or reversibility.
