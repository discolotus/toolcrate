#!/usr/bin/env python3
"""Main CLI entry point for ToolCrate."""

import click
from loguru import logger


@click.group()
@click.version_option()
def main():
    """ToolCrate - A unified tool suite for music management and processing."""
    pass


@main.command()
def info():
    """Show information about available tools."""
    click.echo("ToolCrate - Available Tools:")
    click.echo("  - slsk-tool: Soulseek batch download tool")
    click.echo("  - shazam-tool: Music recognition tool")
    click.echo("  - mdl-tool: Music metadata utility")


if __name__ == "__main__":
    main()
