---
title: Adstock and Carryover Effects
topic: adstock
source: juno_kb
credibility_tier: synthesis
---
Adstock (also called carryover) captures the idea that advertising exposure has
an effect that persists beyond the week the money is spent. Someone who sees an
ad today may not convert until two or three weeks later. Marketing mix models
represent this with a decay parameter, usually between 0 and 1, applied
geometrically: the effect in the current week is the fresh spend plus a decayed
fraction of the prior week's accumulated effect.

A decay of 0 means the channel has no memory — its impact is fully realized in
the week of spend. A decay of 0.9 means 90% of last week's effect carries into
this week, so the influence of a single flight of spend stretches across many
weeks. Higher decay implies longer-lived effects, which is common for
brand-oriented channels like television or video, while lower decay is typical
of direct-response channels like paid search.

Two cautions matter when interpreting adstock. First, high decay values are hard
to identify from limited data: if effects smear across many weeks, the model has
less independent variation to learn from, and the estimate becomes uncertain.
Second, adstock interacts with saturation. The model typically applies adstock
first (to build the carried-over exposure) and then a saturation transform (to
capture diminishing returns), so the two parameters must be read together, not
in isolation. A channel with high adstock and strong saturation behaves very
differently from one with low adstock and a near-linear response.

When an adstock estimate is near the upper bound (say above 0.9), treat it
skeptically and check whether the data span is long enough to support it. Flag
it as a structural risk rather than a confident finding.
