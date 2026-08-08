# Impact Result Model

## Top-Level Result

`ChangeImpactResult` captures:

- proposal identity and revision fingerprints;
- graph fingerprint;
- direct affected entities;
- transitive affected entities;
- affected projects;
- affected contracts;
- affected releases;
- affected work packages;
- validation references;
- refresh requirements;
- sequencing constraints;
- unknown findings;
- structural risk;
- freshness and trust aggregation;
- provenance references;
- impact fingerprint.

## Result Rules

- Direct impacts and transitive impacts are returned separately.
- Project impacts are projected from entity-level impacts.
- The impact fingerprint is semantic only.
- Generated timestamps do not affect the fingerprint.

## Storage Decision

No persistent impact store is required for C3.

The service is derived, deterministic, and repeatable from canonical source records, so storing duplicate impact state would add drift without adding authority.
