"""Carlisle-style baseline balance check for randomized trials.

Carlisle (2017): under real randomization, baseline comparisons between arms
produce p-values that are uniform on [0, 1]. Fabricated data tends to be *too*
balanced, piling p-values up near 1.

The uniformity assumption is only exactly true for independent baseline
variables. Real baseline tables are correlated (height and weight, age and
comorbidity), which makes the KS test anti-conservative, so a flag here is a
reason to look, never a result to report on its own.

Two entry points:

- `carlisle_method` works from raw participant rows.
- `baseline_summary_check` works from a published baseline table -- per-arm n,
  mean and SD per variable. This is the case that actually arises when
  screening a paper, since raw data is rarely available, and it is how
  Carlisle and Bolland apply the method.
"""

from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from scifraudscan.models import Finding, clear, flag, not_applicable
from scifraudscan.utils import decimal_places, numeric_frame, safe_float

MIN_VARIABLES = 5
MAX_CATEGORY_LEVELS = 20
REFERENCE_FILE = (
    Path(__file__).resolve().parent.parent / "reference" / "carlisle_baseline_p_reference.csv"
)
ALPHA = 0.01
CAVEAT = (
    "Baseline variables are usually correlated, which violates the independence the "
    "uniformity test assumes, and rounding of published summary statistics distorts "
    "the p-value distribution away from exactly uniform (Bolland 2020). Treat a flag "
    "as a prompt to inspect, not as evidence."
)


def carlisle_method(df: pd.DataFrame, group_column: str | None = None) -> Finding:
    check = "Carlisle Baseline Balance"
    if not group_column:
        return not_applicable(check, "No group column was supplied.")
    if group_column not in df.columns:
        return not_applicable(check, f"Group column '{group_column}' is not in the dataset.")

    groups = [g for g in df[group_column].dropna().unique()]
    if len(groups) < 2:
        return not_applicable(check, f"Column '{group_column}' has fewer than 2 groups.")

    p_values: list[float] = []
    variables: list[dict[str, object]] = []
    numeric = numeric_frame(df.drop(columns=[group_column], errors="ignore"))

    for column in numeric.columns:
        samples = [
            numeric.loc[df[group_column] == group, column].dropna().to_numpy(dtype=float)
            for group in groups
        ]
        samples = [s for s in samples if len(s) >= 2 and np.std(s) > 0]
        if len(samples) < 2:
            continue
        result = (
            stats.f_oneway(*samples)
            if len(samples) > 2
            else stats.ttest_ind(*samples, equal_var=False)
        )
        p_value = float(result.pvalue)
        if np.isfinite(p_value):
            p_values.append(p_value)
            variables.append(
                {
                    "column": str(column),
                    "test": "anova" if len(samples) > 2 else "welch_t",
                    "p_value": float(f"{p_value:.6g}"),
                }
            )

    for column in df.columns:
        if column == group_column or column in numeric.columns:
            continue
        levels = df[column].nunique(dropna=True)
        # An ID column has one level per row; it is bookkeeping, not a baseline variable.
        if levels > MAX_CATEGORY_LEVELS or levels > len(df) / 10:
            continue
        table = pd.crosstab(df[group_column], df[column])
        if table.shape[0] < 2 or table.shape[1] < 2 or table.to_numpy().sum() < 20:
            continue
        try:
            p_value = float(stats.chi2_contingency(table).pvalue)
        except ValueError:
            continue
        if np.isfinite(p_value):
            p_values.append(p_value)
            variables.append({"column": str(column), "test": "chi2",
                              "p_value": float(f"{p_value:.6g}")})

    if len(p_values) < MIN_VARIABLES:
        return not_applicable(
            check,
            f"Only {len(p_values)} usable baseline variables; {MIN_VARIABLES} are needed.",
            group_column=group_column,
            variables=variables,
        )

    return _uniformity_finding(
        check,
        np.array(p_values),
        {
            "group_column": group_column,
            "variable_count": len(p_values),
            "variables": variables[:50],
        },
    )


def _uniformity_finding(
    check: str, p: np.ndarray, extra: dict[str, object], reference: str = "uniform"
) -> Finding:
    """Compare a set of baseline p-values against the distribution they should follow.

    `reference` is "uniform" for p-values computed from raw participant data,
    and "carlisle" for p-values computed from published, rounded summary
    statistics -- those are not uniform even when the trial is honest.
    """
    cdf = "uniform" if reference == "uniform" else carlisle_reference_cdf
    expected = (
        "a uniform distribution"
        if reference == "uniform"
        else "the distribution real published baseline tables follow"
    )
    ks_p = float(stats.kstest(p, cdf).pvalue)
    # Fabricated balance pushes baseline p-values toward 1, so a one-sided test
    # in that direction has more power than the two-sided test against it.
    too_balanced_p = float(stats.kstest(p, cdf, alternative="less").pvalue)
    too_similar = int((p > 0.95).sum())
    too_different = int((p < 0.05).sum())
    shared = {
        **extra,
        "ks_p_value": float(f"{ks_p:.6g}"),
        "too_balanced_p_value": float(f"{too_balanced_p:.6g}"),
        "mean_baseline_p": round(float(p.mean()), 6),
        "count_above_0_95": too_similar,
        "count_below_0_05": too_different,
        "caveat": CAVEAT,
    }
    best_p = min(ks_p, too_balanced_p)
    if best_p >= ALPHA:
        return clear(
            check,
            f"{len(p)} baseline p-values are consistent with {expected} "
            f"(two-sided KS p={ks_p:.3g}, too-balanced p={too_balanced_p:.3g}).",
            **shared,
        )
    if too_balanced_p < ks_p:
        detail = (
            f"they sit higher than randomization produces (one-sided KS p={too_balanced_p:.3g}), "
            "the pattern left by baselines that were balanced after the fact"
        )
    else:
        detail = f"they depart from it in both directions (KS p={ks_p:.3g})"
    return flag(
        check,
        "high" if best_p < 0.001 else "moderate",
        f"{len(p)} baseline p-values do not follow {expected}: {detail}; "
        f"{too_similar} are above .95 and {too_different} below .05.",
        **shared,
    )


def baseline_pvalues_from_summary(table: pd.DataFrame) -> list[dict[str, object]]:
    """One p-value per baseline variable, from per-arm n / mean / SD.

    Expects columns study, var, and n1..n4 / m1..m4 / s1..s4 for as many arms
    as the trial had. Two arms give a Welch t-test; three or four give a
    one-way ANOVA reconstructed from the summary statistics.
    """
    results: list[dict[str, object]] = []
    for index, row in table.iterrows():
        arms = []
        for arm in range(1, 5):
            n = safe_float(row.get(f"n{arm}"))
            mean = safe_float(row.get(f"m{arm}"))
            sd = safe_float(row.get(f"s{arm}"))
            if n is not None and mean is not None and sd is not None and n >= 2:
                arms.append((n, mean, sd))
        if len(arms) < 2 or all(sd <= 0 for _, _, sd in arms):
            continue
        p_value = _p_two_arms(*arms) if len(arms) == 2 else _p_many_arms(arms)
        if p_value is None or not np.isfinite(p_value):
            continue
        results.append(
            {
                "row": int(index),
                "study": str(row.get("study", "")),
                "variable": str(row.get("var", "")),
                "arms": len(arms),
                "calculated_p": float(f"{p_value:.6g}"),
                "reported_p": safe_float(row.get("p")),
            }
        )
    return results


def baseline_summary_check(table: pd.DataFrame) -> Finding:
    """Carlisle's test applied to a published baseline table."""
    check = "Carlisle Baseline Balance (published table)"
    results = baseline_pvalues_from_summary(table)
    if len(results) < MIN_VARIABLES:
        return not_applicable(
            check,
            f"Only {len(results)} baseline variables could be computed from the table; "
            f"{MIN_VARIABLES} are needed.",
            variables=results,
        )
    p = np.array([r["calculated_p"] for r in results], dtype=float)
    studies = sorted({r["study"] for r in results if r["study"]})
    balanced_p, different_p, reference_mean = _reference_monte_carlo(p)
    shared = {
        "variable_count": len(p),
        "study_count": len(studies) or None,
        "observed_mean_p": round(float(p.mean()), 4),
        "reference_mean_p": round(reference_mean, 4),
        "observed_proportion_above_0_8": round(float((p > 0.8).mean()), 4),
        "reference_proportion_above_0_8": round(1 - float(carlisle_reference_cdf(0.8)), 4),
        "too_balanced_p_value": float(f"{balanced_p:.6g}"),
        "too_different_p_value": float(f"{different_p:.6g}"),
        "reference": "Carlisle 5087 trials, 29,789 baseline variables",
        "variables": results[:100],
        "caveat": CAVEAT,
    }
    best = min(balanced_p, different_p)
    if best >= ALPHA:
        return clear(
            check,
            f"{len(p)} baseline p-values (mean {p.mean():.3f}) are consistent with what real "
            f"published baseline tables look like (mean {reference_mean:.3f}); "
            f"too-balanced p={balanced_p:.3g}.",
            **shared,
        )
    direction = (
        "more balanced than real published trials"
        if balanced_p < different_p
        else "less balanced than real published trials"
    )
    return flag(
        check,
        "high" if best < 0.001 else "moderate",
        f"{len(p)} baseline p-values average {p.mean():.3f} against {reference_mean:.3f} in real "
        f"published trials, making these groups {direction} (Monte-Carlo p={best:.3g}).",
        **shared,
    )


def reported_baseline_p_check(table: pd.DataFrame) -> Finding:
    """Is each printed baseline p-value reachable from the table it sits next to?

    The reported p is compared against the full range of values obtainable from
    the same row: every combination of the means and SDs at the edges of their
    rounding intervals, under both Student's and Welch's t-test. A reported
    value outside that range cannot have come from the summary statistics as
    printed. Being generous about the test used and about rounding is what
    keeps ordinary reporting choices from being flagged.
    """
    check = "Reported Baseline p-value Consistency"
    checked: list[dict[str, object]] = []
    for index, row in table.iterrows():
        reported = safe_float(row.get("p"))
        if reported is None:
            continue
        arms = [
            (
                safe_float(row.get(f"n{a}")),
                safe_float(row.get(f"m{a}")),
                safe_float(row.get(f"s{a}")),
            )
            for a in (1, 2)
        ]
        if any(v is None for arm in arms for v in arm) or any(n < 2 for n, _, _ in arms):
            continue
        bounds = _reachable_p_range(arms, row)
        if bounds is None:
            continue
        low, high = bounds
        # The reported p is itself rounded, so compare its rounding interval
        # against the reachable range rather than the printed value alone.
        tolerance = 0.5 * 10 ** -decimal_places(row.get("p"))
        checked.append(
            {
                "row": int(index),
                "study": str(row.get("study", "")),
                "variable": str(row.get("var", "")),
                "reported_p": reported,
                "reported_p_tolerance": tolerance,
                "reachable_p_min": round(low, 6),
                "reachable_p_max": round(high, 6),
                "unreachable": bool(
                    reported + tolerance < low - 1e-9 or reported - tolerance > high + 1e-9
                ),
            }
        )

    if not checked:
        return not_applicable(
            check, "No two-arm row supplied a reported p-value alongside n, mean and SD."
        )
    unreachable = [c for c in checked if c["unreachable"]]
    if not unreachable:
        return clear(
            check,
            f"All {len(checked)} reported baseline p-values are reachable from the "
            "summary statistics printed beside them.",
            n_checked=len(checked),
            variables=checked[:100],
        )
    rate = len(unreachable) / len(checked)
    return flag(
        check,
        "high" if rate > 0.2 else "moderate",
        f"{len(unreachable)} of {len(checked)} reported baseline p-values cannot be produced "
        "by the means and SDs printed in the same row, under any rounding and either "
        "form of the t-test.",
        n_checked=len(checked),
        unreachable_count=len(unreachable),
        unreachable=unreachable[:100],
        variables=checked[:100],
    )


def run_randomization_checks(df: pd.DataFrame, group_column: str | None = None) -> list[Finding]:
    return [carlisle_method(df, group_column)]


def _reachable_p_range(
    arms: list[tuple[float, float, float]], row: pd.Series
) -> tuple[float, float] | None:
    """Every p obtainable from these summary statistics, given how they were rounded."""
    deltas = []
    for arm in (1, 2):
        deltas.append(
            (
                0.5 * 10 ** -decimal_places(row.get(f"m{arm}")),
                0.5 * 10 ** -decimal_places(row.get(f"s{arm}")),
            )
        )
    values: list[float] = []
    for dm1 in (-1, 1):
        for ds1 in (-1, 1):
            for dm2 in (-1, 1):
                for ds2 in (-1, 1):
                    n1, m1, s1 = arms[0]
                    n2, m2, s2 = arms[1]
                    m1 += dm1 * deltas[0][0]
                    s1 = max(1e-9, s1 + ds1 * deltas[0][1])
                    m2 += dm2 * deltas[1][0]
                    s2 = max(1e-9, s2 + ds2 * deltas[1][1])
                    for equal_var in (True, False):
                        result = stats.ttest_ind_from_stats(
                            m1, s1, int(n1), m2, s2, int(n2), equal_var=equal_var
                        )
                        if np.isfinite(result.pvalue):
                            values.append(float(result.pvalue))
    if not values:
        return None
    return min(values), max(values)


@functools.lru_cache(maxsize=1)
def _carlisle_reference() -> tuple[np.ndarray, np.ndarray]:
    """Empirical CDF of baseline p-values in real published trials.

    Carlisle's 29,789 baseline variables from 5087 trials. Published summary
    statistics are rounded, which creates ties and pushes p-values toward 1,
    so the real distribution is markedly non-uniform: 13.1% of it lies above
    0.95 against 5% for a uniform distribution. Testing a published baseline
    table against a uniform null flags honest papers -- at 500 variables it
    does so essentially always. See scripts/scifraudscan/reference/README.md.
    """
    table = pd.read_csv(REFERENCE_FILE)
    return (
        table["p_value"].to_numpy(dtype=float),
        table["cumulative_proportion"].to_numpy(dtype=float),
    )


def carlisle_reference_cdf(p: np.ndarray | float) -> np.ndarray:
    """Proportion of real published baseline p-values at or below `p`."""
    quantiles, cumulative = _carlisle_reference()
    return np.interp(p, quantiles, cumulative, left=0.0, right=1.0)


def _reference_monte_carlo(
    p: np.ndarray, simulations: int = 20000, seed: int = 0
) -> tuple[float, float, float]:
    """Test mean(p) against samples of the same size drawn from the reference.

    A KS test is not valid here. The reference distribution is atomic --
    rounded summary statistics produce ties, and 11% of real baseline p-values
    sit above 0.99 -- and KS against an atomic reference over-rejects badly:
    it flags honest collections of 500 variables essentially always. Drawing
    the null distribution from the reference itself costs nothing and holds
    the false positive rate at the nominal level.

    Comparing mean(p) is equivalent to comparing the area under the CDF, which
    is the summary Bolland et al. use.
    """
    quantiles, cumulative = _carlisle_reference()
    rng = np.random.default_rng(seed)
    draws = np.interp(rng.random((simulations, len(p))), cumulative, quantiles)
    null_means = draws.mean(axis=1)
    observed = float(p.mean())
    reference_mean = float(np.interp(np.linspace(0, 1, 20001), cumulative, quantiles).mean())
    too_balanced = float((null_means >= observed).mean())
    too_different = float((null_means <= observed).mean())
    return too_balanced, too_different, reference_mean


def _p_two_arms(a: tuple[float, float, float], b: tuple[float, float, float]) -> float | None:
    (n1, m1, s1), (n2, m2, s2) = a, b
    return float(
        stats.ttest_ind_from_stats(m1, s1, int(n1), m2, s2, int(n2), equal_var=False).pvalue
    )


def _p_many_arms(arms: list[tuple[float, float, float]]) -> float | None:
    """One-way ANOVA reconstructed from group sizes, means and SDs."""
    total = sum(n for n, _, _ in arms)
    k = len(arms)
    if total <= k:
        return None
    grand_mean = sum(n * m for n, m, _ in arms) / total
    between = sum(n * (m - grand_mean) ** 2 for n, m, _ in arms) / (k - 1)
    within = sum((n - 1) * sd**2 for n, _, sd in arms) / (total - k)
    if within <= 0:
        return None
    return float(stats.f.sf(between / within, k - 1, total - k))
