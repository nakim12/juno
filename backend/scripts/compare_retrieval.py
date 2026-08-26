"""Compare lexical retrieval against the vector backend.

The demo host can't run the embedding model, so it runs BM25 with query
expansion instead. That's only an acceptable trade if the two agree on what to
cite, so this measures the agreement rather than assuming it.

    python -m scripts.compare_retrieval

Read the top-3 columns, not top-8. The corpus holds fourteen chunks, so
returning eight of them is more than half of everything there is and two
unrelated rankings would still overlap around 57% by chance. Agreement in the
top 3 — the citations actually surfaced in an answer — is the number that
carries information.

The held-out set matters for the same reason. The expansion table in
app/rag/lexical.py was written against the demo's own questions, so scoring it
only on those would measure memorization. The held-out queries were written
afterwards and never consulted while tuning.
"""

from __future__ import annotations

from app.rag import lexical
from app.rag.retriever import Retriever

# Questions the demo actually ships: the curated chat suggestions and the
# analysis retrieval query. Visible while building the expansion table.
DEV_QUERIES = [
    "what does saturation mean for my budget decisions",
    "how much should I trust the TikTok number",
    "where should I move budget next quarter",
    "what if I doubled Search spend",
    "why are the credible intervals so wide",
    "is the Social result reliable enough to act on",
    "which channel is actually delivering the best return",
    "should I cut Display",
    "is Affiliate really better than Search",
    "what is the headline read on this model",
    "MMM model with 6 channels, saturation detected, wide credible intervals",
]

# Written after the expansion table was fixed, and not used to tune it.
HELD_OUT_QUERIES = [
    "my agency says TV is driving everything, is that plausible",
    "the model says email has a 40x return, why is that suspicious",
    "how long after a campaign do the effects keep showing up",
    "two of my channels always run together, does that matter",
    "how do I know this model would hold up on next quarter's data",
    "the baseline is eating most of my sales, is that normal",
    "what would convince me these numbers are causal",
    "our Q4 numbers always look great, is that just Christmas",
    "how do I sanity check this against a geo experiment",
    "the estimate moved a lot when I added a channel",
    "what is the difference between average and marginal efficiency",
    "should I believe the prior or the data here",
]


def evaluate(name: str, queries: list[str], vector: Retriever) -> None:
    at3: list[float] = []
    at8: list[float] = []
    top1 = 0
    rows: list[tuple[str, float, float, bool]] = []

    for query in queries:
        v = [c.chunk_id for c in vector.retrieve(query, top_k=8)]
        lx = [c.chunk_id for c in lexical.retrieve(query, 8)]
        if not v:
            print(f"! vector returned nothing for {query!r} — is the index built?")
            continue

        o3 = len(set(v[:3]) & set(lx[:3])) / min(3, len(v))
        o8 = len(set(v) & set(lx)) / len(v)
        hit = v[0] == lx[0]
        at3.append(o3)
        at8.append(o8)
        top1 += hit
        rows.append((query, o3, o8, hit))

    if not rows:
        return

    width = min(max(len(q) for q, *_ in rows), 62)
    print(f"\n### {name}  (n={len(rows)})")
    print(f"{'query'[:width].ljust(width)}  top3   top8  top-1")
    print("-" * (width + 21))
    for query, o3, o8, hit in rows:
        print(f"{query[:width].ljust(width)}  {o3:>4.0%}  {o8:>5.0%}  {'yes' if hit else '-'}")
    print("-" * (width + 21))
    print(
        f"{'mean'.ljust(width)}  {sum(at3) / len(at3):>4.0%}  "
        f"{sum(at8) / len(at8):>5.0%}  {top1}/{len(rows)}"
    )


def main() -> None:
    vector = Retriever()
    vector._backend = "vector"  # force, whatever this machine's cgroup says

    evaluate("dev (expansions tuned against these)", DEV_QUERIES, vector)
    evaluate("held out (never used for tuning)", HELD_OUT_QUERIES, vector)

    # Chance baseline, for scale: two unrelated rankings over a corpus this
    # small still overlap substantially.
    n = lexical.build().size
    print(f"\ncorpus chunks: {n}")
    print(f"chance overlap: top3 ~{3 / n:.0%}, top8 ~{8 / n:.0%}")


if __name__ == "__main__":
    main()
