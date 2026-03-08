"""
CSV profiler — produces structured metadata about each CSV file
that the schema agent uses for inference.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


# Rough cardinality buckets used in the profile
def _cardinality_label(unique: int, total: int) -> str:
    if unique == 1:
        return "constant"
    ratio = unique / total if total else 0
    if unique <= 2:
        return "binary"
    if ratio < 0.01:
        return "low"
    if ratio < 0.10:
        return "medium"
    if ratio < 0.90:
        return "high"
    return "unique"


def _infer_semantic_type(col_name: str, series: pd.Series, dtype: str) -> str:
    """
    Heuristic semantic type annotation beyond pandas dtype.
    The schema agent will refine these — we just give it signal.
    """
    name = col_name.lower()

    if name.endswith("_id") or name == "id":
        return "identifier"
    if "date" in name or "time" in name:
        return "datetime"
    if "zip" in name or "postal" in name:
        return "postal_code"
    if "phone" in name or "fax" in name:
        return "phone"
    if "email" in name:
        return "email"
    if "npi" in name:
        return "npi"
    if "icd" in name or "code" in name:
        return "code"
    if name in ("is_active", "is_primary", "active"):
        return "boolean_flag"
    if "amount" in name or "charge" in name or "cost" in name or "price" in name:
        return "currency"
    if "status" in name or "type" in name or "category" in name:
        return "categorical"

    if dtype.startswith("int") or dtype.startswith("float"):
        return "numeric"
    return "text"


def profile_csv(path: Path) -> dict:
    """
    Return a profile dict for a single CSV.
    Handles mixed-type columns gracefully by reading everything as str first,
    then attempting numeric conversion per column.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])

    total_rows = len(df)
    columns = []

    for col in df.columns:
        series = df[col]
        null_count = series.isna().sum() + (series == "").sum()
        non_null = series.dropna()
        non_null = non_null[non_null != ""]

        # Try to detect if the column is really numeric
        numeric_series = pd.to_numeric(non_null, errors="coerce")
        numeric_success = numeric_series.notna().sum()
        is_numeric = numeric_success / len(non_null) > 0.95 if len(non_null) > 0 else False

        # Try to detect dates
        date_series = None
        is_date = False
        if not is_numeric and "date" in col.lower():
            try:
                date_series = pd.to_datetime(non_null, infer_datetime_format=True, errors="coerce")
                date_success = date_series.notna().sum()
                is_date = date_success / len(non_null) > 0.80 if len(non_null) > 0 else False
            except Exception:
                pass

        if is_numeric:
            effective_series = numeric_series.dropna()
            dtype_label = "numeric"
            col_min = float(effective_series.min()) if len(effective_series) else None
            col_max = float(effective_series.max()) if len(effective_series) else None
            col_mean = round(float(effective_series.mean()), 2) if len(effective_series) else None
        elif is_date:
            effective_series = date_series.dropna()
            dtype_label = "date"
            col_min = str(effective_series.min().date()) if len(effective_series) else None
            col_max = str(effective_series.max().date()) if len(effective_series) else None
            col_mean = None
        else:
            effective_series = non_null
            dtype_label = "text"
            col_min = None
            col_max = None
            col_mean = None

        unique_count = series.nunique()
        cardinality  = _cardinality_label(unique_count, total_rows)
        semantic     = _infer_semantic_type(col, series, dtype_label)

        # Sample up to 8 distinct non-null values
        sample_pool = non_null.unique().tolist()
        random_sample = sample_pool[:8] if len(sample_pool) <= 8 else (
            pd.Series(sample_pool).sample(8, random_state=42).tolist()
        )

        # Detect mixed format problems
        anomalies = []
        if "date" in col.lower() and dtype_label == "text":
            # Check for mixed date formats
            iso_count = non_null.str.match(r"^\d{4}-\d{2}-\d{2}$").sum()
            us_count  = non_null.str.match(r"^\d{2}/\d{2}/\d{4}$").sum()
            if iso_count > 0 and us_count > 0:
                anomalies.append(
                    f"mixed date formats: {iso_count} ISO (YYYY-MM-DD), {us_count} US (MM/DD/YYYY)"
                )
        if "zip" in col.lower():
            five_digit = non_null.str.match(r"^\d{5}$").sum()
            nine_digit = non_null.str.match(r"^\d{5}-\d{4}$").sum()
            if five_digit > 0 and nine_digit > 0:
                anomalies.append(
                    f"mixed zip formats: {five_digit} five-digit, {nine_digit} nine-digit"
                )
        if semantic == "categorical" or semantic == "boolean_flag":
            # Check case inconsistency
            lower_vals = set(non_null.str.lower().unique())
            actual_vals = set(non_null.unique())
            if len(actual_vals) > len(lower_vals):
                anomalies.append(
                    f"case inconsistency: {len(actual_vals)} raw variants map to "
                    f"{len(lower_vals)} distinct values"
                )
        if semantic == "boolean_flag":
            val_set = set(non_null.str.lower().unique())
            bool_encodings = val_set & {"true", "false", "1", "0", "yes", "no", "t", "f"}
            if len(bool_encodings) > 2:
                anomalies.append(
                    f"mixed boolean encoding detected: {sorted(bool_encodings)}"
                )
        if "npi" in col.lower() and dtype_label == "text":
            leading_zero = non_null.str.match(r"^0\d{9}$").sum()
            if leading_zero > 0:
                anomalies.append(
                    f"{leading_zero} NPI values start with 0 — will be corrupted if cast to INT"
                )
        if "icd" in col.lower():
            with_dot    = non_null.str.contains(r"\.", regex=True).sum()
            without_dot = (~non_null.str.contains(r"\.", regex=True)).sum()
            if with_dot > 0 and without_dot > 0:
                anomalies.append(
                    f"mixed ICD code format: {with_dot} with dot, {without_dot} without"
                )

        col_profile: dict = {
            "name":           col,
            "dtype":          dtype_label,
            "semantic_type":  semantic,
            "null_count":     int(null_count),
            "null_pct":       round(null_count / total_rows * 100, 1) if total_rows else 0,
            "unique_count":   int(unique_count),
            "cardinality":    cardinality,
            "sample_values":  [str(v) for v in random_sample],
        }

        if col_min is not None:
            col_profile["min"] = col_min
        if col_max is not None:
            col_profile["max"] = col_max
        if col_mean is not None:
            col_profile["mean"] = col_mean
        if anomalies:
            col_profile["anomalies"] = anomalies

        columns.append(col_profile)

    return {
        "filename":   path.name,
        "table_hint": path.stem,   # e.g. "patients" from "patients.csv"
        "row_count":  total_rows,
        "col_count":  len(df.columns),
        "columns":    columns,
    }


def profile_directory(data_dir: Path) -> list[dict]:
    """Profile all CSV files in a directory."""
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    profiles = []
    for f in csv_files:
        print(f"  Profiling {f.name}...")
        profiles.append(profile_csv(f))

    return profiles


def profiles_to_json(profiles: list[dict]) -> str:
    return json.dumps(profiles, indent=2)
