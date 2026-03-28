"""SDD CLI — project initialization and management."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Entry point for `sdd` CLI."""
    parser = argparse.ArgumentParser(
        prog="sdd",
        description="SDD (Spec-Driven Development) Orchestrator CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # sdd init
    init_parser = sub.add_parser("init", help="Initialize SDD in current project")
    init_parser.add_argument(
        "--preset",
        default="default",
        help="Project preset (default: default)",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )

    args = parser.parse_args()

    if args.command == "init":
        from sdd_orchestrator.cli.init import run_init

        sys.exit(run_init(preset=args.preset, force=args.force))
    else:
        parser.print_help()
        sys.exit(1)
