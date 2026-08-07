# Prioritisation Policy

The B3 policy version is `gaia-v0.9-b3-v1`.

## Deterministic factors

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

## Tier meaning

- `P0`: immediate integrity, safety, or blocking condition;
- `P1`: high-impact issue requiring prompt attention;
- `P2`: important planned work with meaningful impact;
- `P3`: normal improvement or maintenance;
- `P4`: low urgency or informational candidate.

## Policy rules

- same evidence plus same policy version yields the same score and tier;
- the score is explainable from explicit contributions;
- hidden model prompts do not determine the canonical priority.
