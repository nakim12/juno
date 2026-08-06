---
title: Model Fit, Holdout, and Backtesting
topic: holdout_validation
source: juno_kb
credibility_tier: synthesis
---
Fit metrics tell you how well a marketing mix model reproduces observed
outcomes. In-sample R-squared measures the fraction of variance explained on the
data the model was trained on, and MAPE (mean absolute percentage error)
measures average prediction error. High in-sample fit is necessary but far from
sufficient: a flexible model can fit the training period well and still
generalize poorly, and it can predict the total accurately while mis-attributing
across channels.

Holdout validation is the stronger test. The model is fit on an earlier period
and evaluated on a held-out later period it never saw. A small gap between
in-sample and holdout error indicates the model generalizes; a large gap
signals overfitting. Time-series cross-validation (rolling-origin backtesting)
extends this by repeatedly training up to a point and testing on the next
window, which gives a more robust picture across different market conditions.

It is important to remember what these metrics cannot do. They validate
predictive accuracy, not causal attribution. Two models with identical holdout
error can disagree sharply on how much credit each channel deserves. That is why
predictive validation must be paired with experimental calibration to trust the
per-channel numbers, not just the aggregate forecast.

When reviewing diagnostics, look at the holdout error alongside the in-sample
error, and be cautious about interpreting channel-level ROI from a model whose
holdout performance is weak or unreported.
