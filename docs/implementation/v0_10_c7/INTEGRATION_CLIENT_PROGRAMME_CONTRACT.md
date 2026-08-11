# Integration Client Programme Contract

## Purpose

Extend `packages/gaia_integration_client` with typed models and read methods for the public programme surface.

## Added Model

- `GaiaProgrammeSummaryCounts`
- `GaiaProgrammeSummary`

## Added Methods

- `programmeSummary()`
- `architectureEntities()`
- `architectureEntity()`
- `architectureRelationships()`
- `architectureRelationship()`
- `dependencyGraph()`
- `dependencyFindings()`
- `dependencyCycles()`
- `dependencySharedDependencies()`
- `dependencyOrphans()`
- `dependencyProjectDependencies()`
- `dependencyProjectDependents()`
- `changeImpactSummary()`
- `changeImpactRecommendations()`
- `changeImpactRecommendation()`
- `programmeRoadmap()`
- `releaseTrains()`
- `programmePackages()`
- `programmePackage()`

## Behavior

Parsing is fail-closed for missing or incompatible payloads, and the client remains read-only.
