"""
reporter.py — Terminal table display and JSON report generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich import box


def print_summary_table(stack: dict[str, Any]) -> None:
    """Print a nicely formatted summary table to the terminal using Rich."""
    console = Console()

    console.rule(f"[bold cyan]Tech Stack Analysis: {stack.get('repo_name', 'Unknown')}")
    console.print()

    # Repo meta
    meta = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    meta.add_column("Key", style="bold green", no_wrap=True)
    meta.add_column("Value", style="white")
    meta.add_row("Repository", stack.get("repo_url", ""))
    meta.add_row("Description", stack.get("description", "(none)") or "(none)")
    meta.add_row("Stars", f"{stack.get('stars', 0):,}")
    meta.add_row("Forks", f"{stack.get('forks', 0):,}")
    meta.add_row("Default Branch", stack.get("default_branch", ""))
    console.print(meta)

    # Main analysis table
    table = Table(
        title="Detected Components",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        padding=(0, 1),
    )
    table.add_column("Category", style="bold yellow", no_wrap=True, min_width=22)
    table.add_column("Detected", style="white")

    languages = stack.get("languages", {})
    if languages:
        lang_str = ", ".join(
            f"{lang} ({bytes_:,} B)" if isinstance(bytes_, int) else lang
            for lang, bytes_ in list(languages.items())[:8]
        )
    else:
        lang_str = "(none)"

    rows = [
        ("Languages", lang_str),
        ("Frameworks", ", ".join(stack.get("frameworks", [])) or "(none)"),
        ("Package Managers", ", ".join(stack.get("package_managers", [])) or "(none)"),
        ("Databases / Storage", ", ".join(stack.get("databases", [])) or "(none)"),
        ("Auth / Security", ", ".join(stack.get("auth", [])) or "(none)"),
        ("Messaging / Async", ", ".join(stack.get("messaging", [])) or "(none)"),
        ("CI/CD", ", ".join(stack.get("cicd", [])) or "(none)"),
        ("Containers / K8s", ", ".join(stack.get("containers", [])) or "(none)"),
        ("IaC", ", ".join(stack.get("iac", [])) or "(none)"),
        ("Cloud Providers", ", ".join(stack.get("cloud", [])) or "(none)"),
        ("Infra / HA", ", ".join(stack.get("infra", [])) or "(none)"),
    ]

    for category, value in rows:
        table.add_row(category, value)

    console.print(table)


def save_json_report(stack: dict[str, Any], output_path: str | Path) -> str:
    """Write the stack detection result to a JSON file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Convert sets to sorted lists for JSON serialisation
    serialisable = _make_serialisable(stack)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(serialisable, f, indent=2, ensure_ascii=False)

    print(f"  [REPORT] stack_report.json → {out}")
    return str(out)


def _make_serialisable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _make_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (set, frozenset)):
        return sorted(_make_serialisable(v) for v in obj)
    if isinstance(obj, (list, tuple)):
        return [_make_serialisable(v) for v in obj]
    return obj
