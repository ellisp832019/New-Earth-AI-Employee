# GAIA v0.10 Test Strategy

## Goals

The test strategy must prove that programme intelligence is deterministic, read only where required, and still compatible with v0.9 surfaces.

## Required Test Areas

- unit tests for contract, registry, graph, impact, roadmap, release-train, and package services;
- repository or service tests for deterministic record revisioning;
- API tests for read models and compatibility routes;
- CLI tests for new programme commands;
- migration tests for schema and backward compatibility;
- determinism tests for identical-input identical-output behavior;
- graph tests for traversal, reverse lookup, and cycle detection;
- impact tests for direct, transitive, and unknown states;
- staleness tests for freshness aggregation;
- approval tests for revision locking and immutable approved records;
- Windows widget tests for programme workspace layout;
- integration-client tests for typed read models;
- Dashboard module tests for read-only summaries;
- cross-repository conformance tests;
- security-boundary tests;
- release-acceptance tests.

## Failure Cases

The strategy must explicitly test:

- missing project;
- missing dependency;
- dependency cycle;
- stale snapshot;
- conflicting contract;
- unknown interface version;
- unavailable repository;
- invalid change proposal;
- superseded programme package;
- approved old revision;
- Dashboard backend unavailable.
