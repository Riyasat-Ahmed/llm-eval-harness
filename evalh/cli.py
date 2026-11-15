from __future__ import annotations

import asyncio
import subprocess
import uuid
from datetime import UTC, datetime

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from evalh import store
from evalh.config import load_configs
from evalh.dataset import dataset_hash, load_dataset
from evalh.reporting import summarize
from evalh.runner import DEFAULT_CONCURRENCY, run_all

load_dotenv()

app = typer.Typer(
    add_completion=False,
    help="LLM Eval Harness: compare LLM configs on a labelled dataset.",
)
console = Console()


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


@app.command()
def run(
    task: str = typer.Option(..., "--task", help="Task name, e.g. 'tickets' (tasks/<task>/)."),
    configs: str = typer.Option("*.yaml", "--configs", help="Glob for config files to run."),
    concurrency: int = typer.Option(DEFAULT_CONCURRENCY, "--concurrency"),
) -> None:
    """Run every config in tasks/<task>/configs/ against the dataset, cache, score, store."""
    examples = load_dataset(task)
    specs = load_configs(task, pattern=configs)
    dhash = dataset_hash(task)
    run_id = uuid.uuid4().hex[:12]

    console.print(
        f"[bold]evalh run[/] task={task} configs={[s.name for s in specs]} "
        f"examples={len(examples)} run_id={run_id}"
    )

    conn = store.connect()
    store.start_run(
        conn,
        run_id=run_id,
        task=task,
        dataset_hash=dhash,
        git_commit=_git_commit(),
        started_at=datetime.now(UTC).isoformat(),
    )

    total_calls = len(specs) * len(examples)
    done = 0

    def _progress(_row) -> None:
        nonlocal done
        done += 1
        if done % 25 == 0 or done == total_calls:
            console.print(f"  {done}/{total_calls} calls complete")

    results = asyncio.run(
        run_all(
            conn=conn,
            run_id=run_id,
            task=task,
            configs=specs,
            examples=examples,
            concurrency=concurrency,
            on_result=_progress,
        )
    )
    console.print(f"[green]Done.[/] {len(results)} results stored under run_id={run_id}")
    _print_summary(run_id, task)


@app.command()
def report(
    task: str = typer.Option(..., "--task"),
    run_id: str | None = typer.Option(None, "--run-id", help="Defaults to the latest run."),
) -> None:
    """Print the summary table for a previous run."""
    _print_summary(run_id, task)


def _print_summary(run_id: str | None, task: str) -> None:
    conn = store.connect()
    rid = run_id or store.latest_run_id(conn, task)
    if rid is None:
        console.print(f"[red]No runs found for task {task!r}.[/]")
        raise typer.Exit(1)

    rows = store.fetch_results(conn, rid)
    if not rows:
        console.print(f"[red]Run {rid!r} has no results.[/]")
        raise typer.Exit(1)

    table = Table(title=f"Results: task={task} run_id={rid}")
    columns = [
        "Config", "N", "Accuracy", "Parse fails", "$/1000 calls", "Median ms", "p95 ms", "Total $",
    ]
    for col in columns:
        table.add_column(col, justify="right" if col != "Config" else "left")

    for s in summarize(rows):
        table.add_row(
            s.config_name,
            str(s.n),
            f"{s.accuracy:.1%}",
            str(s.parse_failures),
            f"${s.cost_per_1000:.4f}",
            f"{s.median_latency_ms:.0f}",
            f"{s.p95_latency_ms:.0f}",
            f"${s.total_cost_usd:.4f}",
        )
    console.print(table)


@app.command()
def failures(
    task: str = typer.Option(..., "--task"),
    config: str = typer.Option(..., "--config", help="Config name to filter to."),
    run_id: str | None = typer.Option(None, "--run-id"),
) -> None:
    """List every example a config got wrong: input, expected label, model output."""
    conn = store.connect()
    rid = run_id or store.latest_run_id(conn, task)
    if rid is None:
        console.print(f"[red]No runs found for task {task!r}.[/]")
        raise typer.Exit(1)

    examples_by_id = {e.id: e for e in load_dataset(task)}
    all_rows = store.fetch_results(conn, rid)
    rows = [r for r in all_rows if r["config_name"] == config and not r["correct"]]

    if not rows:
        console.print(f"[green]No failures for {config!r} in run {rid!r}.[/]")
        return

    for r in rows:
        example = examples_by_id.get(r["example_id"])
        console.print(f"[bold]{r['example_id']}[/]")
        console.print(f"  input:    {example.input if example else '?'}")
        console.print(f"  expected: {example.expected if example else '?'}")
        got = r["output_parsed"] or "(unparseable)"
        console.print(f"  got:      {got}  raw={r['output_raw']!r}")
        if r["error"]:
            console.print(f"  error:    {r['error']}")
        console.print()


if __name__ == "__main__":
    app()
