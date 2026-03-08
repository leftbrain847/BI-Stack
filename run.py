"""
BI-Stack Phase 0 — Schema Inference Agent
==========================================
Reads CSVs from data/raw/, profiles them, calls Claude Opus 4.6,
and writes four artifacts to output/.

Usage:
    python run.py                    # uses data/raw/ and output/
    python run.py --data path/       # custom data directory
    python run.py --out  path/       # custom output directory
    python run.py --model claude-sonnet-4-6   # override model
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # loads .env if present (ANTHROPIC_API_KEY, etc.)

from agent.csv_profiler import profile_directory
from agent.schema_agent  import infer_schema
from agent.output_writer import write_all


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BI-Stack schema inference agent")
    p.add_argument("--data",  default="data/raw",  help="Directory containing input CSVs")
    p.add_argument("--out",   default="output",    help="Directory to write artifacts")
    p.add_argument("--model", default=None,        help="Override the Claude model ID")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    data_dir   = Path(args.data)
    output_dir = Path(args.out)

    # ── 1. Profile CSVs ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Step 1 — Profiling CSVs")
    print(f"{'='*60}")
    print(f"Data directory: {data_dir.resolve()}")

    try:
        profiles = profile_directory(data_dir)
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("Run  python scripts/generate_data.py  first.")
        sys.exit(1)

    total_rows = sum(p["row_count"] for p in profiles)
    print(f"\nProfiled {len(profiles)} files, {total_rows:,} total rows.")

    # ── 2. Call the schema agent ───────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Step 2 — Schema Inference Agent")
    print(f"{'='*60}")

    result = infer_schema(profiles, model=args.model)

    # ── 3. Write output artifacts ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Step 3 — Writing Artifacts")
    print(f"{'='*60}")
    print(f"Output directory: {output_dir.resolve()}")

    write_all(result, output_dir)

    # ── 4. Summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"  Tables generated:        {len(result.get('ddl_statements', []))}")
    print(f"  Relationships mapped:    {len(result.get('relationships', []))}")
    print(f"  Review checklist items:  {len(result.get('review_checklist', []))}")

    high = sum(1 for i in result.get("review_checklist", [])
               if i.get("severity", "").lower() == "high")
    if high:
        print(f"\n  [HIGH] {high} HIGH severity item(s) -- review output/review_checklist.md before executing DDL.")

    print(f"\nDone. Open output/ to review artifacts.")
    print("Next step: open output/schema.sql in SSMS 18 and review before executing.\n")


if __name__ == "__main__":
    main()
