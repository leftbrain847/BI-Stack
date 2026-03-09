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

---

## Phase 0 Gap Analysis — Pre-Azure Integration Checklist

Identified gaps before Azure integration. Items are ranked by risk.

### CRITICAL — Resolve Before Azure Integration

#### 1. PHI Handling in Non-Prod Environments
- Dev/test environments must use de-identified or synthetically generated data only.
- Document masking rules before any real data touches Azure, even on a free tier.
- All five CSVs in `data/raw/` are currently synthetic — this must remain true in dev.
- **Action:** Add a `data/raw/README.md` that explicitly prohibits real PHI in this folder and documents the de-identification standard used.

#### 2. Staging Layer (Raw → Staged → Final)
- Raw CSVs should land in a `raw_*` schema untouched, then transform into `staged_*` before populating dim/fact tables.
- Skipping staging makes it impossible to replay a pipeline failure without re-ingesting the source file.
- **Action:** Add `raw_dev`, `staged_dev`, `dw_dev` schemas to the schema generation output. Update ADR-002 to reflect three-layer naming convention.

#### 3. Incremental Load Strategy
- Full reload on every run will not scale and risks duplicate rows without a truncate-reload guard.
- Need a decision: truncate-and-reload vs. merge (upsert) vs. append-with-dedup.
- For most healthcare source files (claims, encounters) a merge on natural key is safest.
- **Action:** Add a load strategy field to `relationships.json` output (`full_reload` | `upsert` | `append`). Let the schema agent recommend per table.

### HIGH PRIORITY

#### 4. Audit Logging
- HIPAA requires logging who accessed what data and when. Not built into SSMS or Power BI by default.
- **Action:** Add an `audit_log` table to the schema output template. Minimum columns: `event_time`, `user_principal`, `table_accessed`, `row_count`, `operation_type`.
- Azure SQL Auditing (built-in) must be enabled on every database that holds PHI — document this as a deployment step.

#### 5. Surrogate Key Strategy
- Natural keys in healthcare (MRN, NPI, ICD code, encounter ID) are unreliable across source systems.
- Need a consistent surrogate key (SK) approach across all dim tables before relationships are generated.
- **Action:** Update `schema_agent.py` system prompt to always generate an `INT IDENTITY(1,1)` SK as the first column on every dimension table. Add SK to `relationships.json` relationship definitions.

#### 6. Slowly Changing Dimension (SCD) Decisions
- Some dims will change over time: patient demographics, provider affiliations, payer contracts.
- No SCD type has been assigned to any dimension.
- **Action:** Add `scd_type` field to the schema agent's dimension output (Type 1 = overwrite, Type 2 = history rows, Type 0 = static). Default to Type 1 in POC; flag Type 2 candidates in the review checklist.

#### 7. Data Quality Validation Post-Load
- No check that row counts and key totals match between source CSV and loaded table.
- Pipeline can silently succeed while dropping rows.
- **Action:** Add a reconciliation step to the pipeline: after load, compare `COUNT(*)` and `SUM()` of numeric key columns between source profile and loaded table. Write results to a `pipeline_audit` table.

### MEDIUM PRIORITY

#### 8. Indexing Plan
- Schema generation produces `CREATE TABLE` with data types but no clustered or non-clustered index decisions.
- Without indexes, Power BI refresh will be slow on any table over ~100K rows.
- **Action:** Update schema agent output to include a `CREATE INDEX` block per table. Cluster on SK for dims; cluster on date + FK for facts. Add NCI on columns flagged as high-cardinality identifiers.

#### 9. Azure Free Tier Limits

**Azure SQL Database**
- The free offer (32 vCore-seconds/second, 32 GB storage) is adequate for schema creation and small test loads but will throttle under any real query load.
- Power BI DirectQuery hits the database on every report interaction — free tier DTU limits will cause timeouts the first time you open a report against a table with more than ~50K rows.
- Import mode (scheduled refresh) is more forgiving but still competes with ADF pipeline writes for connection slots.
- **Upgrade trigger:** Move to Basic ($5/month, 5 DTUs) or S1 ($30/month, 20 DTUs) as soon as Power BI refresh is connected. S1 is the minimum viable tier for concurrent pipeline + report workloads.

**Azure Data Factory**
- ADF has no meaningful free tier for pipeline orchestration. The free 5 activities/month is exhausted by a single test run.
- ADF is billed per activity run (~$0.001) and per DIU-hour for data movement. A simple CSV-to-SQL pipeline costs pennies per run, but it is not free.
- For POC scheduling, consider **Azure Logic Apps** (first 4,000 actions/month free) or a local cron job calling the existing `run.py` script via Azure VM/Function to defer ADF cost.
- **Upgrade trigger:** Introduce ADF when you need dependency chaining between pipeline steps (e.g., blob arrival → profile → load → refresh) or when you need the visual monitoring and retry UI. Don't pay for it to run a single script on a schedule.

**Azure Blob Storage**
- Free tier (5 GB LRS, 12 months) is sufficient for CSV staging at POC data volumes.
- At ~1 MB per synthetic CSV file, you have headroom for thousands of runs before hitting limits.
- Cost after free tier is negligible (~$0.02/GB/month for LRS). Not a constraint.

**Azure Functions (alternative to ADF for scheduling)**
- Consumption plan: first 1 million executions/month free, then $0.20/million.
- A Functions-based trigger (blob trigger on new file → call `run.py` logic) is a cost-effective ADF substitute for POC and can be refactored into ADF pipelines later without changing business logic.

**Realistic POC monthly cost beyond free tier:**
| Service | Tier | Est. Monthly Cost |
|---------|------|-------------------|
| Azure SQL | S1 | ~$30 |
| Blob Storage | LRS | <$1 |
| ADF (if used) | Pay-per-use | ~$5–$15 |
| Azure Functions (ADF alternative) | Consumption | ~$0 |
| **Total** | | **~$30–$45/month** |

- **Action:** Start with Azure Functions (not ADF) for scheduling to stay near-free. Document the ADF migration path for when monitoring and dependency management justify the cost. Pin the Azure SQL tier decision to the first Power BI connection attempt.

#### 10. Azure Access Control / IAM Plan
- No documented plan for which service principals or users can read raw files vs. processed data.
- **Action:** Define three roles before deployment: `bi-stack-ingest` (ADF pipeline SP, read Blob), `bi-stack-dw` (write Azure SQL), `bi-stack-read` (Power BI dataset refresh, read Azure SQL). Document in a `docs/IAM_PLAN.md`.

### MEDIUM PRIORITY — Power BI

#### 11. Row-Level Security (RLS)
- For healthcare data, RLS is non-negotiable before sharing any report with more than one user.
- **Action:** Add RLS role definitions to the TMDL output template. Minimum: a `[UserEmail]` filter on any table containing patient or provider data. Flag tables requiring RLS in the review checklist as HIGH.

#### 12. Semantic Model Layer
- Power BI templates directly on raw tables (no measures, no calculated columns, no role-playing dims) will break as schema evolves.
- **Action:** Ensure the TMDL skeleton generated by `schema_agent.py` includes at minimum: date table, base measures (COUNT, SUM, DISTINCTCOUNT) per fact table, and role-playing dimension stubs for multi-role date dims.

### LOW PRIORITY — Operational

#### 13. Pipeline Failure Alerting
- No mechanism to notify anyone if a pipeline run fails silently.
- **Action:** When Azure Data Factory is introduced, configure alert rules on pipeline failure and partial success. Route to email initially; Slack/Teams webhook later.

#### 14. Data Reconciliation Reporting
- No visible record of whether source-to-target counts match after each load.
- **Action:** See item 7 (`pipeline_audit` table). Add a reconciliation summary to the `review_checklist.md` output that schema agent generates.

---

**Biggest near-term risk: items 1 (PHI) and 2 (staging layer).** Everything else can be retrofitted after Azure integration, but PHI in dev and a missing staging layer are architectural mistakes that compound as the system grows.
