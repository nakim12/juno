---
title: Uncertainty and Credible Intervals
topic: credible_intervals
source: juno_kb
credibility_tier: synthesis
---
A credible interval is the Bayesian analogue of a confidence interval: a 95%
credible interval means the model assigns 95% posterior probability to the true
value lying within that range. In a marketing mix model, the width of the
interval around a channel's ROI is often more informative than the point
estimate itself, because it tells you how much the data actually constrain the
answer.

Interval width has direct consequences for decisions and for calibration. A
narrow interval (for example an ROI of 3.2 with bounds of 2.8 to 3.6) supports a
confident recommendation. A wide interval (an ROI of 1.7 with bounds of 0.6 to
2.8) spans from "barely breaks even" to "highly profitable," so any action based
on the point estimate alone is fragile. A useful heuristic is to compare the
interval width to the point estimate: when the width is as large as or larger
than the point, treat the estimate as low confidence.

Calibration is the property that confidence matches correctness: when a model or
an agent says it is highly confident, it should be right at that rate. An
overconfident system reports narrow intervals or "high confidence" while being
frequently wrong; an underconfident one hedges even when the data are clear.
Expected calibration error measures the average gap between stated confidence
and observed accuracy across many cases.

Good interpretation ties every confidence claim to a source of uncertainty:
interval width, model fit diagnostics, data span, or detected structural risks
like collinearity. Confidence should never be asserted without a reason.
