# BI-Stack

## Tech Stack

**Ingestion**
- CSV files — source data
- Azure Blob Storage — raw landing

**Orchestration**
- Azure Functions — pipeline scheduling
- Azure Data Factory — (future) pipeline orchestration

**Processing & Profiling**
- Python / pandas — data profiling
- Claude API — schema inference

**Storage**
- Azure SQL Database — structured warehouse
- SSMS — database management

**Modeling**
- TMDL / TOM — semantic model
- Power BI PPU — report delivery

**Source Control**
- GitHub — version control

---

## Overview

Automated healthcare BI pipeline. Takes CSV source files, profiles each field, uses Claude to infer data types, PHI flags, relationships, and dim/fact classification, then generates a SQL schema and a prioritized review checklist. Schema is deployed to Azure SQL via SSMS; Power BI templates connect to the resulting tables.

## Project Structure

```
BI-Stack/
├── agent/
│   ├── csv_profiler.py      # Field-level CSV analysis
│   ├── schema_agent.py      # Claude-based schema inference
│   └── output_writer.py     # Artifact persistence
├── data/raw/                # Input CSVs (synthetic only — no PHI)
├── docs/
│   └── ARCHITECTURE_DECISIONS.md
├── output/                  # Generated artifacts (schema.sql, relationships.json, model.tmdl, review_checklist.md)
├── scripts/
│   └── generate_data.py     # Synthetic data generator
├── run.py                   # Main entry point
└── requirements.txt
```

## Usage

```bash
python run.py --data data/raw --out output
```

## Architecture & Decisions

See [`docs/ARCHITECTURE_DECISIONS.md`](docs/ARCHITECTURE_DECISIONS.md) for ADRs, technical debt log, and the pre-Azure integration gap checklist.
