# Architecture Decision Records & Future Considerations

This document tracks architectural decisions made during the POC build,
the rationale behind them, and what should change for a production implementation.

Format: Each entry records WHAT was decided, WHY, and WHAT TO REVISIT when
moving from POC to production.

---

## ADR-001: Agent Orchestration Framework — Semantic Kernel

**Decision:** Use Semantic Kernel for agent orchestration.
**Alternatives considered:** AutoGen (multi-agent conversation framework).

**Rationale:** This system is a DAG of API calls (ADF SDK, Azure SQL, Power BI REST,
XMLA/TOM), not a multi-agent conversation. Semantic Kernel's plugin/skill model maps
directly to discrete, auditable function calls. AutoGen's conversational loop model
introduces unnecessary complexity and harder-to-audit execution paths for this use case.

**Future considerations:**
- If the system evolves toward multi-agent reasoning (e.g., agents debating schema
  designs before proposing), revisit AutoGen or a hybrid approach.
- Monitor Semantic Kernel's roadmap — Microsoft is actively developing it alongside
  Fabric. Tight Azure integration is a benefit now but a lock-in risk long-term.
- AutoGen may be worth revisiting for a "schema review" sub-agent that debates
  relationship choices before proposing them to a human.

---

## ADR-002: Environment Separation — Schema-Level Within Single Database

**Decision:** Use schema-level separation (e.g., `raw_dev`, `staged_dev`, `raw_prod`)
within a single Azure SQL Database for Dev/Test/Prod isolation.

**Rationale:** Minimizes cost on free/low-tier Azure SQL. Sufficient for a single-developer
POC where blast radius is controlled. Avoids managing multiple database instances.

**Future considerations:**
- **Production must use separate databases** (ideally separate resource groups) for:
  - True network isolation and independent RBAC
  - Independent backup/restore without cross-environment risk
  - Separate performance tiers (dev can be free tier, prod needs DTUs)
  - Compliance requirements (healthcare data may require physical separation)
- Schema-level separation offers zero protection against a misconfigured connection
  string writing dev data to prod tables. In production, use Azure Private Endpoints
  and separate service principals per environment.
- HIPAA/healthcare compliance will likely require database-level or resource-group-level
  isolation. Schema separation will not pass an audit.

---

## ADR-003: Data Ingestion — Scheduled CSV Pickup (POC)

**Decision:** Start with CSV file pickup from a designated folder on a schedule.
Architecture the ingestion layer with a plugin/adapter pattern so API-based and
streaming sources can be added without rewriting the pipeline.

**Rationale:** Simplest possible first rep. Most healthcare clients in the small business
segment still deliver data via file drops (SFTP, SharePoint, email attachments).

**Future considerations:**
- Production ingestion should support: SFTP, SharePoint (via Power Automate trigger),
  REST API polling, HL7/FHIR endpoints, flat file watch folders.
- Consider GoAnywhere or a managed file transfer (MFT) tool for clients with
  compliance requirements around file transfer auditing.
- Power Automate is the natural SharePoint trigger layer — it watches the folder
  and either copies to Blob Storage or triggers an ADF pipeline. ADF cannot natively
  watch SharePoint.
- For API-based healthcare data (claims feeds, EHR extracts), build a generic
  API poller adapter that the ingestion plugin system can consume.

---

## ADR-004: Semantic Model Construction — XMLA/TOM via PPU

**Decision:** Use XMLA read/write via TOM (Tabular Object Model) for programmatic
semantic model construction. PPU license ($24/user/month) is available.

**Rationale:** Full programmatic control over semantic model: tables, columns,
relationships, measures, hierarchies. Most direct path to automated model construction.

**Future considerations:**
- **Fabric Notebooks + Semantic Link Labs** (`sempy_labs`) is Microsoft's long-term
  direction for programmatic semantic model management. When mature, it may replace
  direct TOM/XMLA usage.
- TMDL (Tabular Model Definition Language) is the successor to TMSL/BIM. YAML-like,
  human-readable, git-friendly. Consider TMDL as the serialization format for model
  definitions stored in source control.
- .bim file manipulation + Power BI REST API import is more portable (no XMLA
  dependency) but less capable. Keep this as a fallback path.
- Monitor FabCon Atlanta (March 2026) for announcements on Fabric notebook
  capabilities that may shift the build-vs-buy calculus.

---

## ADR-005: Report Delivery — PBIX Template Library

**Decision:** Use a library of pre-built PBIX template files per report archetype.
The agent selects the appropriate template and injects the data model via API.

**Rationale:** Power BI REST API cannot programmatically define visuals, axis bindings,
colors, or layouts. Template-based approach is the practical ceiling for automation.

**Future considerations:**
- Microsoft is investing in natural language report generation (Copilot in Power BI).
  If/when this becomes API-accessible, it could supplement or replace templates.
- Templates are defensible IP — each template encodes domain expertise about how
  healthcare data should be visualized.
- Consider Paginated Reports (RDL) for compliance/regulatory reporting where pixel-
  perfect layout matters. These have better programmatic generation support.
- Template versioning and migration strategy needed when underlying schema evolves.

---

## ADR-006: Optimization Target — Consulting Delivery

**Decision:** Optimize the system for consulting delivery: flexibility, manual override
capability, per-client customization hooks.

**Rationale:** POC is proving out a consulting practice, not a SaaS product. Consulting
values adaptability per engagement over zero-touch repeatability.

**Future considerations:**
- If converting to product: remove manual override hooks, add multi-tenancy,
  build self-service onboarding, add usage-based billing instrumentation.
- Consulting optimization means the agent should surface choices to the consultant
  (not the end client) at decision points. The consultant is the user, not the
  business stakeholder.
- Document every manual intervention point — these are the product gaps that would
  need closing for a SaaS pivot.

---

## ADR-007: Phase 0 Agent SDK — Anthropic Python SDK (Direct)

**Decision:** Use the Anthropic Python SDK directly (`anthropic` pip package) for Phase 0, bypassing Semantic Kernel.

**Rationale:** ADR-001 selected Semantic Kernel for production orchestration (ADF, Azure SQL, Power BI REST, XMLA/TOM plugins). However, Phase 0 is a single-agent loop — read CSVs, call Claude, write artifacts. Semantic Kernel adds plugin registration, kernel config, and service abstraction overhead that slows down the first working iteration. The Anthropic SDK's tool runner and structured outputs handle Phase 0's needs directly. Claude Opus 4.6 with adaptive thinking is used for the inference call; structured JSON output (`output_config.format`) guarantees parseable artifacts.

**Future considerations:**
- Re-introduce Semantic Kernel in Phase 1 when there are multiple agents (ingestion, schema, model, report) that need to be orchestrated as plugins with shared kernel state.
- The schema agent's Claude API call will become one Semantic Kernel plugin among several — the interface contract (CSV profiles in, DDL/relationships/TMDL/checklist out) is already defined and won't change.
- Monitor Semantic Kernel's Anthropic connector support — as of early 2026 it is less mature than the Azure OpenAI connector. May need a custom connector for Phase 1.

---

## General Technical Debt (POC → Production)

| Area | POC Shortcut | Production Requirement |
|------|-------------|----------------------|
| Auth | Local credentials / env vars | Azure Key Vault + Managed Identity |
| Logging | Console / file logs | Azure Monitor + Log Analytics |
| Error handling | Fail-and-log | Dead letter queues + retry policies + alerting |
| Secrets | .env files | Key Vault references, zero secrets in code |
| Data privacy | No PII masking | Column-level encryption, dynamic data masking |
| Networking | Public endpoints | Private endpoints + VNet integration |
| Monitoring | Manual checks | Azure Monitor dashboards + alert rules |
| Backup | Manual exports | Automated backup + point-in-time restore |
| Multi-tenancy | Single client | Tenant isolation (database or schema per client) |
| Healthcare compliance | None | HIPAA BAA, audit logging, access reviews |
