---
title: Geo Experiments and Incrementality Tests
topic: lift_tests
source: juno_kb
credibility_tier: synthesis
---
Incrementality tests measure the causal lift of advertising by creating a
controlled contrast between exposed and unexposed groups. The most common design
in a marketing context is a geo experiment: a set of matched geographic regions
is randomly assigned to treatment (media on, or media increased) and control
(media held out, or held flat), and the difference in outcomes is the estimated
incremental effect. Because assignment is randomized, the contrast is causal and
not merely correlational.

Conversion lift studies do the same at the user or audience level, typically run
through an ad platform, holding out a randomized control audience from seeing a
campaign. Both designs share the same logic: deliberately break the link between
spend and the demand that would have happened anyway, so the measured difference
reflects true incrementality rather than pre-existing intent.

The value of experiments to a marketing mix model is calibration. An experiment
produces a causal estimate for one channel over one window; that estimate anchors
the corresponding coefficient in the model, correcting biases from confounding
and collinearity that observational data alone cannot resolve. Experiments are
expensive and slow, so they should be aimed where they add the most information:
high-spend channels, channels with wide credible intervals, and channels whose
modeled ROI is surprising.

When recommending validation, a geo lift test on the highest-impact or
least-certain channel is usually the single most valuable next step, because it
converts an uncertain observational estimate into a trusted causal one.
