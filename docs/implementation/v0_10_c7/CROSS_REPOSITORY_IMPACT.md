# Cross-Repository Impact

## GAIA C7A

- GAIA C7A merged main: `3a7d316f66aabf9cd677200c55fd5be05a4d6afe`
- GAIA PR: `#30`

## Dashboard C7B

- Dashboard C7B merged main: `67bb0057322ae0d5d7514bdaba5e29258ec3efda`
- Dashboard PR: `#17`

## Boundary

- The Dashboard consumes GAIA only through the supported integration-client and dashboard-module boundary.
- The Dashboard remains read-only and fail-closed for unavailable or incompatible GAIA responses.

## Not Needed for C7

- MicroGrow
- NEOS
- New Earth Platform Core
- Command Centre
