"""Regenerate examples/ from a fixed seed.

    python benchmarks/generate_examples.py

clean_trial.csv is honestly generated and every check should clear it.
fabricated_trial.csv is the same trial with five defects planted in it:

  1. baseline covariates balanced across arms after the fact (Carlisle)
  2. bmi_index silently derived from bmi        (linear duplicate)
  3. outcome scores nudged to end in 0 or 5     (terminal digit preference)
  4. rows 200-211 copied from rows 40-51        (repeated value blocks)
  5. assay_reading is a ramp plus a 12-row cycle (autocorrelation, spectral)

reported_stats.csv and p_values.csv carry their own planted failures. Run
tests/test_benchmark.py to check that the toolkit still separates the two.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(20260921)
N = 240

# --- clean_trial.csv: a plausible, honestly-generated RCT ---------------------
arm = rng.permutation(np.array(["control"] * (N // 2) + ["treatment"] * (N // 2)))
age = np.round(rng.normal(54, 12, N), 1)
bmi = np.round(rng.normal(27.4, 4.1, N), 1)
sbp = np.round(rng.normal(132, 15, N), 0)
crp = np.round(np.exp(rng.normal(0.6, 0.9, N)), 2)
score = np.clip(np.round(rng.normal(41, 9, N) + (arm == "treatment") * 3.2, 0), 0, 100)
day = np.arange(N)
# a Table 1 of the size a real trial reports
hba1c = np.round(rng.normal(7.1, 1.0, N), 1)
egfr = np.round(rng.normal(88, 18, N), 0)
ldl = np.round(rng.normal(3.2, 0.8, N), 2)
weight_kg = np.round(rng.normal(81, 14, N), 1)
diastolic_bp = np.round(rng.normal(78, 9, N), 0)
years_since_dx = np.round(rng.gamma(2.0, 3.0, N), 1)
clean = pd.DataFrame({
    "subject_id": [f"S{i:04d}" for i in range(1, N + 1)],
    "arm": arm, "enrol_day": day, "age": age, "bmi": bmi,
    "systolic_bp": sbp, "diastolic_bp": diastolic_bp, "weight_kg": weight_kg,
    "hba1c": hba1c, "egfr": egfr, "ldl_mmol_l": ldl,
    "years_since_dx": years_since_dx, "crp_mg_l": crp, "outcome_score": score,
})
clean.to_csv("examples/clean_trial.csv", index=False)

# --- fabricated_trial.csv: same shape, several planted defects ----------------
fab = clean.copy()
# 1. baseline arms made implausibly balanced (Carlisle signature)
for col in ["age", "bmi", "systolic_bp", "diastolic_bp", "weight_kg",
            "hba1c", "egfr", "ldl_mmol_l", "years_since_dx", "crp_mg_l"]:
    values = fab[col].to_numpy(dtype=float).copy()
    grand_mean = values.mean()
    for group in ("control", "treatment"):
        mask = (fab["arm"] == group).to_numpy()
        values[mask] = values[mask] - values[mask].mean() + grand_mean
    fab[col] = np.round(values, 2)
# 2. a column silently derived from another
fab["bmi_index"] = np.round(fab["bmi"] * 1.35 + 2.0, 3)
# 3. terminal-digit preference: outcomes nudged to end in 0 or 5
nudge = rng.random(N) < 0.55
fab.loc[nudge, "outcome_score"] = (fab.loc[nudge, "outcome_score"] / 5).round() * 5
# 4. a block of rows copied from earlier in the file
fab.iloc[200:212, 3:] = fab.iloc[40:52, 3:].to_numpy()
# 5. a "measured" series that is really a fixed ramp plus a cycle
fab["assay_reading"] = np.round(
    50 + 0.25 * day + 6 * np.sin(2 * np.pi * day / 12) + rng.normal(0, 0.05, N), 3)
fab.to_csv("examples/fabricated_trial.csv", index=False)

# --- reported_stats.csv: GRIM/GRIMMER/statcheck cases -------------------------
pd.DataFrame([
    # impossible: 3.45 cannot be a mean of 20 integer responses
    dict(test="grim", n=20, mean="3.46", sd="", scale_min=1, scale_max=5, scale_step=1,
         stat="", df1="", df2="", p="", note="impossible mean"),
    # possible: 3.45 = 69/20 fails, but 3.40 = 68/20 works
    dict(test="grim", n=20, mean="3.40", sd="", scale_min=1, scale_max=5, scale_step=1,
         stat="", df1="", df2="", p="", note="attainable mean"),
    # SD far above what a 1-5 scale can produce at this mean
    dict(test="grimmer", n=30, mean="4.50", sd="2.80", scale_min=1, scale_max=5, scale_step=1,
         stat="", df1="", df2="", p="", note="impossible SD"),
    dict(test="grimmer", n=30, mean="3.00", sd="1.20", scale_min=1, scale_max=5, scale_step=1,
         stat="", df1="", df2="", p="", note="attainable mean and SD"),
    # reported p disagrees with t(18)=2.35 and crosses alpha
    dict(test="t", n="", mean="", sd="", scale_min="", scale_max="", scale_step="",
         stat=2.35, df1=18, df2="", p="0.004", note="p inconsistent, decision error"),
    dict(test="t", n="", mean="", sd="", scale_min="", scale_max="", scale_step="",
         stat=2.35, df1=18, df2="", p="0.030", note="p consistent"),
    dict(test="f", n="", mean="", sd="", scale_min="", scale_max="", scale_step="",
         stat=4.20, df1=2, df2=57, p="0.020", note="p consistent"),
    dict(test="chi2", n="", mean="", sd="", scale_min="", scale_max="", scale_step="",
         stat=7.82, df1=3, df2="", p="0.050", note="p consistent"),
]).to_csv("examples/reported_stats.csv", index=False)

# --- p_values.csv: a literature with a just-below-.05 pile-up ----------------
honest = rng.beta(0.45, 6.0, 55)
hacked = rng.uniform(0.0455, 0.0499, 26)
just_over = rng.uniform(0.0500, 0.0549, 6)
mid = rng.uniform(0.026, 0.045, 24)
pd.DataFrame({"p": np.round(np.concatenate([honest, hacked, just_over, mid]), 4)}) \
  .sample(frac=1, random_state=7).to_csv("examples/p_values.csv", index=False)
print("written")
