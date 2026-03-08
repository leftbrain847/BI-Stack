"""
Schema inference agent.

Takes CSV profiles (from csv_profiler.py) and calls Claude Opus 4.6
to produce:
  - DDL CREATE TABLE statements (SQL Server syntax)
  - Relationship map (FK / star schema)
  - TMDL semantic model skeleton
  - Consultant review checklist

Uses structured JSON output so the response is always parseable.
"""

from __future__ import annotations

import json
import os

import anthropic

# ── JSON output schema ─────────────────────────────────────────────────────
# All objects must have additionalProperties: false for structured outputs.

_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "ddl_statements": {
            "type": "array",
            "description": "One CREATE TABLE statement per table, SQL Server T-SQL syntax.",
            "items": {"type": "string"},
        },
        "relationships": {
            "type": "array",
            "description": "FK / star schema relationships between tables.",
            "items": {
                "type": "object",
                "properties": {
                    "from_table":    {"type": "string"},
                    "from_column":   {"type": "string"},
                    "to_table":      {"type": "string"},
                    "to_column":     {"type": "string"},
                    "cardinality":   {
                        "type": "string",
                        "description": "one-to-many | many-to-one | one-to-one | many-to-many",
                    },
                    "relationship_role": {
                        "type": "string",
                        "description": "fact-to-dimension | dimension-to-dimension | bridge | other",
                    },
                    "notes": {"type": "string"},
                },
                "required": [
                    "from_table", "from_column", "to_table", "to_column",
                    "cardinality", "relationship_role", "notes",
                ],
                "additionalProperties": False,
            },
        },
        "tmdl_skeleton": {
            "type": "string",
            "description": (
                "A TMDL (Tabular Model Definition Language) skeleton. "
                "Include table definitions, columns with data types, "
                "suggested relationships, and stub measure definitions. "
                "Mark sections that need human review with // TODO comments."
            ),
        },
        "review_checklist": {
            "type": "array",
            "description": "Issues and decisions the consultant must review before proceeding.",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "data_quality | schema_design | relationship | "
                            "semantic_model | compliance | performance"
                        ),
                    },
                    "severity": {
                        "type": "string",
                        "description": "high | medium | low | info",
                    },
                    "item": {
                        "type": "string",
                        "description": "Short description of the issue or decision point.",
                    },
                    "recommendation": {
                        "type": "string",
                        "description": "Specific recommended action or question to answer.",
                    },
                },
                "required": ["category", "severity", "item", "recommendation"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ddl_statements", "relationships", "tmdl_skeleton", "review_checklist"],
    "additionalProperties": False,
}

# ── system prompt ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a senior data warehouse architect specializing in healthcare BI.
Your job is to analyze raw CSV metadata profiles and produce the first-pass
artifacts for a consulting engagement:

1. **DDL** — SQL Server T-SQL CREATE TABLE statements for a star schema.
   - Map CSV files to fact or dimension tables appropriately.
   - Choose precise SQL Server data types (VARCHAR(n), NVARCHAR(n), DATE,
     DATETIME2, DECIMAL(p,s), INT, BIGINT, BIT) — avoid generic NVARCHAR(MAX).
   - Add PK constraints. Add FK constraints where the relationship is clear,
     but comment out FKs where orphan records or data quality issues make them
     unsafe to enforce immediately.
   - Add inline comments where a column needs consultant review.
   - Prefix with schema: [dbo].

2. **Relationships** — A JSON relationship map for the Power BI semantic model.
   - Identify fact tables and dimension tables.
   - Map every FK relationship including cardinality.
   - Note any many-to-many relationships that need a bridge table.

3. **TMDL skeleton** — A TMDL file for the semantic model.
   - Include all tables, columns, and data types.
   - Add 2-3 stub DAX measures per fact table (e.g., count, sum, average).
   - Include relationship definitions.
   - Mark anything needing human review with // TODO comments.

4. **Review checklist** — Every data quality issue, schema design decision,
   compliance concern, and open question the consultant must resolve before
   executing the DDL or publishing the model.
   - Be specific. "Review date format" is not helpful. "patients.date_of_birth
     has mixed ISO and US date formats — standardize before loading" is helpful.
   - Flag HIPAA/healthcare-specific concerns (PHI columns, audit trail needs).
   - High severity: blockers that will cause failures or data errors.
   - Medium severity: decisions that affect model correctness.
   - Low/info: best practices and future considerations.

Base your analysis strictly on the column profiles provided. Do not invent
tables or columns not present in the data. Where you are uncertain, flag it
in the review checklist rather than guessing.
"""

# ── agent call ─────────────────────────────────────────────────────────────

def infer_schema(profiles: list[dict], model: str | None = None) -> dict:
    """
    Call Claude with all CSV profiles and return the structured result.

    Args:
        profiles: List of profile dicts from csv_profiler.profile_directory()
        model:    Override the model (defaults to env AGENT_MODEL or claude-opus-4-6)

    Returns:
        Parsed dict matching _OUTPUT_SCHEMA
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )

    model_id = model or os.environ.get("AGENT_MODEL", "claude-opus-4-6")
    client   = anthropic.Anthropic(api_key=api_key)

    user_content = (
        "Here are the CSV profiles for this engagement. "
        "The dataset is healthcare — patients, clinical encounters, billing.\n\n"
        f"```json\n{json.dumps(profiles, indent=2)}\n```\n\n"
        "Produce the schema artifacts as specified."
    )

    print(f"\nCalling {model_id} (adaptive thinking, streaming)...")

    # Stream to avoid timeout on large structured outputs.
    # Adaptive thinking is enabled — Claude will reason before responding.
    with client.messages.stream(
        model=model_id,
        max_tokens=24000,
        thinking={"type": "enabled", "budget_tokens": 8000},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": _OUTPUT_SCHEMA,
            }
        },
    ) as stream:
        # Stream thinking blocks to console so the user sees progress
        current_block_type: str | None = None
        for event in stream:
            if event.type == "content_block_start":
                current_block_type = getattr(event.content_block, "type", None)
                if current_block_type == "thinking":
                    print("\n[Thinking...]", flush=True)
                elif current_block_type == "text":
                    print("\n[Generating schema artifacts...]", flush=True)
            elif event.type == "content_block_delta":
                if (current_block_type == "thinking"
                        and hasattr(event.delta, "thinking")):
                    print(".", end="", flush=True)

        final = stream.get_final_message()

    # Find the text block (may follow a thinking block)
    text_block = next(
        (b for b in final.content if b.type == "text"), None
    )
    if not text_block:
        raise ValueError("No text block in response — unexpected model output.")

    result = json.loads(text_block.text)

    usage = final.usage
    print(f"\n\nTokens — input: {usage.input_tokens:,}  output: {usage.output_tokens:,}")

    return result
