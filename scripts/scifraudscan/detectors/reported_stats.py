"""Consistency of statistics as reported in a manuscript.

GRIM and GRIMMER are implemented here rather than taken from a wrapper
package: both are short, exact, integer-arithmetic tests, and a reported value
that fails one is arithmetically impossible rather than merely unusual. That
makes them the most actionable checks in this toolkit -- and the reason the
implementation is written out in full and covered by tests.

Nothing here runs a stochastic SPRITE search. The SD feasibility check is the
deterministic variance-bounds test, which is weaker than SPRITE but never
returns a different answer on a re-run.
"""

from __future__ import annotations

import functools
import math

import numpy as np
import pandas as pd
from scipy import stats

from scifraudscan.models import Finding, clear, flag, not_applicable
from scifraudscan.utils import decimal_places, safe_float


def grim_consistent(n: int, mean: float, decimals: int, scale_step: float = 1.0) -> bool:
    """Can `mean` arise from n integer-scale responses rounded to `decimals`?

    Brown & Heathers (2017). With scale_step s, admissible totals are multiples
    of s, so the granularity of the total is n*s rather than 1.
    """
    if n <= 0 or scale_step <= 0:
        return False
    granularity = scale_step / n
    quotient = mean / granularity
    tolerance = 10 ** -(decimals + 6)
    for candidate in {math.floor(quotient), round(quotient), math.ceil(quotient)}:
        reconstructed = candidate * granularity
        if abs(round(reconstructed, decimals) - mean) <= tolerance:
            return True
    return False


def sd_bounds(n: int, mean: float, scale_min: float, scale_max: float) -> tuple[float, float]:
    """Smallest and largest sample SD reachable by n integers in [min, max] with this mean."""
    if n <= 1 or scale_min >= scale_max:
        return (0.0, 0.0)
    factor = n / (n - 1)
    # Maximum: all mass at the two endpoints.
    max_population_variance = max(0.0, (mean - scale_min) * (scale_max - mean))
    maximum = math.sqrt(max_population_variance * factor)
    # Minimum: integers packed as tightly around the mean as the total allows.
    total = round(mean * n)
    base, remainder = divmod(int(total), n)
    values = np.array([base + 1] * remainder + [base] * (n - remainder), dtype=float)
    minimum = float(values.std(ddof=1)) if n > 1 else 0.0
    return (minimum, maximum)


def grimmer_consistent(
    n: int,
    mean: float,
    sd: float,
    mean_decimals: int,
    sd_decimals: int,
) -> bool:
    """Is (mean, SD) reachable by n integers? Anaya (2016).

    For integer data the sum of squares is an integer with the same parity as
    the total, so the test is whether any such integer falls inside the
    interval implied by the reported values' rounding intervals.
    """
    if n <= 1:
        return False
    mean_half = 0.5 * 10**-mean_decimals
    sd_half = 0.5 * 10**-sd_decimals
    sd_low = max(0.0, sd - sd_half)
    sd_high = sd + sd_half

    total_low = math.ceil((mean - mean_half) * n - 1e-9)
    total_high = math.floor((mean + mean_half) * n + 1e-9)
    for total in range(total_low, total_high + 1):
        # var = (SS - total^2/n) / (n-1)
        ss_low = sd_low**2 * (n - 1) + total**2 / n
        ss_high = sd_high**2 * (n - 1) + total**2 / n
        for sum_squares in range(math.ceil(ss_low - 1e-9), math.floor(ss_high + 1e-9) + 1):
            if sum_squares >= 0 and (sum_squares - total) % 2 == 0:
                return True
    return False


@functools.lru_cache(maxsize=256)
def _mann_whitney_null(n1: int, n2: int) -> np.ndarray:
    """Exact distribution of U under the null, assuming no ties.

    Counts arrangements by the standard recurrence
    f(m, n, u) = f(m-1, n, u-n) + f(m, n-1, u), then normalises.
    """
    counts = np.zeros((n1 + 1, n2 + 1, n1 * n2 + 1))
    counts[0, :, 0] = 1.0
    counts[:, 0, 0] = 1.0
    for m in range(1, n1 + 1):
        for n in range(1, n2 + 1):
            shifted = np.zeros(n1 * n2 + 1)
            if n <= m * n:
                shifted[n:] = counts[m - 1, n, : n1 * n2 + 1 - n]
            counts[m, n] = shifted + counts[m, n - 1]
    total = counts[n1, n2].sum()
    return counts[n1, n2] / total


def mann_whitney_p_upper_bound(u: float, n1: int, n2: int) -> float | None:
    """Largest two-sided p the reported U can correspond to.

    Ties shrink the variance of U and can only move p downward, and they
    cannot be recovered from a paper that reports only U. The no-tie p is
    therefore an upper bound, which makes the consistency check one-sided: a
    reported p *below* this is ordinary, a reported p *above* it is not
    reachable however the data were tied.

    The bound is the largest value produced by the exact null distribution and
    by the normal approximation with and without a continuity correction,
    since a paper rarely says which of them it used.

    The test is symmetric about n1*n2/2, so it does not matter whether the
    paper reports U1, U2 or the smaller of the two.
    """
    if n1 < 1 or n2 < 1:
        return None
    maximum = n1 * n2
    if not 0 <= u <= maximum:
        return None
    centre = maximum / 2
    distance = abs(u - centre)
    sd = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)

    # Papers do not say which form of the test produced their p, and the three
    # in common use disagree by a few thousandths at these sample sizes. Take
    # the largest, so the bound is never tighter than the method the authors
    # actually used.
    candidates = [
        float(2 * stats.norm.sf(distance / sd)),
        float(2 * stats.norm.sf(max(0.0, distance - 0.5) / sd)),
    ]
    if n1 * n2 <= 4000:  # exact is cheap at these sizes and correct for small n
        null = _mann_whitney_null(n1, n2)
        support = np.arange(maximum + 1)
        candidates.append(float(null[np.abs(support - centre) >= distance - 1e-9].sum()))
    return min(1.0, max(candidates))


MANN_WHITNEY_NAMES = frozenset({"u", "mwu", "mannwhitney", "mann-whitney", "mann_whitney"})


def p_from_statistic(test: str, statistic: float, df1: float, df2: float | None) -> float | None:
    if test == "t":
        return float(stats.t.sf(abs(statistic), df1) * 2)
    if test == "f" and df2 is not None:
        return float(stats.f.sf(statistic, df1, df2))
    if test in {"chi2", "chisq", "chi-square", "chisquare"}:
        return float(stats.chi2.sf(statistic, df1))
    if test in {"r", "correlation"}:
        if df1 <= 0 or abs(statistic) >= 1:
            return None
        t_value = statistic * math.sqrt(df1 / (1 - statistic**2))
        return float(stats.t.sf(abs(t_value), df1) * 2)
    return None


def validate_reported_stats(stats_df: pd.DataFrame) -> list[Finding]:
    grim_failures: list[dict[str, object]] = []
    grim_checked = 0
    sd_failures: list[dict[str, object]] = []
    sd_checked = 0
    mismatches: list[dict[str, object]] = []
    p_checked = 0

    for index, row in stats_df.iterrows():
        test = str(row.get("test", "")).strip().lower()
        n = _as_int(row.get("n"))
        mean = safe_float(row.get("mean"))
        sd = safe_float(row.get("sd"))
        scale_min = safe_float(row.get("scale_min"))
        scale_max = safe_float(row.get("scale_max"))
        scale_step = safe_float(row.get("scale_step")) or 1.0

        if test in {"grim", "grimmer", "sprite"} and n and mean is not None:
            grim_checked += 1
            mean_decimals = decimal_places(row.get("mean"))
            mean_attainable = grim_consistent(n, mean, mean_decimals, scale_step)
            if not mean_attainable:
                grim_failures.append(
                    {
                        "row": int(index),
                        "n": n,
                        "reported_mean": mean,
                        "decimals": mean_decimals,
                        "scale_step": scale_step,
                        "reason": "no set of n responses rounds to this mean",
                    }
                )

            # GRIMMER needs only N, mean and SD; the variance-bounds test additionally
            # needs the scale, so the two run independently of each other.
            #
            # An SD is only testable when the mean is attainable. If no integer
            # total produces the reported mean, GRIMMER fails for that reason
            # alone and says nothing about the SD, so counting it as an SD
            # failure would report the same defect twice.
            if sd is not None and mean_attainable:
                sd_checked += 1
                failure = _sd_failure(n, mean, sd, scale_min, scale_max, mean_decimals, row)
                if failure:
                    sd_failures.append({"row": int(index), **failure})

        statistic = safe_float(row.get("stat"))
        reported_p = safe_float(row.get("p"))
        df1 = safe_float(row.get("df1"))
        df2 = safe_float(row.get("df2"))

        if test in MANN_WHITNEY_NAMES:
            outcome = _mann_whitney_mismatch(row, statistic, reported_p, int(index))
            if outcome is not None:
                p_checked += 1
                if outcome:
                    mismatches.append(outcome)
            continue

        if statistic is None or reported_p is None or df1 is None:
            continue
        computed = p_from_statistic(test, statistic, df1, df2)
        if computed is None:
            continue
        p_checked += 1
        decimals = max(decimal_places(row.get("p")), 2)
        consistent = round(computed, decimals) == round(reported_p, decimals)
        # A t or r reported one-tailed is not an error, so accept either tail.
        if not consistent and test in {"t", "r", "correlation"}:
            consistent = round(computed / 2, decimals) == round(reported_p, decimals)
        if not consistent:
            mismatches.append(
                {
                    "row": int(index),
                    "test": test,
                    "statistic": statistic,
                    "df1": df1,
                    "df2": df2,
                    "reported_p": reported_p,
                    "computed_p": float(f"{computed:.6g}"),
                    "crosses_alpha": bool((reported_p < 0.05) != (computed < 0.05)),
                }
            )

    return [
        _grim_finding(grim_failures, grim_checked),
        _sd_finding(sd_failures, sd_checked),
        _statcheck_finding(mismatches, p_checked),
    ]


def _sd_failure(
    n: int,
    mean: float,
    sd: float,
    scale_min: float | None,
    scale_max: float | None,
    mean_decimals: int,
    row: pd.Series,
) -> dict[str, object] | None:
    if scale_min is not None and scale_max is not None:
        minimum, maximum = sd_bounds(n, mean, scale_min, scale_max)
        tolerance = 0.5 * 10 ** -decimal_places(row.get("sd"))
        if sd > maximum + tolerance or sd < minimum - tolerance:
            return {
                "n": n,
                "reported_mean": mean,
                "reported_sd": sd,
                "min_possible_sd": round(minimum, 6),
                "max_possible_sd": round(maximum, 6),
                "scale": [scale_min, scale_max],
                "reason": "SD is outside the range attainable on this scale",
            }
    if not grimmer_consistent(n, mean, sd, mean_decimals, decimal_places(row.get("sd"))):
        return {
            "n": n,
            "reported_mean": mean,
            "reported_sd": sd,
            "reason": "no integer sum of squares matches this mean and SD (GRIMMER)",
        }
    return None


def _grim_finding(failures: list[dict[str, object]], checked: int) -> Finding:
    check = "GRIM"
    if checked == 0:
        return not_applicable(check, "No row supplied both an integer N and a reported mean.")
    if not failures:
        return clear(
            check,
            f"All {checked} reported means are attainable for their N.",
            n_checked=checked,
        )
    return flag(
        check,
        "high",
        f"{len(failures)} of {checked} reported means cannot arise from N responses "
        "on the stated scale.",
        failures=failures[:50],
        failure_count=len(failures),
        n_checked=checked,
    )


def _sd_finding(failures: list[dict[str, object]], checked: int) -> Finding:
    check = "SD Feasibility (GRIMMER / variance bounds)"
    if checked == 0:
        return not_applicable(
            check,
            "No row supplied N, mean and SD together with an attainable mean. An SD can "
            "only be tested once the mean it belongs to is possible.",
        )
    if not failures:
        return clear(
            check,
            f"All {checked} testable mean/SD pairs are attainable.",
            n_testable=checked,
        )
    return flag(
        check,
        "high",
        f"{len(failures)} of {checked} testable mean/SD pairs are impossible; "
        "an SD is testable only where the mean itself is attainable.",
        failures=failures[:50],
        failure_count=len(failures),
        n_testable=checked,
    )


def _statcheck_finding(mismatches: list[dict[str, object]], checked: int) -> Finding:
    check = "Reported p-value Consistency"
    if checked == 0:
        return not_applicable(
            check,
            "No row supplied a test statistic with its df (or, for Mann-Whitney U, its "
            "group sizes) and a reported p-value.",
        )
    if not mismatches:
        return clear(
            check,
            f"All {checked} reported p-values match the recomputed values.",
            n_checked=checked,
        )
    decision_errors = [m for m in mismatches if m["crosses_alpha"]]
    severity = "high" if decision_errors else "moderate"
    return flag(
        check,
        severity,
        f"{len(mismatches)} of {checked} reported p-values are not consistent with the test "
        f"statistic reported beside them; {len(decision_errors)} change significance "
        "at alpha=.05.",
        mismatches=mismatches[:50],
        mismatch_count=len(mismatches),
        decision_error_count=len(decision_errors),
        n_checked=checked,
    )


def _mann_whitney_mismatch(
    row: pd.Series, statistic: float | None, reported_p: float | None, index: int
) -> dict[str, object] | bool | None:
    """None if the row cannot be checked, False if it is fine, else the mismatch.

    One-sided by necessity. Ties shrink p and cannot be recovered from a
    published U, so only a reported p *above* the no-tie value is a problem.
    """
    n1 = _as_int(row.get("n1"))
    n2 = _as_int(row.get("n2"))
    if statistic is None or reported_p is None or n1 is None or n2 is None:
        return None
    upper_bound = mann_whitney_p_upper_bound(statistic, n1, n2)
    if upper_bound is None:
        return None
    tolerance = 0.5 * 10 ** -max(decimal_places(row.get("p")), 2)
    if reported_p <= upper_bound + tolerance:
        return False
    return {
        "row": index,
        "test": "mann-whitney u",
        "statistic": statistic,
        "n1": n1,
        "n2": n2,
        "reported_p": reported_p,
        "max_possible_p": float(f"{upper_bound:.6g}"),
        "crosses_alpha": bool((reported_p < 0.05) != (upper_bound < 0.05)),
        "reason": (
            "reported p exceeds the largest value this U can produce; ties only "
            "move p downward, so they cannot explain it"
        ),
    }


def _as_int(value: object) -> int | None:
    number = safe_float(value)
    if number is None or number <= 0:
        return None
    return round(number)
