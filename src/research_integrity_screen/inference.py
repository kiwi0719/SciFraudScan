from __future__ import annotations

from dataclasses import dataclass
import warnings

import pandas as pd


@dataclass(frozen=True)
class InferredInputs:
    group_column: str | None
    time_column: str | None
    p_values: pd.DataFrame | None
    reported_stats: pd.DataFrame | None
    notes: list[str]


def infer_inputs(df: pd.DataFrame) -> InferredInputs:
    group_column = infer_group_column(df)
    time_column = infer_time_column(df)
    p_values = infer_p_values(df)
    reported_stats = infer_reported_stats(df)
    notes = []
    if group_column:
        notes.append(f"Detected group column: {group_column}")
    if time_column:
        notes.append(f"Detected time column: {time_column}")
    if p_values is not None:
        notes.append(f"Detected p-value column: {p_values.columns[0]}")
    if reported_stats is not None:
        notes.append("Detected reported-statistics table in dataset CSV")
    return InferredInputs(group_column, time_column, p_values, reported_stats, notes)


def infer_group_column(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    name_priority = {
        "group",
        "groups",
        "arm",
        "trial_arm",
        "treatment",
        "condition",
        "cohort",
        "intervention",
        "randomization",
        "randomisation",
    }
    candidates = []
    row_count = len(df)
    for column in df.columns:
        normalized = _normalize(column)
        if _looks_like_id(normalized) or _looks_like_time_name(normalized):
            continue
        values = df[column].dropna()
        unique_count = values.nunique(dropna=True)
        if unique_count < 2 or unique_count > min(12, max(2, row_count // 2)):
            continue
        if not _is_categorical_like(values, unique_count):
            continue
        name_score = 100 if normalized in name_priority else 0
        balance_score = _balance_score(values)
        candidates.append((name_score + balance_score - unique_count, str(column)))
    if not candidates:
        return None
    return sorted(candidates, reverse=True)[0][1]


def infer_time_column(df: pd.DataFrame) -> str | None:
    candidates = []
    for column in df.columns:
        values = df[column].dropna()
        if len(values) < 3:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            parsed = pd.to_datetime(values, errors="coerce")
        parse_rate = float(parsed.notna().mean()) if len(parsed) else 0.0
        if parse_rate < 0.7:
            continue
        unique_count = parsed.nunique(dropna=True)
        if unique_count < 3:
            continue
        name_score = 50 if _looks_like_time_name(_normalize(column)) else 0
        candidates.append((name_score + parse_rate * 30 + min(unique_count, 20), str(column)))
    if not candidates:
        return None
    return sorted(candidates, reverse=True)[0][1]


def infer_p_values(df: pd.DataFrame) -> pd.DataFrame | None:
    names = {"p", "p_value", "pvalue", "pval", "reported_p", "p.value", "p-value"}
    candidates = []
    for column in df.columns:
        normalized = _normalize(column)
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(values) < 3:
            continue
        in_range = values[(values >= 0) & (values <= 1)]
        rate = len(in_range) / len(values)
        if rate < 0.9:
            continue
        name_score = 100 if normalized in names else 0
        candidates.append((name_score + len(in_range), str(column), in_range.reset_index(drop=True)))
    if not candidates:
        return None
    _, column, values = sorted(candidates, reverse=True)[0]
    return pd.DataFrame({column: values})


def infer_reported_stats(df: pd.DataFrame) -> pd.DataFrame | None:
    normalized = {_normalize(column): column for column in df.columns}
    if "test" not in normalized:
        return None
    useful = {"n", "mean", "sd", "stat", "df1", "df2", "p", "p_value", "scale_min", "scale_max"}
    if not any(name in normalized for name in useful):
        return None
    out = df.copy()
    if "p" not in out.columns:
        for alias in ("p_value", "pvalue", "reported_p", "p.value", "p-value"):
            original = normalized.get(alias)
            if original:
                out = out.rename(columns={original: "p"})
                break
    return out


def _normalize(column: object) -> str:
    return str(column).strip().lower().replace(" ", "_").replace("-", "_")


def _looks_like_id(name: str) -> bool:
    return name in {"id", "subject_id", "participant_id", "patient_id"} or name.endswith("_id")


def _looks_like_time_name(name: str) -> bool:
    return any(token in name for token in ("time", "date", "day", "visit", "timestamp", "year", "month"))


def _is_categorical_like(values: pd.Series, unique_count: int) -> bool:
    if values.dtype == "object" or str(values.dtype).startswith(("category", "bool")):
        return True
    numeric = pd.to_numeric(values, errors="coerce")
    return bool(numeric.notna().all() and unique_count <= 8)


def _balance_score(values: pd.Series) -> float:
    counts = values.value_counts(normalize=True)
    if counts.empty:
        return 0.0
    return float((1.0 - counts.max()) * 40)
