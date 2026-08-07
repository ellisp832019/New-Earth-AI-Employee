# Scoring Model

B3 scores recommendations with explicit numeric contributions.

## Score breakdown

Each recommendation exposes:

- severity contribution;
- urgency contribution;
- user impact contribution;
- release impact contribution;
- safety impact contribution;
- dependency impact contribution;
- confidence contribution;
- effort contribution;
- reversibility contribution;
- freshness contribution;
- total score.

## Current implementation rule set

- blocking health conditions and root-unavailable states can reach `P0`;
- stale evidence lowers actionability unless the recommendation is specifically about refreshing evidence;
- dependency relationships increase the score slightly but also make blocked recommendations visible;
- effort and reversibility make small deterministic adjustments, but they do not override blocking conditions.

## Explainability

Each record stores the score breakdown so a reviewer can see why one item outranks another.
