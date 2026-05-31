from __future__ import annotations

import pandas as pd
import pysprite
from scipy import stats

from research_integrity_screen.models import Finding
from research_integrity_screen.utils import safe_float


def grim_possible(n: int, mean: float, scale_step: float = 1.0) -> bool:
    if scale_step != 1:
        return _scaled_grim_possible(n, mean, scale_step)
    return bool(pysprite.grim(n, mean, prec=_decimal_precision(mean)))


def sprite_possible(
    n: int,
    mean: float,
    sd: float,
    scale_min: float,
    scale_max: float,
    scale_step: float = 1.0,
    tolerance: float = 0.01,
) -> bool:
    if n <= 1 or scale_step <= 0 or scale_min > scale_max:
        return False
    if scale_step != 1:
        return False
    try:
        sprite = pysprite.Sprite(
            n,
            mean,
            sd,
            _decimal_precision(mean),
            _decimal_precision(sd),
            int(scale_min),
            int(scale_max),
        )
        result = sprite.find_possible_distribution()
    except ValueError:
        return False
    return bool(result and result[0] == "Success")


def validate_reported_stats(stats_df: pd.DataFrame) -> list[Finding]:
    findings: list[Finding] = []
    grim_failures = []
    sprite_failures = []
    p_mismatches = []

    for index, row in stats_df.iterrows():
        test = str(row.get("test", "")).strip().lower()
        n = _int(row.get("n"))
        mean = safe_float(row.get("mean"))
        sd = safe_float(row.get("sd"))
        scale_min = safe_float(row.get("scale_min")) or 1.0
        scale_max = safe_float(row.get("scale_max")) or 5.0
        scale_step = safe_float(row.get("scale_step")) or 1.0

        if test == "grim" and n and mean is not None:
            if not grim_possible(n, mean, scale_step):
                grim_failures.append({"row": int(index), "n": n, "mean": mean})
        if test == "sprite" and n and mean is not None and sd is not None:
            if not sprite_possible(n, mean, sd, scale_min, scale_max, scale_step):
                sprite_failures.append({"row": int(index), "n": n, "mean": mean, "sd": sd})

        stat = safe_float(row.get("stat"))
        p = safe_float(row.get("p"))
        df1 = safe_float(row.get("df1"))
        df2 = safe_float(row.get("df2"))
        computed = _computed_p(test, stat, df1, df2)
        if p is not None and computed is not None and abs(p - computed) > max(0.005, computed * 0.05):
            p_mismatches.append(
                {
                    "row": int(index),
                    "test": test,
                    "reported_p": p,
                    "computed_p": round(computed, 6),
                }
            )

    findings.append(
        Finding(
            "GRIM",
            _status(min(100.0, len(grim_failures) * 50)),
            min(100.0, len(grim_failures) * 50),
            f"{len(grim_failures)} reported means are impossible for N and scale step.",
            {"failures": grim_failures[:20], "failure_count": len(grim_failures)},
        )
    )
    findings.append(
        Finding(
            "SPRITE",
            _status(min(100.0, len(sprite_failures) * 50)),
            min(100.0, len(sprite_failures) * 50),
            f"{len(sprite_failures)} mean/SD combinations are inconsistent with the scale.",
            {"failures": sprite_failures[:20], "failure_count": len(sprite_failures)},
        )
    )
    findings.append(
        Finding(
            "Statcheck",
            _status(min(100.0, len(p_mismatches) * 45)),
            min(100.0, len(p_mismatches) * 45),
            f"{len(p_mismatches)} reported p-values disagree with recomputed values.",
            {"mismatches": p_mismatches[:20], "mismatch_count": len(p_mismatches)},
        )
    )
    return findings


def _computed_p(test: str, stat_value: float | None, df1: float | None, df2: float | None) -> float | None:
    if stat_value is None or df1 is None:
        return None
    if test == "t":
        return float(stats.t.sf(abs(stat_value), df1) * 2)
    if test == "f" and df2 is not None:
        return float(stats.f.sf(stat_value, df1, df2))
    if test in {"chi2", "chisq", "chi-square"}:
        return float(stats.chi2.sf(stat_value, df1))
    return None


def _int(value: object) -> int | None:
    number = safe_float(value)
    if number is None:
        return None
    return int(round(number))


def _scaled_grim_possible(n: int, mean: float, scale_step: float) -> bool:
    total = mean * n / scale_step
    return abs(total - round(total)) < 1e-8


def _decimal_precision(value: float) -> int:
    text = f"{value:.12g}"
    if "." not in text:
        return 0
    return len(text.rstrip("0").split(".", maxsplit=1)[1])


def _status(score: float) -> str:
    if score >= 70:
        return "High Risk"
    if score >= 35:
        return "Warning"
    return "Pass"
