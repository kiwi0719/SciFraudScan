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
            if not grim_consistent(n, mean, mean_decimals, scale_step):
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
            if sd is not None:
                sd_checked += 1
                failure = _sd_failure(n, mean, sd, scale_min, scale_max, mean_decimals, row)
                if failure:
                    sd_failures.append({"row": int(index), **failure})

        statistic = safe_float(row.get("stat"))
        reported_p = safe_float(row.get("p"))
        df1 = safe_float(row.get("df1"))
        df2 = safe_float(row.get("df2"))
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
        return not_applicable(check, "No row supplied N, mean and SD together.")
    if not failures:
        return clear(check, f"All {checked} mean/SD pairs are attainable.", n_checked=checked)
    return flag(
        check,
        "high",
        f"{len(failures)} of {checked} mean/SD pairs are impossible on the stated scale.",
        failures=failures[:50],
        failure_count=len(failures),
        n_checked=checked,
    )


def _statcheck_finding(mismatches: list[dict[str, object]], checked: int) -> Finding:
    check = "Reported p-value Consistency"
    if checked == 0:
        return not_applicable(
            check, "No row supplied a test statistic, its df and a reported p-value."
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
        f"{len(mismatches)} of {checked} reported p-values disagree with the value recomputed "
        f"from the statistic and df; {len(decision_errors)} change significance at alpha=.05.",
        mismatches=mismatches[:50],
        mismatch_count=len(mismatches),
        decision_error_count=len(decision_errors),
        n_checked=checked,
    )


def _as_int(value: object) -> int | None:
    number = safe_float(value)
    if number is None or number <= 0:
        return None
    return round(number)
