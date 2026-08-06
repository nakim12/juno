---
title: MMM versus Multi-Touch Attribution
topic: attribution
source: juno_kb
credibility_tier: synthesis
---
Marketing mix modeling (MMM) and multi-touch attribution (MTA) answer related
but different questions and rest on different data. MMM works top-down on
aggregate time-series data — weekly spend and outcomes across channels — and
estimates the incremental contribution of each channel while controlling for
seasonality, pricing, and other drivers. MTA works bottom-up on user-level event
data, assigning credit across the touchpoints in an individual's path to
conversion.

Their strengths are complementary. MMM captures the effects of channels that
have no user-level tracking (television, out-of-home, and increasingly
privacy-restricted digital channels), naturally accounts for saturation and
carryover, and measures long-term and offline effects. But it is coarse in time,
data-hungry, and cannot say much about creative or audience-level decisions. MTA
is granular and fast but is undermined by cookie loss, cross-device gaps, and
the fact that last-touch and even data-driven attribution conflate correlation
with incrementality.

Neither is a substitute for experiments. Both MMM and MTA should be calibrated
against incrementality tests, which measure causal lift directly. A mature
measurement stack triangulates: MMM for strategic budget allocation across
channels, experiments for ground-truth calibration, and MTA or platform metrics
for tactical, in-flight optimization.

When a stakeholder asks why MMM disagrees with a platform's reported ROAS, the
answer usually involves incrementality: platform-reported conversions include
demand that would have occurred anyway, whereas MMM tries to isolate the
incremental portion.
