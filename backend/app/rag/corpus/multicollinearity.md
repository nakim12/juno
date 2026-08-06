---
title: Multicollinearity and Correlated Channels
topic: multicollinearity
source: juno_kb
credibility_tier: synthesis
---
Multicollinearity arises when two or more media channels have spend patterns
that move together over time. If Meta and Instagram are always flighted in
lockstep, or if all upper-funnel channels ramp together for a seasonal push, the
model cannot cleanly separate their individual contributions. The regression can
fit the combined effect well while distributing credit between the correlated
channels almost arbitrarily.

The tell-tale symptoms are wide credible intervals on the correlated channels,
unstable coefficients that swing when the model is refit, and sometimes a
negative coefficient on one channel that is compensated by an inflated
coefficient on another. Point estimates for individual channels become
unreliable even when the aggregate prediction is accurate.

There are several mitigations. Channels that are conceptually similar and always
co-move can be grouped into a single modeled variable. Deliberate variation
helps enormously: staggering flight timing or running geo experiments where one
channel is perturbed independently gives the model the independent signal it
needs. Informative priors from experiments also stabilize the estimates.

When reviewing a model, look for pairs of channels with correlated spend and
overlapping wide intervals, and flag them explicitly. A recommendation to shift
budget between two collinear channels should carry low confidence, because the
model genuinely cannot tell which of them is doing the work.
