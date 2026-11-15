"""Streamlit dashboard for the LLM Eval Harness.

Reads stored results only -- never calls a model API (see PRD NFR: Security).
Run with: uv run streamlit run dashboard/app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from evalh import store
from evalh.dataset import load_dataset
from evalh.reporting import summarize

st.set_page_config(page_title="LLM Eval Harness", layout="wide")

TASKS = ["tickets"]  # add more task names here as tasks/<task>/ is added


@st.cache_resource
def get_conn():
    return store.connect()


def list_runs(conn, task: str) -> list[str]:
    cur = conn.execute(
        "SELECT run_id FROM runs WHERE task = ? ORDER BY started_at DESC", (task,)
    )
    return [r[0] for r in cur.fetchall()]


st.title("LLM Eval Harness")
st.caption(
    "Compares LLM configurations on the same labelled dataset for accuracy, "
    "cost per 1,000 calls and latency. Reads stored results only."
)

conn = get_conn()

col_task, col_run = st.columns([1, 2])
with col_task:
    task = st.selectbox("Task", TASKS)

runs = list_runs(conn, task)
if not runs:
    st.warning(
        f"No runs found for task {task!r} yet. Run `evalh run --task {task}` first."
    )
    st.stop()

with col_run:
    run_id = st.selectbox("Run", runs, index=0)

rows = store.fetch_results(conn, run_id)
summaries = summarize(rows)
df = pd.DataFrame([s.model_dump() for s in summaries])

st.subheader("Comparison")
display_df = df.rename(
    columns={
        "config_name": "Config",
        "n": "N",
        "accuracy": "Accuracy",
        "parse_failures": "Parse failures",
        "cost_per_1000": "$ / 1000 calls",
        "median_latency_ms": "Median latency (ms)",
        "p95_latency_ms": "p95 latency (ms)",
        "total_cost_usd": "Total cost ($)",
    }
)
st.dataframe(
    display_df.style.format(
        {
            "Accuracy": "{:.1%}",
            "$ / 1000 calls": "${:.4f}",
            "Median latency (ms)": "{:.0f}",
            "p95 latency (ms)": "{:.0f}",
            "Total cost ($)": "${:.4f}",
        }
    ),
    hide_index=True,
    width="stretch",
)

st.subheader("Cost vs. accuracy")
fig = px.scatter(
    df,
    x="cost_per_1000",
    y="accuracy",
    color="config_name",
    size="n",
    hover_data=["median_latency_ms", "p95_latency_ms", "parse_failures"],
    labels={
        "cost_per_1000": "Cost per 1,000 calls ($)",
        "accuracy": "Accuracy",
        "config_name": "Config",
    },
)
fig.update_yaxes(tickformat=".0%")
fig.update_traces(marker=dict(sizemin=10))
st.plotly_chart(fig, width="stretch")

st.subheader("Failure browser")
examples_by_id = {e.id: e for e in load_dataset(task)}
config_names = sorted({r["config_name"] for r in rows})

col_cfg, col_cat = st.columns(2)
with col_cfg:
    selected_configs = st.multiselect("Config", config_names, default=config_names)
with col_cat:
    all_categories = sorted({e.expected for e in examples_by_id.values()})
    selected_categories = st.multiselect(
        "Expected category", all_categories, default=all_categories
    )

failure_rows = [
    r
    for r in rows
    if not r["correct"]
    and r["config_name"] in selected_configs
    and examples_by_id.get(r["example_id"])
    and examples_by_id[r["example_id"]].expected in selected_categories
]

if not failure_rows:
    st.success("No failures match the current filters.")
else:
    table = []
    for r in failure_rows:
        example = examples_by_id[r["example_id"]]
        table.append(
            {
                "Config": r["config_name"],
                "Example": r["example_id"],
                "Input": example.input,
                "Expected": example.expected,
                "Model output": r["output_parsed"] or "(unparseable)",
                "Raw output": r["output_raw"] or "",
                "Error": r["error"] or "",
            }
        )
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
    st.caption(f"{len(failure_rows)} failing examples match the current filters.")
