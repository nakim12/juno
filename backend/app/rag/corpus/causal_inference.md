---
title: Causal Inference Foundations for MMM
topic: causal_inference
source: juno_kb
credibility_tier: synthesis
---
Marketing mix modeling is fundamentally a causal question dressed as a
regression: what would sales have been if we had spent differently? Answering it
requires more than fitting a curve to historical data, because the media spends
themselves are chosen by marketers who respond to expected demand. Spend often
rises ahead of known high-demand periods, which induces a spurious positive
correlation between spend and sales that is not causal.

The core threats to causal validity in MMM are confounding, reverse causality,
and selection. Confounding occurs when an unobserved driver (a promotion, a
competitor's exit, a macro shock) moves both spend and sales. Reverse causality
occurs when budgets are set based on anticipated sales. Selection occurs when
media is targeted at audiences already likely to convert. Each inflates
apparent effectiveness if not addressed.

Good MMM practice mitigates these with careful controls (seasonality, trend,
promotions, pricing, distribution), with priors informed by experiments, and
with holdout validation. But no purely observational model fully escapes these
threats, which is why incrementality experiments remain the gold standard and
why MMM outputs should always be framed as estimates with uncertainty rather
than as measured facts.

When interpreting a model, be explicit about the difference between association
and incrementality. Language like "the model attributes X to this channel" is
appropriate; language like "this channel caused X" overstates what an
observational model can establish on its own.
