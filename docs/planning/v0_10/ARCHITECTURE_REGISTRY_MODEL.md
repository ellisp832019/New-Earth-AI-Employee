# Architecture Registry Model

## Purpose

The Architecture Registry is the organisation-wide catalog of shared engineering entities. It is a traceability layer, not a free-form knowledge dump.

## Entity Kinds

- projects;
- services;
- APIs;
- packages;
- libraries;
- firmware;
- hardware;
- protocols;
- databases;
- local services;
- user interfaces;
- integration clients;
- schemas;
- release contracts.

## Canonical Fields

- stable entity id;
- entity kind;
- name;
- owning project or domain;
- repository or source reference;
- revision id;
- current status;
- provenance;
- freshness policy;
- relationship references.

## Registry Rules

- Every entity must have stable identity and provenance.
- Entities should be as small and typed as possible.
- A relationship is a first-class record, not a comment on the entity.
