"""Public offline CLI. No command starts a model or accesses the network."""

from __future__ import annotations

import argparse
import csv
from importlib import resources
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Callable, TextIO

from . import __version__
from .campaign import CampaignError, iter_ledger, load_campaign, plan_campaign
from .runtime import RuntimeProfileError, inspect_runtime

MAX_LEDGER_ROWS = 10_000_000
LEDGER_FIELDS = (
    "domain_id", "location_id", "reach_id", "issue_time_utc", "lead_hour", "valid_time_utc"
)


def _json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _publish_new(path: Path, writer: Callable[[TextIO], None]) -> None:
    """Publish a complete new file without clobbering an existing destination."""
    # A temporary file on the destination filesystem keeps publication atomic.
    # link() refuses an existing destination, including a dangling symlink.
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent,
        prefix=".ngen-reforecast-", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        try:
            writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _emit(text: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(text)
    else:
        _publish_new(output, lambda handle: handle.write(text))


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_plan_report(plan: dict) -> str:
    """Render planning evidence as Markdown, with explicit execution limits."""
    lines = [
        "# Reforecast campaign planning report", "",
        f"Campaign: `{_cell(plan['campaign_id'])}`  ",
        f"Plan identity: `{plan['plan_id']}`", "",
        "This report describes an offline plan. No forecast has been generated. "
        "Physical runtime qualification is pending; execution readiness is false.",
        "", "## Expected output", "", "| Quantity | Value |", "|---|---:|",
    ]
    for key, value in sorted(plan["totals"].items()):
        lines.append(f"| {_cell(key)} | {_cell(value)} |")
    lines.extend(["", "## Blockers", ""])
    for item in plan.get("blockers", []):
        lines.append(f"- **{_cell(item['code'])}**: {_cell(item['message'])}")
    if not plan.get("blockers"):
        lines.append("No input blocker recorded; this does not qualify physical execution.")
    lines.extend(["", "## Warnings", ""])
    for item in plan.get("warnings", []):
        if isinstance(item, dict):
            lines.append(f"- {_cell(item.get('code', 'WARNING'))}: {_cell(item.get('message', item))}")
        else:
            lines.append(f"- {_cell(item)}")
    if not plan.get("warnings"):
        lines.append("None recorded.")
    lines.extend([
        "", "## Evidence limits", "",
        "Expected counts are schedule arithmetic, not observed archive coverage. "
        "File hashes establish byte identity, not numerical validity, scientific suitability "
        "or redistribution rights. Missing measurements of runtime, memory, cost and "
        "forecast skill remain unknown. The issue ledger retains each forecast's issue "
        "and lead even when different issues share a valid time.", "",
    ])
    return "\n".join(lines)


def _init(directory: Path) -> int:
    template = resources.files("ngen_reforecast").joinpath("templates/campaign.json").read_text()
    guide = resources.files("ngen_reforecast").joinpath("templates/README.md").read_text()
    directory.mkdir(parents=True, exist_ok=False)
    _publish_new(directory / "campaign.json", lambda handle: handle.write(template))
    _publish_new(directory / "README.md", lambda handle: handle.write(guide))
    sys.stdout.write(_json({
        "status": "planning_template_created", "directory": str(directory),
        "inputs_included": False, "execution_ready": False,
        "next_step": "Bind your existing resident input assets, then run plan.",
    }))
    return 0


def _ledger(campaign: Path, output: Path, max_rows: int) -> int:
    if not 1 <= max_rows <= MAX_LEDGER_ROWS:
        raise ValueError(f"--max-rows must be between 1 and {MAX_LEDGER_ROWS}")
    spec = load_campaign(campaign)
    plan = plan_campaign(spec, campaign.parent, check_assets=False)
    expected = plan["totals"]["expected_forecast_rows"]
    if expected > max_rows:
        raise ValueError(f"Ledger has {expected} rows, exceeding --max-rows={max_rows}")

    def write(handle: TextIO) -> None:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_FIELDS, lineterminator="\n")
        writer.writeheader()
        count = 0
        for row in iter_ledger(spec):
            writer.writerow({key: row[key] for key in LEDGER_FIELDS})
            count += 1
            if count > max_rows:
                raise ValueError("Ledger generator exceeded the configured row cap")
        if count != expected:
            raise ValueError("Ledger row count differs from planned output count")

    _publish_new(output, write)
    sys.stdout.write(_json({
        "status": "expected_ledger_created", "rows": expected,
        "output": str(output), "forecasts_generated": 0,
        "plan_id": plan["plan_id"],
    }))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ngen-reforecast",
        description="Offline planning and historical runtime inspection; no model execution.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = p.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a planning template without scientific data")
    init.add_argument("directory", type=Path)
    for name in ("plan", "report"):
        sub = commands.add_parser(name, help=f"Write an offline campaign {name}")
        sub.add_argument("campaign", type=Path)
        sub.add_argument("--output", type=Path, help="New output file; existing files are never overwritten")
    ledger = commands.add_parser("ledger", help="Write expected issue/lead keys, not forecast values")
    ledger.add_argument("campaign", type=Path)
    ledger.add_argument("--output", type=Path, required=True)
    ledger.add_argument("--max-rows", type=int, default=1_000_000)
    doctor = commands.add_parser("doctor", help="Inspect a historical runtime profile without starting it")
    doctor.add_argument("profile", type=Path)
    doctor.add_argument("--asset-root", type=Path)
    doctor.add_argument("--output", type=Path)
    for name in ("run", "resume"):
        commands.add_parser(name, help="Unavailable until physical runtime and recovery are qualified")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            return _init(args.directory)
        if args.command in ("plan", "report"):
            spec = load_campaign(args.campaign)
            plan = plan_campaign(spec, args.campaign.parent, check_assets=True)
            _emit(_json(plan) if args.command == "plan" else render_plan_report(plan), args.output)
            return 2 if plan["blockers"] else 0
        if args.command == "ledger":
            return _ledger(args.campaign, args.output, args.max_rows)
        if args.command == "doctor":
            report = inspect_runtime(args.profile, args.asset_root)
            _emit(_json(report), args.output)
            return 2 if report["blockers"] else 0
        if args.command in ("run", "resume"):
            sys.stderr.write(_json({
                "error": "PHYSICAL_EXECUTION_NOT_IMPLEMENTED",
                "message": "Physical execution/recovery requires the qualified runtime and complete fixture described in IMPLEMENTATION_PLAN.md.",
            }))
            return 2
        raise ValueError("Unknown command")
    except (CampaignError, RuntimeProfileError, OSError, ValueError) as exc:
        sys.stderr.write(_json({"error": type(exc).__name__, "message": str(exc)}))
        return 1
