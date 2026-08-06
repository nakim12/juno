---
title: Bayesian MMM and Priors
topic: bayesian_priors
source: juno_kb
credibility_tier: synthesis
---
Bayesian marketing mix models treat the unknown parameters — channel
coefficients, adstock decays, saturation shapes — as distributions rather than
single numbers. The model combines a prior (what we believe before seeing this
dataset) with the likelihood (what the data say) to produce a posterior
distribution for each parameter. The posterior is summarized by a point estimate
(often the mean or median) and a credible interval that expresses genuine
uncertainty.

Priors are the mechanism for injecting domain knowledge and experimental
evidence. A weakly informative prior might simply enforce that a channel's
effect is non-negative. A strongly informative prior, derived from a lift test,
might pin a channel's ROI near a measured value with a tightness reflecting the
experiment's precision. Priors regularize the model, which is especially
valuable when data are limited or channels are collinear — they keep estimates
from wandering to implausible values.

The Bayesian framing has two big advantages for interpretation. First,
uncertainty is first class: every estimate comes with a credible interval that
should drive how much confidence to place in it. Second, diagnostics from the
sampler (such as R-hat convergence statistics and divergence counts in
Hamiltonian Monte Carlo) tell you whether the posterior can be trusted at all. A
model with poor convergence should not be interpreted as if its numbers were
reliable.

When priors are strong, be aware that a channel's estimate partly reflects the
prior rather than the data. That is by design, but it should be stated when
explaining why a channel looks the way it does.
