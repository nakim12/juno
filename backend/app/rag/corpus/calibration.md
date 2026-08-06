---
title: Calibrating MMM with Experiments
topic: calibration
source: juno_kb
credibility_tier: synthesis
---
A marketing mix model is a correlational model fit to observational data, so its
coefficients can be biased by confounding, collinearity, and mis-specification.
Calibration is the practice of anchoring the model to causal ground truth from
experiments — most often geo-based incrementality tests or conversion lift
studies. When a lift test says a channel's true incremental ROI is around 2.0,
that estimate can be used as a prior or a constraint so the model's coefficient
does not drift to an implausible value.

Calibration matters because a well-fit model is not the same as a correct model.
A model can predict sales accurately while attributing them to the wrong
channels, because correlated media spends are hard to disentangle. Experiments
break the correlation deliberately (for example by turning a channel off in
some geographies) and therefore measure incrementality directly.

The strongest MMM programs run a cadence of experiments and feed the results
back into the model as calibration points. In a Bayesian MMM this is natural:
the experimental estimate becomes an informative prior on the channel's effect,
with the prior's tightness reflecting the experiment's precision. The model then
balances the experimental evidence against the observational data.

When reviewing a model, a good validation recommendation is to identify the
channels with the widest credible intervals or the most surprising ROI estimates
and prioritize them for a lift test. Calibration is most valuable exactly where
the observational model is least certain.
