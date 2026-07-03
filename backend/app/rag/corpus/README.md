# Knowledge Base Corpus

Drop curated MMM methodology documents here as `.md` or `.txt` files, then build
the index:

```bash
python -m app.rag.indexer --reset
```

Target 30-50 high-quality documents (design doc 5.3, Appendix A). Suggested
sources: Google's MMM papers, Recast blog (Vladeck / Kaminsky), Meta Robyn docs,
Google Meridian docs, and select academic papers on causal inference for
advertising.

Each file is chunked to ~500 tokens with `source`, `topic`, and
`credibility_tier` metadata. Refine the metadata tagging in `indexer.py` as the
corpus matures.
