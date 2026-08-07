# Approval State Machine

B4 approval is deliberately narrow.

## States

- `proposed`
- `under_review`
- `approved`
- `rejected`
- `superseded`
- `expired`
- `handed_off`
- `completed`
- `failed`
- `rolled_back`

## Rules

- only the current revision can transition;
- stale packages cannot transition to approval;
- blocked packages cannot be approved or handed off;
- approval decisions are recorded separately from the package row;
- expiry can supersede a live review package.
