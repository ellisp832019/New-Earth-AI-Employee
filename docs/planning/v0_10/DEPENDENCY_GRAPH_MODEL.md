# Dependency Graph Model

## Purpose

The dependency graph is a deterministic graph derived from approved project contracts and architecture records.

## Supported Queries

- direct dependencies;
- transitive dependencies;
- reverse dependencies;
- shared dependency detection;
- dependency cycles;
- critical dependency chains;
- orphaned architecture components;
- unsupported dependencies;
- version or contract relationships.

## Edge Model

Each edge should include:

- stable edge id;
- source entity;
- target entity;
- relationship type;
- provenance;
- freshness;
- confidence or evidence level;
- version or contract constraint when relevant.

## Determinism Rule

The graph engine must build the same graph for the same approved inputs. LLMs may explain the graph, but they do not author the canonical structure.
