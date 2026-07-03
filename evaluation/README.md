# Evaluation Framework

The evaluation harness is the differentiating piece of Juno (design doc §5.4).
Its core logic lives in the backend package so it can reuse the agent, models,
and parsers directly:

- `backend/app/evaluation/benchmark_generator.py` — generate N ground-truth MMM
  scenarios via the BlueAlpha simulator.
- `backend/app/evaluation/judge.py` — LLM-as-judge (Opus grades Sonnet).
- `backend/app/evaluation/metrics.py` — Spearman accuracy, ECE calibration, etc.
- `backend/app/evaluation/failure_catalog.py` — SQLite-backed failure logging.
- `backend/app/evaluation/runner.py` — ties it together (offline / batch).

The `dashboard/` Streamlit app visualizes results.

## Layout of this directory

- `benchmarks/` — versioned benchmark sets (generated JSON, checked in or DVC'd).

## Running an eval (once the simulator is wired)

```bash
cd backend && . .venv/bin/activate
python -c "import asyncio; from app.evaluation import runner, benchmark_generator as bg; \
asyncio.run(runner.run_suite(bg.generate_cases(20)))"
```

Then launch the dashboard:

```bash
streamlit run dashboard/app.py
```
