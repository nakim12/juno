---
title: Common MMM Pitfalls and Failure Modes
topic: failure_modes
source: juno_kb
credibility_tier: synthesis
---
Marketing mix models fail in recognizable ways, and a good interpreter names
these risks explicitly rather than presenting every number as trustworthy. The
most common pitfalls cluster around confounding, identifiability, and
extrapolation.

Baseline leakage is the classic failure: unmodeled seasonal or promotional
demand gets attributed to whatever media was running, inflating ROI. Related is
seasonality confounding, where spend rises with demand and the model mistakes
correlation for effectiveness. Both are worst when the data span is short.

Identifiability failures come from collinear channels whose spends move together;
the model splits credit between them almost arbitrarily, producing wide,
unstable intervals. Overfitting is another: a model that fits the training
period beautifully but has weak holdout performance is telling you its
attribution should not be trusted.

Extrapolation risk appears when a recommendation pushes a channel far outside its
historically observed spend range, where the saturation curve is guesswork.
High-adstock estimates are hard to identify and often over-stated. And there is
the interpretation-layer failure of overconfidence: stating "high confidence" on
a channel whose credible interval is wide, or giving a precise budget
recommendation without noting the uncertainty behind it.

A trustworthy analysis actively checks for each of these — wide intervals,
collinear channels, short data spans, weak holdout fit, saturation, and
extrapolation — and flags the ones present as structural risks, lowering
confidence accordingly instead of asserting precision the data cannot support.
