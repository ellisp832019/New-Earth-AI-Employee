# Change Impact Model

## Purpose

The Change Impact Engine evaluates a proposed change before it is implemented and explains which projects, contracts, releases, work packages, and tests are affected.

## Example Inputs

- API change;
- package upgrade;
- schema change;
- firmware protocol change;
- repository restructure;
- release version change;
- hardware interface change;
- shared library modification;
- project contract modification.

## Required Outputs

- directly affected projects;
- transitively affected projects;
- affected architecture entities;
- affected contracts;
- affected releases;
- affected work packages;
- affected tests;
- risk level;
- impact reasons;
- required evidence refresh;
- recommended sequencing;
- unknown or unverified impacts.

## Rule

Unknown remains unknown. Incomplete evidence must not be silently upgraded to safe.
