"""Core CSV analysis logic for DataSense AI.

All statistics are computed from the uploaded data with pandas/NumPy.
Nothing here knows about HTTP; main.py handles routing and validation.
"""

import csv
import io
import logging
import math
import re
import warnings
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas.api import types as ptypes

logger = logging.getLogger("datasense")

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


# ===========================================================================
# Advanced column profiling and quality findings
# ===========================================================================
# Everything below is derived from the uploaded data. Rules are deliberately
# simple and are echoed back in `quality_summary.rules` so they can be audited.

# ---- Profiling thresholds (all echoed in quality_summary.rules) -----------
HIGH_MISSING_PERCENT = 20.0        # missing share at/above which a column is a warning
DUPLICATE_WARNING_PERCENT = 1.0    # duplicate-row share at/above which it is a warning
LOW_CARDINALITY_MAX = 10           # <= this many distinct values = "low" cardinality
HIGH_CARDINALITY_UNIQUE = 50       # more distinct values than this = "high"
HIGH_CARDINALITY_RATIO = 0.5       # unique/non-missing at/above this (and > LOW max) = "high"
NEAR_UNIQUE_RATIO = 0.9            # unique/non-missing at/above this = "high" (identifier-like text)
NEAR_UNIQUE_MIN_ROWS = 5           # ...but only with at least this many non-missing values
SEQUENTIAL_ID_MIN_ROWS = 5         # min rows for the "row-number pattern" identifier rule
EXTREME_IQR_MULTIPLIER = 3.0       # beyond Q1/Q3 -/+ 3*IQR = "extreme" outlier
NUMERIC_TEXT_MIN_SHARE = 0.9       # text column is "numeric-like" if >= 90% of values parse
DATETIME_MIN_SHARE = 0.95          # text column is "date-like" if >= 95% match + parse
DATETIME_MIN_VALUES = 3            # minimum non-missing values for date detection
TYPE_SAMPLE_SIZE = 1000            # values sampled for date-pattern detection
MAX_MODES = 5
MAX_EXAMPLES = 5
MAX_VARIANT_GROUPS = 3
VARIANT_MAX_UNIQUE = 5000          # skip spelling-variant check above this cardinality
MAX_EVIDENCE_COLUMNS = 50          # cap on per-column evidence rows in one finding

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}

# Column-name words that suggest an identifier/code stored as a number.
_ID_NAME_WORDS = {
    "id", "uuid", "guid", "zip", "zipcode", "postal", "postcode", "pincode",
    "pin", "phone", "mobile", "tel", "ssn", "sku", "isbn", "code",
}
# Column-name words that suggest values should not be negative.
_NONNEGATIVE_NAME_WORDS = {
    "age", "quantity", "qty", "price", "salary", "height", "weight",
    "distance", "duration", "count",
}
# Literal strings that often stand for "unknown" but are not read as missing by pandas.
_PLACEHOLDER_TOKENS = {
    "-", "--", "?", "??", "unknown", "unk", "missing", "not available",
    "n.a.", "tbd", "undefined", "nil", "not specified", "unspecified",
    "(blank)", "blank",
}
_BOOLEAN_WORDS = {"true", "false", "yes", "no", "y", "n", "t", "f", "0", "1"}

_DATE_PATTERNS = (
    ("iso", r"\d{4}-\d{1,2}-\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"),
    ("year_first_slash", r"\d{4}/\d{1,2}/\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?"),
    ("day_month_year", r"\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?"),
)


# ---- Small helpers --------------------------------------------------------
def _name_words(name: Any) -> set:
    """Lower-case words in a column name; splits snake_case, spaces and camelCase."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(name))
    return {w for w in re.split(r"[^a-z0-9]+", spaced.lower()) if w}


def _is_text_dtype(series: pd.Series) -> bool:
    return not (
        ptypes.is_bool_dtype(series)
        or ptypes.is_numeric_dtype(series)
        or ptypes.is_datetime64_any_dtype(series)
    )


def _text_values(series: pd.Series) -> pd.Series:
    """Non-missing values as stripped strings (original series is not modified)."""
    return series.dropna().astype(str).str.strip()


def _fmt_pct(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _plural(count: int, singular: str, plural: Optional[str] = None) -> str:
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"


def _cap(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    return rows[:MAX_EVIDENCE_COLUMNS], len(rows)


# ---- Type inference -------------------------------------------------------
def _parse_dates(strings: pd.Series, pattern_name: str) -> Optional[pd.Series]:
    """Parse date-like strings; NaT where unparseable. None if parsing itself failed."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if pattern_name == "iso":
                return pd.to_datetime(strings, errors="coerce", format="ISO8601")
            if pattern_name == "year_first_slash":
                return pd.to_datetime(strings, errors="coerce", format="mixed")
            month_first = pd.to_datetime(strings, errors="coerce", format="mixed", dayfirst=False)
            day_first = pd.to_datetime(strings, errors="coerce", format="mixed", dayfirst=True)
            return month_first if month_first.notna().sum() >= day_first.notna().sum() else day_first
    except Exception:
        return None


def detect_datetime(strings: pd.Series) -> Optional[Dict[str, Any]]:
    """Detect date-like text. Requires one dominant pattern AND successful parsing.

    A min/max range is reported only for unambiguous year-first formats; for
    day/month/year text the day-vs-month order cannot be known, so no range.
    """
    n = len(strings)
    if n < DATETIME_MIN_VALUES:
        return None
    step = max(1, n // TYPE_SAMPLE_SIZE)
    sample = strings if n <= TYPE_SAMPLE_SIZE else strings.iloc[::step]
    for pattern_name, pattern in _DATE_PATTERNS:
        if sample.str.fullmatch(pattern).mean() < DATETIME_MIN_SHARE:
            continue
        parsed_sample = _parse_dates(sample, pattern_name)
        if parsed_sample is None or parsed_sample.notna().mean() < DATETIME_MIN_SHARE:
            continue
        info: Dict[str, Any] = {
            "pattern": pattern_name,
            "ambiguous_day_month": pattern_name == "day_month_year",
            "earliest": None,
            "latest": None,
            "unparsed_count": None,
        }
        if pattern_name != "day_month_year":
            parsed = _parse_dates(strings, pattern_name)
            if parsed is not None:
                valid = parsed.dropna()
                info["unparsed_count"] = int(n - len(valid))
                if len(valid):
                    try:
                        info["earliest"] = valid.min().isoformat()
                        info["latest"] = valid.max().isoformat()
                    except Exception:
                        pass
        return info
    return None


def numeric_like_text(strings: pd.Series) -> Optional[Dict[str, Any]]:
    """Evidence that a text column is mostly numbers (>= NUMERIC_TEXT_MIN_SHARE)."""
    if strings.empty:
        return None
    parsed = pd.to_numeric(strings, errors="coerce").astype("float64")
    ok = parsed.notna() & np.isfinite(parsed)
    numeric_count = int(ok.sum())
    if numeric_count == 0 or numeric_count / len(strings) < NUMERIC_TEXT_MIN_SHARE:
        return None
    bad_counts = strings[~ok].value_counts().head(MAX_EXAMPLES)
    return {
        "numeric_like_count": numeric_count,
        "non_numeric_count": int(len(strings) - numeric_count),
        "numeric_like_percent": _percent(numeric_count, len(strings)),
        "examples": [f"{value} ×{int(count)}" for value, count in bad_counts.items()],
    }


def _infer_numeric_type(series: pd.Series, name: Any) -> Dict[str, Any]:
    values = _clean_numeric(series)
    if values.empty:
        return {"analytical_type": "other", "type_detail": "no_finite_values",
                "type_reason": "Numeric column, but it has no finite values (all are infinite)."}
    integer_valued = bool((values % 1 == 0).all())
    id_words = sorted(_name_words(name) & _ID_NAME_WORDS)
    if integer_valued and id_words:
        return {
            "analytical_type": "other", "type_detail": "identifier_like",
            "type_reason": (f"Column name contains '{id_words[0]}' and every value is a whole number, "
                            "so it is treated as an identifier/code rather than a measurement."),
        }
    if (integer_valued and len(values) == len(series) and len(values) >= SEQUENTIAL_ID_MIN_ROWS
            and values.is_unique and values.min() in (0, 1)
            and bool((values.sort_values().diff().dropna() == 1).all())):
        return {
            "analytical_type": "other", "type_detail": "identifier_like",
            "type_reason": ("Values are consecutive whole numbers starting at 0 or 1 with no repeats "
                            "(a row-number pattern), so they are treated as an identifier."),
        }
    return {
        "analytical_type": "numeric",
        "type_detail": "integer" if integer_valued else "decimal",
        "type_reason": f"Numeric dtype ({series.dtype}) with {'whole-number' if integer_valued else 'decimal'} values.",
    }


def infer_column_type(series: pd.Series, name: Any) -> Dict[str, Any]:
    """Infer the analytical type with a human-readable reason.

    analytical_type is one of numeric / categorical / datetime / other.
    The original column values are never modified.
    """
    non_missing = series.dropna()
    if non_missing.empty:
        return {"analytical_type": "other", "type_detail": "all_missing",
                "type_reason": "Every value is missing, so no type can be inferred."}
    if ptypes.is_bool_dtype(series):
        return {"analytical_type": "categorical", "type_detail": "boolean",
                "type_reason": "Boolean dtype; treated as a two-category column."}
    if ptypes.is_numeric_dtype(series):
        return _infer_numeric_type(series, name)
    if ptypes.is_datetime64_any_dtype(series):
        info = {"pattern": "datetime64", "ambiguous_day_month": False,
                "earliest": non_missing.min().isoformat(), "latest": non_missing.max().isoformat(),
                "unparsed_count": 0}
        return {"analytical_type": "datetime", "type_detail": "datetime64",
                "type_reason": "Datetime dtype.", "datetime": info}

    strings = _text_values(series)
    date_info = detect_datetime(strings)
    if date_info:
        note = ("Day/month order is ambiguous, so no date range is reported."
                if date_info["ambiguous_day_month"] else "Dates parsed successfully.")
        return {"analytical_type": "datetime", "type_detail": "date_like_text",
                "type_reason": (f"At least {int(DATETIME_MIN_SHARE * 100)}% of values match a date pattern "
                                f"({date_info['pattern']}) and parse as dates. Stored as text. {note}"),
                "datetime": date_info}
    lowered = {str(v).strip().casefold() for v in non_missing.unique()}
    if len(lowered) <= 2 and lowered <= _BOOLEAN_WORDS:
        return {"analytical_type": "categorical", "type_detail": "boolean_like",
                "type_reason": "Text column whose values are all yes/no-style words."}
    return {"analytical_type": "categorical", "type_detail": "text",
            "type_reason": f"Text values ({series.dtype}); treated as categories."}


# ---- Categorical helpers --------------------------------------------------
def cardinality_info(unique: int, non_missing: int) -> Optional[Dict[str, Any]]:
    """Cardinality level, using the thresholds listed in quality_summary.rules."""
    if non_missing == 0:
        return None
    ratio = unique / non_missing
    all_unique = unique == non_missing and non_missing >= 2
    if unique == 1:
        level = "constant"
    elif non_missing >= NEAR_UNIQUE_MIN_ROWS and ratio >= NEAR_UNIQUE_RATIO:
        level = "high"
    elif unique <= LOW_CARDINALITY_MAX:
        level = "low"
    elif unique > HIGH_CARDINALITY_UNIQUE or ratio >= HIGH_CARDINALITY_RATIO:
        level = "high"
    else:
        level = "medium"
    return {"level": level, "high_cardinality": level == "high",
            "all_values_unique": all_unique, "unique_percent": _percent(unique, non_missing)}


def case_whitespace_variants(counts: pd.Series) -> Optional[Dict[str, Any]]:
    """Distinct values that differ only by letter case or spacing."""
    if len(counts) < 2 or len(counts) > VARIANT_MAX_UNIQUE:
        return None
    groups: Dict[str, List[Tuple[str, int]]] = {}
    for value, count in counts.items():
        raw = str(value)
        groups.setdefault(" ".join(raw.split()).casefold(), []).append((raw, int(count)))
    clashes = [v for v in groups.values() if len(v) > 1]
    if not clashes:
        return None
    clashes.sort(key=lambda v: -sum(c for _, c in v))
    examples = [" / ".join(f'"{raw}" ×{c}' for raw, c in sorted(v, key=lambda x: -x[1]))
                for v in clashes[:MAX_VARIANT_GROUPS]]
    return {"group_count": len(clashes),
            "affected_values": sum(len(v) for v in clashes),
            "examples": examples}


def placeholder_tokens(counts: pd.Series) -> Optional[Dict[str, Any]]:
    """Literal 'unknown'-style strings that pandas does not treat as missing."""
    hits = [(str(v), int(c)) for v, c in counts.items()
            if str(v).strip().casefold() in _PLACEHOLDER_TOKENS]
    if not hits:
        return None
    hits.sort(key=lambda x: -x[1])
    return {"total_count": sum(c for _, c in hits),
            "examples": [f'"{v}" ×{c}' for v, c in hits[:MAX_EXAMPLES]]}


# ---- Per-column profile ---------------------------------------------------
def _numeric_profile(series: pd.Series, stats: Dict[str, Any], outliers: Dict[str, Any]) -> Dict[str, Any]:
    """Numeric profile built on the SAME stats/outlier results used by the legacy sections."""
    values = _clean_numeric(series)
    q1, q3 = stats["q25"], stats["q75"]
    iqr = None if q1 is None or q3 is None else q3 - q1
    extreme = None
    if outliers.get("note") is None and iqr is not None and iqr > 0:
        low = q1 - EXTREME_IQR_MULTIPLIER * iqr
        high = q3 + EXTREME_IQR_MULTIPLIER * iqr
        extreme = int(((values < low) | (values > high)).sum())
    return {
        "finite_count": int(len(values)),
        "mean": stats["mean"],
        "median": stats["median"],
        "std": stats["std"],
        "min": stats["min"],
        "max": stats["max"],
        "p25": q1,
        "p50": stats["median"],
        "p75": q3,
        "iqr": iqr,
        "zero_count": int((values == 0).sum()),
        "negative_count": int((values < 0).sum()),
        "infinite_count": int(np.isinf(series.astype("float64")).sum()),
        "outliers": {
            "count": outliers["count"],
            "percent": outliers["percent"],
            "percent_basis": "finite_numeric_values",
            "lower_bound": outliers["lower_bound"],
            "upper_bound": outliers["upper_bound"],
            "extreme_count": extreme,
            "sample_values": outliers["sample_values"],
            "note": outliers["note"],
        },
    }


def profile_column(series: pd.Series, name: Any, n_rows: int,
                   stats: Optional[Dict[str, Any]], outliers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    present = series.dropna()
    non_missing = int(len(present))
    missing = int(n_rows - non_missing)
    counts = present.value_counts()
    unique = int(len(counts))

    type_info = infer_column_type(series, name)
    date_info = type_info.pop("datetime", None)
    atype = type_info["analytical_type"]
    detail = type_info["type_detail"]

    profile: Dict[str, Any] = {
        "name": name,
        "dtype": str(series.dtype),
        "analytical_type": atype,
        "type_detail": detail,
        "type_reason": type_info["type_reason"],
        "row_count": int(n_rows),
        "non_missing_count": non_missing,
        "missing_count": missing,
        "missing_percent": _percent(missing, n_rows),
        "unique_count": unique,
        "unique_percent": _percent(unique, non_missing) if non_missing else None,
        "unique_percent_basis": "non_missing_count",
        "is_constant": unique == 1 and non_missing >= 2,
        "is_all_missing": non_missing == 0,
        "constant_value": counts.index[0] if (unique == 1 and non_missing >= 2) else None,
        "cardinality": (cardinality_info(unique, non_missing)
                        if atype == "categorical" or detail == "identifier_like" else None),
        "numeric": None,
        "categorical": None,
        "datetime": date_info,
        "checks": {"numeric_like_text": None, "case_whitespace_variants": None,
                   "placeholder_tokens": None},
        "notes": [],
    }

    if atype == "numeric" and stats is not None and outliers is not None:
        profile["numeric"] = _numeric_profile(series, stats, outliers)
        num = profile["numeric"]
        if pd.isna(num["std"]):  # NaN here; converted to null by to_json_safe at the end
            profile["notes"].append("Standard deviation is undefined with fewer than 2 numeric values.")
        if num["infinite_count"]:
            profile["notes"].append(
                f"{_plural(num['infinite_count'], 'infinite value')} excluded from the statistics.")
        if outliers["note"]:
            profile["notes"].append(f"Outliers: {outliers['note']}")

    if atype == "categorical" and non_missing:
        top = counts.head(TOP_CATEGORIES)
        top_count = int(counts.iloc[0])
        every_value_once = top_count == 1 and unique > 1
        modes = [] if every_value_once else counts[counts == top_count].index.tolist()
        profile["categorical"] = {
            "percent_basis": "non_missing_count",
            "top_values": [{"value": v, "count": int(c), "percent": _percent(c, non_missing)}
                           for v, c in top.items()],
            "shown_count": int(len(top)),
            "truncated": unique > len(top),
            "other_count": int(non_missing - top.sum()),
            "other_percent": _percent(non_missing - top.sum(), non_missing),
            "modes": modes[:MAX_MODES],
            "mode_count": top_count if modes else None,
            "modes_truncated": len(modes) > MAX_MODES,
            "mode_note": "Every value occurs exactly once, so there is no mode." if every_value_once else None,
        }
        if _is_text_dtype(series):
            profile["checks"]["numeric_like_text"] = numeric_like_text(_text_values(series))
            profile["checks"]["case_whitespace_variants"] = case_whitespace_variants(counts)
            # Placeholder strings in a numbers-stored-as-text column are already
            # listed as that finding's non-numeric examples; don't warn twice.
            if profile["checks"]["numeric_like_text"] is None:
                profile["checks"]["placeholder_tokens"] = placeholder_tokens(counts)

    if detail == "identifier_like":
        profile["notes"].append(
            "Numeric statistics are intentionally not computed for identifier-like columns.")
    if date_info and date_info["ambiguous_day_month"]:
        profile["notes"].append("Day/month order is ambiguous; no date range is shown.")
    return profile


def build_column_profiles(df: pd.DataFrame, numeric_stats_map: Dict[str, Any],
                          outliers_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    n_rows = len(df)
    return [profile_column(df[c], c, n_rows, numeric_stats_map.get(c), outliers_map.get(c))
            for c in df.columns]


# ---- Quality findings -----------------------------------------------------
def _finding(fid: str, category: str, severity: str, confidence: str, title: str,
             columns: List[Any], evidence: Dict[str, Any], explanation: str,
             recommendation: str) -> Dict[str, Any]:
    return {
        "id": fid, "category": category, "severity": severity, "confidence": confidence,
        "title": title,
        "affected_columns": list(columns)[:MAX_EVIDENCE_COLUMNS],
        "affected_columns_total": len(columns),
        "evidence": evidence, "explanation": explanation, "recommendation": recommendation,
    }


def _missing_findings(profiles: List[Dict[str, Any]], n_rows: int) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    empty = [p for p in profiles if p["is_all_missing"]]
    partial = [p for p in profiles if 0 < p["missing_count"] and not p["is_all_missing"]]
    high = sorted((p for p in partial if p["missing_percent"] >= HIGH_MISSING_PERCENT),
                  key=lambda p: -p["missing_percent"])
    low = sorted((p for p in partial if p["missing_percent"] < HIGH_MISSING_PERCENT),
                 key=lambda p: -p["missing_percent"])

    def rows(group: List[Dict[str, Any]]) -> Dict[str, Any]:
        capped, total = _cap([{"column": p["name"], "missing_count": p["missing_count"],
                               "missing_percent": p["missing_percent"]} for p in group])
        return {"rows": n_rows, "percent_basis": "all rows in the column",
                "columns": capped, "columns_total": total}

    if empty:
        findings.append(_finding(
            "missing_values.all_missing", "missing_values", "critical", "confirmed",
            f"{_plural(len(empty), 'column')} with no values at all",
            [p["name"] for p in empty], rows(empty),
            f"Every one of the {n_rows} rows is empty in these columns, so no statistic or chart can be computed for them.",
            "Check whether the export or join dropped this data. If the columns are not needed, consider leaving them out of the analysis."))
    if high:
        findings.append(_finding(
            "missing_values.high", "missing_values", "warning", "confirmed",
            f"{_plural(len(high), 'column')} with {_fmt_pct(HIGH_MISSING_PERCENT)}% or more missing values",
            [p["name"] for p in high], rows(high),
            f"Highest: {high[0]['name']} is missing {_fmt_pct(high[0]['missing_percent'])}% of its {n_rows} values. "
            "Statistics for these columns describe only the rows that have a value.",
            "Decide per column whether the gaps are expected (for example an optional field). Options include recovering the data, "
            "filtering rows, or imputing with a method you can justify and document."))
    if low:
        findings.append(_finding(
            "missing_values.low", "missing_values", "info", "confirmed",
            f"{_plural(len(low), 'column')} with some missing values (under {_fmt_pct(HIGH_MISSING_PERCENT)}%)",
            [p["name"] for p in low], rows(low),
            "Missing values are limited, and column statistics are computed from the non-missing values only.",
            "Check whether rows with gaps differ systematically from complete rows before ignoring them."))
    return findings


def _duplicate_finding(n_rows: int, duplicate_rows: int, in_groups: int) -> List[Dict[str, Any]]:
    if duplicate_rows <= 0:
        return []
    percent = _percent(duplicate_rows, n_rows)
    severity = "warning" if percent >= DUPLICATE_WARNING_PERCENT else "info"
    return [_finding(
        "duplicates.exact_rows", "duplicates", severity, "confirmed",
        f"{_plural(duplicate_rows, 'exact duplicate row')} ({_fmt_pct(percent)}% of rows)",
        [],
        {"duplicate_rows": duplicate_rows, "duplicate_percent": percent,
         "rows_in_duplicate_groups": in_groups, "total_rows": n_rows,
         "definition": "Rows identical to an earlier row in every column; the first occurrence is not counted."},
        f"{in_groups} rows belong to repeated groups; {duplicate_rows} of them are extra copies.",
        "Confirm whether repeats are genuine repeated events (for example identical purchases) or accidental copies. "
        "If accidental, remove them in your source data; DataSense AI never modifies your file.")]


def _constant_finding(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    const = [p for p in profiles if p["is_constant"]]
    if not const:
        return []
    capped, total = _cap([{
        "column": p["name"],
        "value": p["constant_value"],
        "non_missing_count": p["non_missing_count"], "missing_count": p["missing_count"],
    } for p in const])
    return [_finding(
        "structure.constant_columns", "structure", "info", "confirmed",
        f"{_plural(len(const), 'column')} with a single repeated value",
        [p["name"] for p in const], {"columns": capped, "columns_total": total},
        "A column with one distinct value cannot separate rows or correlate with anything.",
        "Keep it only if it documents a fixed setting (such as a source label); otherwise consider excluding it from analysis.")]


def _outlier_findings(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flagged = [p for p in profiles if p["numeric"] and p["numeric"]["outliers"]["count"] > 0]
    if not flagged:
        return []

    def rows(group: List[Dict[str, Any]]) -> Dict[str, Any]:
        capped, total = _cap([{
            "column": p["name"],
            "outlier_count": p["numeric"]["outliers"]["count"],
            "outlier_percent": p["numeric"]["outliers"]["percent"],
            "extreme_count": p["numeric"]["outliers"]["extreme_count"],
            "lower_bound": p["numeric"]["outliers"]["lower_bound"],
            "upper_bound": p["numeric"]["outliers"]["upper_bound"],
            "sample_values": p["numeric"]["outliers"]["sample_values"],
        } for p in sorted(group, key=lambda p: -p["numeric"]["outliers"]["count"])])
        return {"method": f"IQR rule: outside Q1 - 1.5×IQR to Q3 + 1.5×IQR; extreme = beyond {EXTREME_IQR_MULTIPLIER:g}×IQR",
                "percent_basis": "finite numeric values in the column",
                "columns": capped, "columns_total": total}

    recommendation = ("Outliers are statistical flags, not proven errors. Check the listed values against the source: correct typos or unit "
                      "mistakes, keep genuine extremes, and consider robust statistics (median, IQR) when reporting these columns.")
    extreme = [p for p in flagged if (p["numeric"]["outliers"]["extreme_count"] or 0) > 0]
    moderate = [p for p in flagged if p not in extreme]
    findings = []
    if extreme:
        findings.append(_finding(
            "outliers.extreme", "outliers", "warning", "needs_review",
            f"Extreme outliers in {_plural(len(extreme), 'column')}",
            [p["name"] for p in extreme], rows(extreme),
            "These columns contain values more than 3×IQR beyond the quartiles, which is far outside the typical spread.",
            recommendation))
    if moderate:
        findings.append(_finding(
            "outliers.moderate", "outliers", "info", "needs_review",
            f"Moderate outliers in {_plural(len(moderate), 'column')}",
            [p["name"] for p in moderate], rows(moderate),
            "These columns contain values outside 1.5×IQR of the quartiles but within 3×IQR.",
            recommendation))
    return findings


def _type_findings(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    texty = [p for p in profiles if p["checks"]["numeric_like_text"]]
    if texty:
        capped, total = _cap([{"column": p["name"], **p["checks"]["numeric_like_text"]} for p in texty])
        findings.append(_finding(
            "types.numeric_stored_as_text", "types", "warning", "confirmed",
            f"Numbers stored as text in {_plural(len(texty), 'column')}",
            [p["name"] for p in texty],
            {"threshold_percent": NUMERIC_TEXT_MIN_SHARE * 100, "columns": capped, "columns_total": total},
            f"At least {int(NUMERIC_TEXT_MIN_SHARE * 100)}% of the values in these columns parse as numbers, yet pandas read the column as text, "
            "so numeric statistics are not calculated for it.",
            "Inspect the listed non-numeric values (stray symbols, units, placeholders, trailing spaces), fix them in the source, and re-upload."))
    ids = [p for p in profiles if p["type_detail"] == "identifier_like"]
    if ids:
        capped, total = _cap([{"column": p["name"], "reason": p["type_reason"],
                               "unique_count": p["unique_count"],
                               "non_missing_count": p["non_missing_count"]} for p in ids])
        findings.append(_finding(
            "types.identifier_like_numeric", "types", "info", "needs_review",
            f"{_plural(len(ids), 'numeric column')} treated as identifier-like",
            [p["name"] for p in ids], {"columns": capped, "columns_total": total},
            "These columns are stored as numbers but follow identifier or code patterns, so no means or outlier findings are produced for them here. "
            "The older Numeric Analysis, Correlations and Outliers sections use the raw dtype and may still include them.",
            "If a column really is a measurement, ignore this note; otherwise exclude it from numeric analysis."))
    return findings


def _consistency_findings(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    variants = [p for p in profiles if p["checks"]["case_whitespace_variants"]]
    if variants:
        capped, total = _cap([{"column": p["name"], **p["checks"]["case_whitespace_variants"]} for p in variants])
        findings.append(_finding(
            "consistency.case_whitespace_variants", "consistency", "warning", "needs_review",
            f"Same value spelled differently in {_plural(len(variants), 'column')}",
            [p["name"] for p in variants], {"columns": capped, "columns_total": total},
            "Distinct values in these columns differ only by letter case or spacing, so they are counted as separate categories.",
            "Standardize capitalization and spacing in your source data so one category is not split into several."))
    placeholders = [p for p in profiles if p["checks"]["placeholder_tokens"]]
    if placeholders:
        capped, total = _cap([{"column": p["name"], **p["checks"]["placeholder_tokens"]} for p in placeholders])
        findings.append(_finding(
            "consistency.placeholder_tokens", "consistency", "warning", "needs_review",
            f"Possible missing-value placeholders in {_plural(len(placeholders), 'column')}",
            [p["name"] for p in placeholders], {"columns": capped, "columns_total": total},
            "These literal strings are counted as ordinary categories, not as missing values, so missing counts above may be understated.",
            "If they mean 'unknown', treat them as missing before calculating category shares. If they are legitimate categories, no action is needed."))
    return findings


def _negative_finding(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hits = []
    for p in profiles:
        if p["numeric"] and p["numeric"]["negative_count"] > 0:
            words = sorted(_name_words(p["name"]) & _NONNEGATIVE_NAME_WORDS)
            if words:
                hits.append({"column": p["name"], "matched_name_word": words[0],
                             "negative_count": p["numeric"]["negative_count"],
                             "min": p["numeric"]["min"]})
    if not hits:
        return []
    capped, total = _cap(hits)
    return [_finding(
        "values.unexpected_negative", "values", "warning", "needs_review",
        f"Negative values in {_plural(len(hits), 'column')} whose names suggest non-negative data",
        [h["column"] for h in hits], {"columns": capped, "columns_total": total},
        "The column names contain words such as age, price or count, which are normally zero or positive, but negative values were found. "
        "This is a name-based heuristic, not proof of an error.",
        "Verify whether negatives are legitimate (refunds, adjustments, codes such as -1 for unknown) or data-entry errors.")]


def build_quality(df: pd.DataFrame, profiles: List[Dict[str, Any]],
                  duplicate_rows: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    n_rows, n_cols = df.shape
    total_cells = int(n_rows * n_cols)
    missing_cells = int(sum(p["missing_count"] for p in profiles))
    rows_with_missing = int(df.isna().any(axis=1).sum())
    in_groups = int(df.duplicated(keep=False).sum()) if duplicate_rows else 0

    findings = (
        _missing_findings(profiles, n_rows)
        + _duplicate_finding(n_rows, duplicate_rows, in_groups)
        + _constant_finding(profiles)
        + _outlier_findings(profiles)
        + _type_findings(profiles)
        + _consistency_findings(profiles)
        + _negative_finding(profiles)
    )
    findings.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])  # stable: keeps category order

    type_counts = {t: 0 for t in ("numeric", "categorical", "datetime", "other")}
    for p in profiles:
        type_counts[p["analytical_type"]] += 1
    severity_counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITY_ORDER}
    severity_counts["total"] = len(findings)

    summary = {
        "rows": int(n_rows),
        "columns": int(n_cols),
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "missing_cells_percent": _percent(missing_cells, total_cells),
        "completeness_percent": _percent(total_cells - missing_cells, total_cells),
        "rows_with_missing": rows_with_missing,
        "complete_rows": int(n_rows - rows_with_missing),
        "complete_rows_percent": _percent(n_rows - rows_with_missing, n_rows),
        "columns_with_missing": sum(1 for p in profiles if p["missing_count"] > 0),
        "columns_all_missing": sum(1 for p in profiles if p["is_all_missing"]),
        "constant_columns": sum(1 for p in profiles if p["is_constant"]),
        "duplicate_rows": int(duplicate_rows),
        "duplicate_percent": _percent(duplicate_rows, n_rows),
        "rows_in_duplicate_groups": in_groups,
        "type_counts": type_counts,
        "identifier_like_columns": sum(1 for p in profiles if p["type_detail"] == "identifier_like"),
        "high_cardinality_columns": sum(1 for p in profiles if p["cardinality"] and p["cardinality"]["high_cardinality"]),
        "numeric_columns_with_outliers": sum(1 for p in profiles if p["numeric"] and p["numeric"]["outliers"]["count"] > 0),
        "finding_counts": severity_counts,
        "definitions": {
            "completeness_percent": "Non-missing cells ÷ total cells (rows × columns) × 100.",
            "missing_cells_percent": "Missing cells ÷ total cells × 100.",
            "complete_rows": "Rows with no missing value in any column.",
            "duplicate_rows": "Rows identical to an earlier row in every column (first occurrence not counted); percent is of all rows.",
            "unique_percent": "Distinct non-missing values ÷ non-missing values in that column × 100.",
            "missing_percent": "Missing values in the column ÷ all rows × 100.",
            "outlier_percent": "Values outside the IQR fences ÷ finite numeric values in the column × 100.",
            "note": "These are descriptive counts. They are not a score and do not measure correctness or fitness for any purpose.",
        },
        "rules": {
            "high_missing_percent": HIGH_MISSING_PERCENT,
            "duplicate_warning_percent": DUPLICATE_WARNING_PERCENT,
            "low_cardinality_max_unique": LOW_CARDINALITY_MAX,
            "high_cardinality_min_unique": HIGH_CARDINALITY_UNIQUE + 1,
            "high_cardinality_ratio": HIGH_CARDINALITY_RATIO,
            "near_unique_ratio": NEAR_UNIQUE_RATIO,
            "near_unique_min_rows": NEAR_UNIQUE_MIN_ROWS,
            "extreme_outlier_iqr_multiplier": EXTREME_IQR_MULTIPLIER,
            "numeric_like_text_min_percent": NUMERIC_TEXT_MIN_SHARE * 100,
            "date_like_min_percent": DATETIME_MIN_SHARE * 100,
            "severity": {
                "critical": "Confirmed: a column has no values at all.",
                "warning": ("Confirmed or likely to distort analysis: a column missing >= the high-missing threshold, duplicates >= the duplicate threshold, "
                            "numbers stored as text, extreme outliers, spelling variants, placeholder strings, or negatives where names suggest none."),
                "info": "Descriptive or low impact: smaller missing shares, small duplicate shares, constant columns, moderate outliers, identifier-like columns.",
            },
            "confidence": {
                "confirmed": "A computed fact about the data (counts, parse results).",
                "needs_review": "A potential anomaly that depends on context; a person must decide.",
            },
        },
    }
    return summary, findings


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

    # Computed once and shared with the profiler so every section agrees.
    numeric_stats_map = {c: numeric_stats(df[c]) for c in numeric_cols}
    outliers_map = {c: iqr_outliers(df[c]) for c in numeric_cols}

    # Profiling is additive. If it ever fails on an unusual file, the original
    # analysis is still returned and the failure is reported in profiling_error.
    profiling_error: Optional[str] = None
    try:
        column_profiles = build_column_profiles(df, numeric_stats_map, outliers_map)
        quality_summary, quality_findings = build_quality(df, column_profiles, duplicate_rows)
    except Exception:
        logger.exception("Column profiling failed")
        column_profiles, quality_summary, quality_findings = [], None, []
        profiling_error = "Advanced profiling could not be completed for this file."

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
        "numeric_stats": numeric_stats_map,
        "categorical_summary": {c: categorical_summary(df[c]) for c in categorical_cols},
        "correlations": correlations(df, numeric_cols),
        "outliers": outliers_map,
        "preview": df.head(PREVIEW_ROWS).to_dict(orient="records"),
        "column_profiles": column_profiles,
        "quality_summary": quality_summary,
        "quality_findings": quality_findings,
        "profiling_error": profiling_error,
    }
    return to_json_safe(result)


def analyze_csv_bytes(content: bytes) -> Dict[str, Any]:
    df, meta = load_csv(content)
    analysis = analyze_dataframe(df)
    analysis["meta"] = meta
    return analysis