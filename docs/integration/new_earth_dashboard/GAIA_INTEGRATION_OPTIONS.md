# GAIA Integration Options

## Option A: Direct Dependency on Official GAIA Flutter Packages

Pros:

- Smallest number of moving parts.
- Reuses the released packages directly.
- Fastest to prototype.

Cons:

- Can leak GAIA package assumptions into Dashboard UI code.
- Makes Dashboard route ownership less clear.
- Harder to keep a Dashboard-specific feature flag and adapter boundary.

## Option B: Thin Dashboard-Owned Adapter Around Official GAIA Packages

Pros:

- Best fit for the current Dashboard architecture.
- Keeps route ownership, feature flags, and UI policy in the Dashboard repo.
- Keeps GAIA packages as the backend-facing contract.
- Makes stale-data, trust-alert, and capability state explicit in one place.

Cons:

- Slightly more code than a raw direct dependency.
- Requires a small adapter layer and a dedicated test harness.

## Option C: Process-Isolated or Deep-Link Integration with the Standalone Control Centre

Pros:

- Strongest isolation boundary.
- Simplifies security arguments if Dashboard integration stays minimal.

Cons:

- More awkward user experience.
- More platform-specific process handling.
- Higher release coupling to the standalone control centre app.

## Recommendation

- Primary: Option B.
- Fallback: Option C.

Reason:

The Dashboard already uses a structured shell, Riverpod state, and route-gated workflows. A thin adapter gives the safest integration seam without forcing the Dashboard to become a second GAIA control centre.
