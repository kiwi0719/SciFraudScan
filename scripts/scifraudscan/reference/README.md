# Vendored reference distribution

`carlisle_baseline_p_reference.csv` is the empirical distribution of baseline
p-values from real published randomized trials: Carlisle's corpus of 29,789
baseline variables across 5087 trials.

- Source: the `rep_carlisle` internal dataset of the **reappraised** R package
  by Mark Bolland, <https://cran.r-project.org/package=reappraised> (v0.2),
  MIT licence, Copyright (c) 2023 reappraised authors.
- Underlying study: Carlisle, J. B. (2017). Data fabrication and other reasons
  for non-random sampling in 5087 randomised, controlled trials in anaesthetic
  and general medical journals. *Anaesthesia* 72(8), 944-952.
  doi:[10.1111/anae.13938](https://doi.org/10.1111/anae.13938)
- See also Bolland, M. J., Gamble, G. D., Grey, A., & Avenell, A. (2020).
  Empirically generated reference proportions for baseline p values from
  rounded summary statistics. *Anaesthesia* 75, 1685-1687.
  doi:[10.1111/anae.15165](https://doi.org/10.1111/anae.15165)

The 29,998-point step function was reduced to its quantile function on an even
1001-point grid; maximum error in the recovered CDF is 0.0014.

## Why this exists

Baseline p-values computed from *published, rounded* summary statistics are
not uniformly distributed, even when the trial is honest. In this reference,
13.1% of real baseline p-values exceed 0.95 and 11.1% exceed 0.99, against 5%
and 1% under a uniform distribution. Rounding creates ties and near-ties,
which push p toward 1.

Testing a published baseline table against a uniform null therefore flags
honest papers. Measured against this reference distribution, a uniform null at
alpha = 0.01 flags honest, real-literature-shaped collections at these rates:

| Baseline variables | False positive rate |
|---|---|
| 20 | 2% |
| 50 | 4% |
| 100 | 15% |
| 200 | 52% |
| 500 | **100%** |

That is why `baseline_summary_check` compares against this distribution and
not against uniform. The raw-data path (`carlisle_method`) computes p-values
from unrounded participant data and keeps the uniform null, which is correct
there.
