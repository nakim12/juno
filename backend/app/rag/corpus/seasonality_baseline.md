---
title: Seasonality, Trend, and Baseline
topic: seasonality
source: juno_kb
credibility_tier: synthesis
---
Only part of a brand's sales is driven by media. The rest is the baseline: the
demand that would exist with no advertising, shaped by trend, seasonality,
price, distribution, and macro conditions. A marketing mix model must separate
this baseline from media effects, because any baseline demand that is
mistakenly attributed to advertising inflates channel ROI.

Seasonality is the most common confounder. Many businesses spend more during
their high-demand seasons, so spend and sales rise together for reasons that
have nothing to do with advertising effectiveness. If the model does not include
strong seasonal controls, it will credit that seasonal lift to whatever channels
happened to be active, overstating their impact. Good models include explicit
seasonal terms (for example Fourier components or holiday indicators) and a
trend component to absorb slow-moving shifts in underlying demand.

The length and richness of the data matter here. Estimating annual seasonality
reliably requires at least two full years; shorter windows make it hard to
distinguish a seasonal pattern from a media effect. A model built on 26 weeks of
data cannot confidently separate a seasonal peak from advertising-driven lift,
and its channel estimates should be treated cautiously.

When interpreting a model, note the data span and whether seasonality is
plausibly controlled. If a channel's high ROI coincides with the brand's peak
season, raise the possibility that some of that effect is really unmodeled
seasonal demand.
