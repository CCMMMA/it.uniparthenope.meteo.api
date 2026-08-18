# API Versioning, Deprecation, and Access Governance

## Normative purpose

This document defines how the University of Naples Parthenope Meteo API evolves.
Its purpose is to make technical change observable, reviewable, and reversible
while preserving scientific reproducibility and operational continuity. The
keywords **must**, **should**, and **may** express obligation, recommendation,
and permission respectively.

## Roles and accountability

- The API owner approves public contracts, supported versions, and sunset dates.
- Resource maintainers implement handlers, schemas, parity tests, and migration
  material.
- Security operators review API-key requests, grant least-privilege scopes, and
  perform issuance, rotation, and revocation.
- Service operators monitor reliability, capacity, usage, and deprecation uptake.
- Data stewards review privacy, retention, and scientifically material semantic
  changes.
- Consumers maintain accurate ownership and migrate within announced windows.

One person may occupy several roles, but approval evidence should identify the
role exercised.

## Change classification

Additive optional fields, new endpoints, documentation corrections, and
performance changes that preserve observable semantics may ship within v1.
Removing or renaming fields, changing units or meanings, tightening previously
public access, or changing success/error envelopes requires either an explicitly
documented transition or a new major API version. Scientific changes to model
interpretation must document provenance independently of HTTP compatibility.

## Resource-family promotion

A legacy resource may be declared replaced only when all of the following exist:

1. a functional v1 endpoint using production dependencies;
2. stable authentication and error behavior;
3. local legacy/v1 status, media-type, and payload parity tests;
4. an optional live contract check suitable for deployment validation;
5. endpoint reference, consumer examples, and compatibility-matrix entries;
6. telemetry capable of measuring identified migration where keys are supplied;
7. an operational rollback that leaves the legacy handler available.

Only then may the legacy route emit `Deprecation` and a successor link. Routes
without replacements must not inherit family-wide deprecation headers.

## Sunset decision process

A sunset date requires an owner-approved proposal recording affected routes,
consumer evidence, migration support, risks, rollback, and communication dates.
Operators should observe at least one representative usage cycle and directly
contact identifiable active consumers. The `Sunset` header must be an announced
HTTP-date and must not be configured speculatively. Removal occurs in a distinct
release after the notice period; regression tests then assert `404` for retired
routes. Emergency security action may shorten this process but requires a written
incident record and prompt consumer communication.

## Credential governance

Requests must state identity, purpose, requested scopes, and expected use.
Reviewers may reduce but never expand requested scopes during issuance. Plaintext
keys are disclosed once; stored verifiers use salted scrypt. Consumer keys do not
authorize operator actions merely by holding `keys:admin` or `operations:cache`;
deployments must place administrative interfaces behind the institutional
operator-control boundary as well.

Expired, revoked, and rotated credentials remain auditable. Suspected disclosure
requires immediate rotation or revocation. Secrets and hashes must never enter
logs, documentation, usage events, or analytics exports.

## Telemetry and reporting governance

Usage collection follows data minimization. The event schema intentionally omits
query values, payloads, IP addresses, and user agents. Administrative reports are
bounded and protected by `keys:admin`; their output remains operational data and
must not be published as an open consumer directory. The API owner and data
steward must approve a retention schedule before production collection and review
it periodically. Deletion or aggregation jobs should preserve only the evidence
needed for capacity, security, billing if introduced, and migration decisions.

## Evidence and release gate

Every governed API release should retain a change record, reviewed OpenAPI and
reference documentation, migration notes, database migration instructions,
syntax validation, unit results, and relevant live validation. A release is not
complete when code alone is merged: deployment schema, credentials, observability,
consumer notice, and rollback readiness are part of the same socio-technical
contract.
