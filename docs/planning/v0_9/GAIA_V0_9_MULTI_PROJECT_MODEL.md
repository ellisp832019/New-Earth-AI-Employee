# GAIA v0.9 Multi-Project Model

## Goal

Support multiple approved repositories without weakening isolation.

## Project Record

Each project should define:

- canonical ID;
- display name;
- canonical path;
- repository type;
- allowed inspection capabilities;
- allowed output capabilities;
- excluded paths;
- sensitivity classification;
- approval requirements;
- health rules;
- release rules.

## Example Projects

- MicroGrow
- New Earth Command Dashboard
- New Earth AI Employee
- future New Earth applications

## Isolation Rules

- Each project must be explicitly allowlisted.
- No generic unrestricted filesystem access.
- No cross-project writes.
- No path inference outside canonical project roots.
- No shared approval state across projects unless explicitly modeled.

## Read-Only Exceptions

MicroGrow remains read-only unless a future explicit permission decision allows more.
