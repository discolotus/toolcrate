#!/usr/bin/env python3
"""Console-script wrappers for ToolCrate-managed external tools."""

import os
import sys

import click

from toolcrate.cli.binary_manager import find_executable, find_managed, managed_bin_dir


def exec_tool(command: str, display_name: str, allow_system: bool = True) -> None:
    """Replace the current process with a managed or system tool executable."""
    executable = find_executable(command) if allow_system else find_managed(command)
    if executable is None:
        click.echo(
            f"Error: {display_name} is not installed.\n"
            f"Run `toolcrate tools install` to install ToolCrate-managed tools.\n"
            f"Managed tools are installed under: {managed_bin_dir()}",
            err=True,
        )
        sys.exit(1)

    args = [command] + sys.argv[1:]
    os.execv(executable, args)


def run_slsk() -> None:
    """Run the Soulseek batch downloader."""
    exec_tool("sldl", "slsk-batchdl")


def run_shazam() -> None:
    """Run the Shazam recognition tool."""
    exec_tool("shazam-tool", "Shazam Tool", allow_system=False)


def run_mdl() -> None:
    """Run the music metadata utility."""
    exec_tool("mdl-tool", "mdl-tool", allow_system=False)
