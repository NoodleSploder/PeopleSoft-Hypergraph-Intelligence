# PeopleSoft Explorer Roadmap

## Vision

PeopleSoft Explorer is evolving into a complete operational intelligence platform for PeopleSoft.

The long-term objective is to provide a unified interface for:

- Metadata exploration
- Dependency analysis
- Runtime observability
- Environment comparison
- Security analysis
- Operational tooling
- AI-assisted engineering workflows

---

# Current Status

## Platform Status

The following major subsystems are considered production-ready:

- Unified Object Model (UOM)
- Object Explorer
- Graph Explorer
- Knowledge Graph
- Environment Compare
- Runtime Monitor
- SQL Workspace
- Integration Broker Explorer
- Identity Management
- Oracle ASH Integration
- Runtime Alerts
- Application Package Explorer
- Component Interface Explorer
- Portal Explorer
- Version-aware metadata adapters

Development focus now shifts from feature parity toward platform intelligence.

---

# Phase 4 — Runtime Intelligence

## Live Session Explorer

Provide complete end-to-end session visibility.

Features:

- Browser session tracking
- WebLogic session tracking
- App Server tracking
- Oracle session tracking
- SQL execution
- Wait events
- Lock analysis
- Integration Broker activity
- Process Scheduler linkage

---

## Runtime Timeline

Persist runtime snapshots.

Support:

- Runtime history
- Process history
- Queue depth history
- Alert history
- Oracle ASH history
- Trend graphs

---

## Runtime Topology

Interactive infrastructure topology.

Visualize:

- Browser
- nginx
- WebLogic
- App Server
- Process Scheduler
- Oracle
- Integration Broker
- OpenSearch

with live status indicators.

---

## Incident Recording

Capture complete runtime incidents.

Support replay for troubleshooting.

---

# Phase 5 — Complete Knowledge Graph

Continue expanding object coverage.

Remaining providers include:

- Message Catalog
- Approval Framework
- XML Publisher
- BI Publisher
- WorkCenters
- Dashboards
- Search Definitions
- Search Categories
- Homepage Tiles
- Navigation Collections
- Event Mapping
- Drop Zones
- Related Content
- Branding
- Page Composer

---

## Relationship Expansion

Continue enriching graph relationships.

Current work:

- Shared UOM relationship graph helper introduced for Tree, Component Interface, and Page providers.
- Continue migrating mature UOM providers from ad hoc graph loops to declarative relationship specs where behavior can be preserved.
- Align UOM `_relationships`, UOM `_graph`, and Knowledge Graph ingestion around one relationship vocabulary.

Examples:

- CALLS
- REFERENCES
- USES
- WRITES
- READS
- CONTAINS
- WRAPS
- SECURES
- GENERATES
- DEPLOYS

---

## Complete Cross References

Every object should answer:

- What references me?
- What do I reference?
- Who executes me?
- Who secures me?
- What breaks if I change?

---

# Phase 6 — Environment Intelligence

## Continuous Drift Detection

Automatically detect:

- New objects
- Deleted objects
- Changed PeopleCode
- Changed SQL
- Changed Security
- Changed Menus
- Changed Trees
- Changed Integration Broker metadata

---

## Environment History

Maintain historical snapshots.

Support:

DEV

↓

TEST

↓

UAT

↓

PROD

Track promotion history and differences.

---

## Impact Forecasting

Predict downstream impact before migration.

Examples:

- affected components
- affected security
- affected runtime
- affected integrations
- dependency risk

---

# Phase 7 — AI Engineering Assistant

Leverage the knowledge graph for engineering assistance.

## Natural Language Search

Examples:

- Where is employee termination implemented?
- Show every SQL touching PS_JOB.
- Which AEs update JOB?
- Which Components use this record?

---

# Phase 8 — Platform Extensibility

## Plugin SDK

Support:

- Custom object providers
- Custom graph providers
- Custom runtime providers
- Custom dashboards
- Custom health checks
- Organization-specific plugins
- Third-party integrations

---

# Phase X — Digital Twin Persistence

Persist everything.

Support:

- historical runtime
- graph snapshots
- deployment history
- configuration history
- security history
- runtime replay
- change history

The platform evolves from a live explorer into a persistent Digital Twin of the PeopleSoft enterprise.

---

## Root Cause Analysis

Correlate:

- Runtime
- Graph
- Oracle ASH
- Alerts
- Deployments

Answer:

Why did this happen?

---

## Change Risk Analysis

Given a project:

Predict:

- affected objects
- affected users
- deployment risk
- runtime impact

---

## Architecture Assistant

Generate:

- dependency reports
- sequence diagrams
- technical documentation
- impact summaries
- architecture documentation

---

# Long-Term Goals

PeopleSoft Explorer should become the definitive engineering, observability, and operational intelligence platform for PeopleSoft environments.
