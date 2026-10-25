"""Core CSV analysis logic for DataSense AI.

All statistics are computed from the uploaded data with pandas/NumPy.
Nothing here knows about HTTP; main.py handles routing and validation.
"""

import csv
import io
import math
from datetime import date, datetime
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from pandas.api import types as ptypes

# ---- Tunable limits -------------------------------------------------------
MAX_COLUMNS = 200
TOP_CATEGORIES = 10
MAX_CORRELATION_COLUMNS = 30
STRONG_CORRELATION = 0.7
MAX_STRONG_PAIRS = 10
OUTLIER_SAMPLE_SIZE = 5
PREVIEW_ROWS = 5


class CSVAnalysisError(Exception):
    """A problem with the uploaded CSV that is safe to show to the user."""


# ---- JSON safety ----------------------------------------------------------
def to_json_safe(value: Any) -> Any:
    """Recursively convert NumPy/pandas values into plain JSON-safe Python.

    NaN, +inf and -inf become None (JSON null).
    """
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, dict):
        return {str(k): to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [to_json_safe(v) for v in value.tolist()]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, str):
        return value
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


# ---- Loading --------------------------------------------------------------
def _decode(content: bytes) -> Tuple[str, str]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise CSVAnalysisError(
        "The file could not be decoded as text. Please save it as UTF-8 CSV."
    )


def _detect_delimiter(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text[:20000], delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _make_unique_names(names: List[Any]) -> List[str]:
    seen: Dict[str, int] = {}
    result: List[str] = []
    for index, raw in enumerate(names):
        name = str(raw).strip() or f"unnamed_{index}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        result.append(name)
    return result


def load_csv(content: bytes) -> Tuple[pd.DataFrame, Dict[str, str]]:
    text, encoding = _decode(content)
    if not text.strip():
        raise CSVAnalysisError("The CSV file is empty.")

    delimiter = _detect_delimiter(text)
    try:
        df = pd.read_csv(io.StringIO(text), sep=delimiter, skipinitialspace=True)
    except pd.errors.EmptyDataError:
        raise CSVAnalysisError("The CSV file is empty or has no readable columns.")
    except pd.errors.ParserError as exc:
        raise CSVAnalysisError(f"The CSV is malformed: {str(exc)[:200]}")
    except Exception:
        raise CSVAnalysisError("The CSV could not be parsed. Please check its format.")

    if df.shape[1] == 0:
        raise CSVAnalysisError("The CSV has no columns.")
    if df.shape[0] == 0:
        raise CSVAnalysisError("The CSV has a header but no data rows.")
    if df.shape[1] > MAX_COLUMNS:
        raise CSVAnalysisError(
            f"The CSV has {df.shape[1]} columns; the maximum supported is {MAX_COLUMNS}."
        )

    df.columns = _make_unique_names(list(df.columns))
    return df, {"encoding": encoding, "delimiter": delimiter}


# ---- Column helpers -------------------------------------------------------
def classify_column(series: pd.Series) -> str:
    """Return one of: boolean, numeric, datetime, categorical."""
    if ptypes.is_bool_dtype(series):
        return "boolean"
    if ptypes.is_numeric_dtype(series):
        return "numeric"
    if ptypes.is_datetime64_any_dtype(series):
        return "datetime"
    return "categorical"


def _clean_numeric(series: pd.Series) -> pd.Series:
    """Float series with infinities treated as missing and NaNs dropped."""
    return series.astype("float64").replace([np.inf, -np.inf], np.nan).dropna()


def _percent(part: float, whole: float) -> float:
    return round(part / whole * 100, 2) if whole else 0.0


# ---- Individual analyses --------------------------------------------------
def numeric_stats(series: pd.Series) -> Dict[str, Any]:
    values = _clean_numeric(series)
    if values.empty:
        return {k: None for k in
                ("mean", "std", "min", "q25", "median", "q75", "max")} | {"count": 0}
    return {
        "count": int(values.count()),
        "mean": values.mean(),
        "std": values.std(),
        "min": values.min(),
        "q25": values.quantile(0.25),
        "median": values.median(),
        "q75": values.quantile(0.75),
        "max": values.max(),
    }


def iqr_outliers(series: pd.Series) -> Dict[str, Any]:
    values = _clean_numeric(series)
    if len(values) < 4:
        return {"count": 0, "percent": 0.0, "lower_bound": None, "upper_bound": None,
                "sample_values": [], "note": "Not enough data points for IQR."}

    q1, q3 = values.quantile(0.25), values.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return {"count": 0, "percent": 0.0, "lower_bound": q1, "upper_bound": q3,
                "sample_values": [], "note": "IQR is zero; outlier detection skipped."}

    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = values[(values < lower) | (values > upper)]
    # Most extreme values first
    distance = (outliers - values.median()).abs().sort_values(ascending=False)
    sample = outliers.loc[distance.index[:OUTLIER_SAMPLE_SIZE]]
    return {
        "count": int(len(outliers)),
        "percent": _percent(len(outliers), len(values)),
        "lower_bound": lower,
        "upper_bound": upper,
        "sample_values": sample.tolist(),
        "note": None,
    }


def categorical_summary(series: pd.Series) -> Dict[str, Any]:
    non_null = series.dropna()
    counts = non_null.value_counts()
    top = counts.head(TOP_CATEGORIES)
    return {
        "unique_count": int(non_null.nunique()),
        "top_values": [
            {"value": value, "count": int(count),
             "percent": _percent(count, len(non_null))}
            for value, count in top.items()
        ],
        "truncated": bool(len(counts) > TOP_CATEGORIES),
    }


def correlations(df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
    if len(numeric_cols) < 2:
        return {"available": False,
                "reason": "At least two numeric columns are needed."}

    cols = numeric_cols[:MAX_CORRELATION_COLUMNS]
    numeric = df[cols].astype("float64").replace([np.inf, -np.inf], np.nan)
    with np.errstate(all="ignore"):
        corr = numeric.corr()

    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            if pd.notna(r) and abs(r) >= STRONG_CORRELATION:
                pairs.append({"column_a": cols[i], "column_b": cols[j],
                              "correlation": float(r)})
    pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)

    return {
        "available": True,
        "columns": cols,
        "matrix": corr.values.tolist(),
        "strong_pairs": pairs[:MAX_STRONG_PAIRS],
        "truncated": len(numeric_cols) > MAX_CORRELATION_COLUMNS,
    }


# ---- Public entry points --------------------------------------------------
def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    n_rows, n_cols = df.shape
    kinds = {col: classify_column(df[col]) for col in df.columns}
    numeric_cols = [c for c, k in kinds.items() if k == "numeric"]
    categorical_cols = [c for c, k in kinds.items() if k in ("categorical", "boolean")]

    missing = df.isna().sum()
    duplicate_rows = int(df.duplicated().sum())

    columns_info = [
        {
            "name": col,
            "dtype": str(df[col].dtype),
            "kind": kinds[col],
            "missing_count": int(missing[col]),
            "missing_percent": _percent(missing[col], n_rows),
            "unique_count": int(df[col].nunique(dropna=True)),
        }
        for col in df.columns
    ]

    result = {
        "summary": {
            "rows": int(n_rows),
            "columns": int(n_cols),
            "duplicate_rows": duplicate_rows,
            "duplicate_percent": _percent(duplicate_rows, n_rows),
            "total_missing_cells": int(missing.sum()),
            "numeric_columns": len(numeric_cols),
            "categorical_columns": len(categorical_cols),
        },
        "columns": columns_info,
        "numeric_stats": {c: numeric_stats(df[c]) for c in numeric_cols},
        "categorical_summary": {c: categorical_summary(df[c]) for c in categorical_cols},
        "correlations": correlations(df, numeric_cols),
        "outliers": {c: iqr_outliers(df[c]) for c in numeric_cols},
        "preview": df.head(PREVIEW_ROWS).to_dict(orient="records"),
    }
    return to_json_safe(result)


def analyze_csv_bytes(content: bytes) -> Dict[str, Any]:
    df, meta = load_csv(content)
    analysis = analyze_dataframe(df)
    analysis["meta"] = meta
    return analysis