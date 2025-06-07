#!/usr/bin/env python3
"""Main CLI entry point for ToolCrate."""

import click

from .wrappers import run_sldl_docker_command
from .schedule import schedule


@click.group()
@click.version_option()
@click.option('--build', is_flag=True, help='Rebuild docker containers before running commands')
@click.pass_context
def main(ctx, build):
    """ToolCrate - A unified tool suite for music management and processing."""
    # Store the build flag in the context for subcommands to access
    ctx.ensure_object(dict)
    ctx.obj['build'] = build


@main.command()
def info():
    """Show information about available tools."""
    click.echo("ToolCrate - Available Tools:")
    click.echo("  - slsk-tool: Soulseek batch download tool")
    click.echo("  - shazam-tool: Music recognition tool")
    click.echo("  - mdl-tool: Music metadata utility")
    click.echo("  - sldl: Run commands in slsk-batchdl docker container")
    click.echo("  - schedule: Manage scheduled downloads and cron jobs")
    click.echo("    • toolcrate schedule daily/hourly/weekly - Easy scheduling")


@main.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.pass_context
def sldl(ctx):
    """Run commands in the slsk-batchdl docker container.

    When called without arguments, enters an interactive shell in the container.
    When called with arguments, executes the slsk-batchdl command with those arguments.
    The config file path (-c /config/sldl.conf) is automatically included.

    Examples:
        toolcrate sldl                           # Enter interactive shell
        toolcrate --build sldl                   # Rebuild container and enter shell
        toolcrate sldl --help                    # Show slsk-batchdl help
        toolcrate sldl -a "artist" -t "track"    # Download specific track
        toolcrate --build sldl <playlist-url>    # Rebuild container and download from playlist
        toolcrate sldl --version                 # Show slsk-batchdl version
    """
    # Get the build flag from the parent context
    build_flag = ctx.obj.get('build', False) if ctx.obj else False

    # Pass all arguments to the docker command runner
    run_sldl_docker_command(ctx.params, ctx.args, build=build_flag)


# Add the schedule command group
main.add_command(schedule)


if __name__ == "__main__":
    main()
