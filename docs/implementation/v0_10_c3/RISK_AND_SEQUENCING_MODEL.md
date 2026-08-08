# Risk and Sequencing Model

## Structural Risk

Risk is deterministic and structural only.

It considers:

- direct impacted entity count;
- transitive impacted entity count;
- affected project spread;
- affected contract count;
- affected release count;
- affected work package count;
- unresolved or unknown findings;
- cycle involvement;
- shared dependency breadth;
- project criticality;
- stale or unavailable evidence.

## Risk Scale

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`
- `UNKNOWN`

Unknown evidence prevents a false low classification.

## Sequencing Constraints

Sequencing constraints are derived directly from dependency structure.

They describe prerequisites such as:

- provider update before consumer validation;
- shared schema update before downstream verification;
- release metadata confirmation before release-related validation.

This is not a roadmap or release-train planner.
