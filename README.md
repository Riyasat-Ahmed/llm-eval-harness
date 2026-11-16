# LLM Eval Harness

Run a labelled test set through several LLM configurations and see which one
gives the best accuracy for the cost and latency — one command, reproducible,
with every failure inspectable.

## The problem

Teams pick models and prompts by trying a few examples by hand. That misses
regressions, hides cost differences of 10x or more, and gives no evidence
when someone asks "why this model?" This harness replaces hand-testing with a
repeatable pipeline: a versioned dataset, a runner that calls every config,
scorers that grade every output, and a dashboard that compares results side
by side.

## Results

Real run on the 100-ticket dataset (2026-11-16). OpenAI configs aren't run
yet (no key configured on this machine) — Anthropic and local Ollama are:

| Config | Accuracy | $ / 1,000 calls | Median latency | p95 latency |
|---|---|---|---|---|
| `anthropic_large_baseline` (Opus) | 92.0% | $0.7104 | 706ms | 1335ms |
| `anthropic_small_baseline` (Haiku) | 91.0% | $0.1098 | 422ms | 628ms |
| `anthropic_small_fewshot` (Haiku + few-shot) | **93.0%** | $0.5800 | 461ms | 581ms |
| `local_ollama` (llama3.1 8B, $0) | 88.0% | $0.0000 | 504ms | 631ms |
| `local_ollama_small` (llama3.2 1B, $0) | 47.0% | $0.0000 | 107ms | 132ms |

**Key finding:** the cheap model with a better prompt beats the expensive
model with a basic one — `anthropic_small_fewshot` hits 93.0% accuracy,
*higher* than the much pricier Opus baseline (92.0%), while costing about
18% less per call. Prompt quality mattered more than model size here.

![dashboard screenshot](docs/dashboard-screenshot.png)

## Quickstart

```bash
git clone <this-repo>
cd "LLM Comparison"
uv sync --extra dev

cp .env.example .env
# edit .env and add OPENAI_API_KEY and/or ANTHROPIC_API_KEY
# (only configs for providers whose key is set will succeed)

uv run evalh run --task tickets      # ~100 examples x 6 configs, < $2, < 10 min uncached
uv run evalh report --task tickets   # re-prints the summary table for the latest run
uv run evalh failures --task tickets --config small_baseline
```

Re-running `evalh run` reuses the cache (keyed on config + example) and costs
$0 and takes under 10 seconds, as long as the dataset and configs haven't
changed.

**Each `evalh run` invocation gets its own `run_id`, and the dashboard's
comparison table only shows configs from one `run_id` at a time.** To compare
N configs side by side, run them all in a single command — pass a glob that
matches all of them (e.g. `--configs "*.yaml"` or `--configs "local_ollama*.yaml"`)
rather than invoking `evalh run` once per config. Since results are cached
per `(config, example)` regardless of run_id, re-running configs you've
already evaluated together costs nothing.

## Dashboard

```bash
uv run streamlit run dashboard/app.py
```

Opens a comparison table, a cost-vs-accuracy scatter plot, and a failure
browser filterable by config and expected category. The dashboard only reads
from the local `results.db` SQLite file — it never calls a model API, so it's
safe to host publicly (e.g. Streamlit Community Cloud) without exposing keys.

## The launch task

Support-ticket classification into 6 categories: Billing, Technical issue,
Account access, Shipping, Refund, Other. 100 examples, at least 15 per
category, with written [labelling guidelines](tasks/tickets/labeling_guidelines.md).
The tickets were LLM-drafted (varied tone and length) and reviewed against
those guidelines before being committed — they are not real customer data.
A few are deliberately ambiguous so the task doesn't trivially hit 95%+
accuracy for every config (see the PRD's risk section).

## Configurations at launch

| Config | Provider / model | Prompt |
|---|---|---|
| `large_baseline` | OpenAI `gpt-5` | baseline |
| `small_baseline` | OpenAI `gpt-5-mini` | baseline |
| `small_fewshot` | OpenAI `gpt-5-mini` | few-shot + label definitions |
| `anthropic_large_baseline` | Anthropic `claude-opus-5` | baseline |
| `anthropic_small_baseline` | Anthropic `claude-haiku-4-5-20251001` | baseline |
| `anthropic_small_fewshot` | Anthropic `claude-haiku-4-5-20251001` | few-shot + label definitions |
| `local_ollama`, `local_ollama_small` (optional) | Ollama `llama3.1`, `llama3.2:1b` | baseline |

All six cloud configs run by default (`evalh run --task tickets`); you only
need an API key for the provider(s) you actually want to run — a config
whose key is missing fails every call but doesn't stop the others (see
Reliability below). Prices live in one file, [`prices.yaml`](prices.yaml),
checked against each provider's official pricing docs on **2026-11-15** —
verify before trusting cost figures for a real decision, since prices change
without notice. The optional Ollama configs cost $0 but need a local server
running with the model pulled (`ollama pull llama3.1`); they aren't
auto-discovered by the default config glob, see
[`tasks/tickets/configs/optional/`](tasks/tickets/configs/optional/) for how
to include them.

## Adding a task or a config

- **New config:** drop a YAML file into `tasks/<task>/configs/` with
  `provider`, `model`, `prompt_file`, `temperature`, `max_tokens` — no code
  changes.
- **New task:** add `tasks/<new_task>/data.jsonl` (rows of `id`, `input`,
  `expected`, optional `notes`), at least one prompt file, and a
  `configs/` directory. If it's a classification task, the same
  parser/scorer apply as long as the prompt instructs the model to answer
  with one of the known labels — only the category list in
  `evalh/scoring/parser.py` needs updating per task today (see Roadmap).

## Architecture

A straight pipeline, each stage its own module so a new task, provider or
scorer slots in without touching the rest:

```
evalh/
  cli.py            typer commands: run, report, failures
  runner.py         asyncio + semaphore + tenacity retries, cache-aware
  store.py          SQLite: runs / configs / results / cache tables
  pricing.py        cost_usd() from prices.yaml
  reporting.py      accuracy / cost-per-1000 / median+p95 latency per config
  dataset.py        loads + validates tasks/<task>/data.jsonl, hashes it
  config.py         loads tasks/<task>/configs/*.yaml, hashes each config
  models.py         pydantic types shared across the pipeline
  providers/        openai.py, anthropic.py, ollama.py -- one shape out
  scoring/          parser.py (label extraction), scorers.py (exact-match)
tasks/tickets/      the launch task: data, prompts, configs, guidelines
dashboard/app.py    Streamlit + Plotly, reads SQLite only
prices.yaml
tests/
```

**Reproducibility:** every run records the dataset hash, each config's hash
(model + params + prompt text), the git commit, and a timestamp. Temperature
defaults to 0 for OpenAI and Ollama configs — the Anthropic Messages API no
longer accepts a `temperature` parameter at all, so Anthropic configs are
only as reproducible as Anthropic's own (undocumented) sampling defaults.
Responses are cached on `(config_hash, example_id)`, so a re-run with the
same dataset and config is free and returns the same result regardless.

**Reliability:** provider calls retry up to 3 times with exponential backoff;
a call that still fails is recorded as an error row (counted as wrong) rather
than stopping the run.

## Development

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check .
```

CI (`.github/workflows/ci.yml`) runs both on every push/PR to `main`. Tests
cover the parser, scorer, dataset/config loaders, pricing and the runner
(against a fake provider — no real API calls run in CI).

## Roadmap (not yet built)

Per-class accuracy and confusion matrix, run-to-run diff (which examples
flipped right/wrong), a CI mode that fails below an accuracy threshold,
bootstrap confidence intervals, and a field-level/LLM-as-judge scorer for
non-classification tasks. See the PRD for the full P1/P2 list.

## Non-goals (v1)

Not a general-purpose eval platform, no user accounts/auth, no fine-tuning,
no multi-turn/agent evals, no real-time production monitoring.
