"""Command Line Interface for ai-ops-eval-harness."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from ai_ops_eval_harness import __version__
from ai_ops_eval_harness.assertions import assert_decoupled_json_contract
from ai_ops_eval_harness.auditor import assert_no_coercion_starvation, reconcile_channel_ledgers
from ai_ops_eval_harness.exceptions import (
    DataStarvationError,
    FinancialAnomalyError,
)
from ai_ops_eval_harness.scenarios import BlastShield, QAScenario, ScenarioHarness


def _cmd_eval(args: argparse.Namespace) -> int:
    """Run evaluation scenarios and print structured results."""
    harness = ScenarioHarness(name=args.suite_name)

    # Register default clean-room sanity scenarios
    def _sample_json_pipeline() -> dict[str, str]:
        with BlastShield(simulate_success=True) as shield:
            shield.record_dispatch("+1234567890", {"status": "ok"})
            return {"status": "success", "text": "pipeline healthy"}

    harness.register(
        QAScenario(
            name="system_contract_eval",
            description="Sanity check for prompt contract & blast shield isolation",
            runner=_sample_json_pipeline,
            assertions=[assert_decoupled_json_contract],
        )
    )

    report = harness.run_all()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"=== Evaluation Harness: {report['harness']} ===")
        print(f"Total Scenarios : {report['total_scenarios']}")
        print(f"Passed          : {report['passed']}")
        print(f"Failed          : {report['failed']}")
        for res in report["results"]:
            icon = "✅" if res["passed"] else "❌"
            print(f"  {icon} {res['name']} ({res['duration_seconds']:.4f}s)")
            if not res["passed"]:
                print(f"     Error: {res['error']}")

    return 0 if report["failed"] == 0 else 1


def _cmd_reconcile(args: argparse.Namespace) -> int:
    """Reconcile multi-channel ledgers with float precision tolerance."""
    try:
        res = reconcile_channel_ledgers(
            primary_gross=args.primary_gross,
            secondary_gross=args.secondary_gross,
            secondary_net=args.secondary_net,
            secondary_tax=args.secondary_tax,
            secondary_fee=args.secondary_fee,
            platform_estimate=args.platform_estimate,
            abs_tol=args.abs_tol,
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print("=== Reconciliation Succeeded ===")
            print(f"Consolidated Gross: {res['consolidated_gross']:.2f}")
            print(f"Primary Gross     : {res['primary_gross']:.2f}")
            print(f"Secondary Gross   : {res['secondary_gross']:.2f}")
            print(f"Secondary Net     : {res['secondary_net']:.2f}")
            print(f"Gross Variance    : {res['variance_gross']:.4f}")
            print(f"Net Variance      : {res['variance_net']:.4f}")
            print(f"Hidden Variance   : {res['hidden_variance']:.4f}")
        return 0
    except FinancialAnomalyError as e:
        print(f"FINANCIAL ANOMALY ERROR: {e}", file=sys.stderr)
        return 2


def _cmd_starvation_check(args: argparse.Namespace) -> int:
    """Verify record coercion count does not exceed starvation threshold."""
    try:
        assert_no_coercion_starvation(
            initial_count=args.initial,
            final_count=args.final,
            tolerance_pct=args.tolerance_pct,
        )
        print(f"STARVATION CHECK PASSED: initial={args.initial}, final={args.final}")
        return 0
    except DataStarvationError as e:
        print(f"DATA STARVATION ERROR: {e}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="ai-ops-eval",
        description="SRE-hardened evaluation harness and operational pipeline auditor.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # eval subcommand
    eval_parser = subparsers.add_parser("eval", help="Execute evaluation scenario harness")
    eval_parser.add_argument(
        "--suite-name",
        default="cli_evaluation_suite",
        help="Name of evaluation suite",
    )
    eval_parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON report",
    )

    # reconcile subcommand
    rec_parser = subparsers.add_parser(
        "reconcile",
        help="Reconcile primary and secondary channel ledgers",
    )
    rec_parser.add_argument("--primary-gross", type=float, required=True, help="Primary channel gross")
    rec_parser.add_argument("--secondary-gross", type=float, required=True, help="Secondary channel gross")
    rec_parser.add_argument("--secondary-net", type=float, required=True, help="Secondary channel net")
    rec_parser.add_argument("--secondary-tax", type=float, required=True, help="Secondary channel tax")
    rec_parser.add_argument("--secondary-fee", type=float, required=True, help="Secondary channel fee")
    rec_parser.add_argument(
        "--platform-estimate",
        type=float,
        default=None,
        help="Optional external platform net estimate",
    )
    rec_parser.add_argument(
        "--abs-tol",
        type=float,
        default=0.01,
        help="Absolute tolerance for IEEE 754 precision reconciliation",
    )
    rec_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    # starvation-check subcommand
    starv_parser = subparsers.add_parser(
        "starvation-check",
        help="Audit dataset coercion loss",
    )
    starv_parser.add_argument("--initial", type=int, required=True, help="Initial record count")
    starv_parser.add_argument("--final", type=int, required=True, help="Final coerced record count")
    starv_parser.add_argument(
        "--tolerance-pct",
        type=float,
        default=5.0,
        help="Maximum allowable drop percentage (default: 5.0)",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "eval":
        return _cmd_eval(args)
    if args.command == "reconcile":
        return _cmd_reconcile(args)
    if args.command == "starvation-check":
        return _cmd_starvation_check(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
