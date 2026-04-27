#!/usr/bin/env python3
"""Main CLI entry point for ToolCrate."""

import click

from toolcrate.cli import binary_manager


@click.group()
@click.version_option()
def main():
    """ToolCrate - A unified tool suite for music management and processing."""
    pass


@main.command()
def info():
    """Show information about available tools."""
    click.echo("ToolCrate - Available Tools:")
    for status in binary_manager.tool_statuses():
        location = status.system_path or str(status.managed_path)
        marker = "installed" if status.installed else "missing"
        click.echo(f"  - {status.name}: {marker} ({location})")


@main.group()
def tools():
    """Install and inspect integrated command line tools."""


@tools.command("status")
def tools_status():
    """Show managed and system tool resolution."""
    click.echo(f"ToolCrate home: {binary_manager.toolcrate_home()}")
    click.echo(f"Managed bin:    {binary_manager.managed_bin_dir()}")
    for status in binary_manager.tool_statuses():
        click.echo("")
        click.echo(f"{status.name}")
        click.echo(f"  command:      {status.command}")
        click.echo(f"  installed:    {'yes' if status.installed else 'no'}")
        click.echo(f"  managed path: {status.managed_path}")
        click.echo(f"  system path:  {status.system_path or '-'}")
        click.echo(f"  resolution:   {status.note}")


@tools.command("install")
@click.option(
    "--tool",
    "selected_tools",
    multiple=True,
    type=click.Choice(["sldl", "shazam-tool", "mdl-tool"]),
    help="Install only the selected tool. Can be passed more than once.",
)
def tools_install(selected_tools):
    """Install integrated tools as local executables."""
    installers = {
        "sldl": binary_manager.install_sldl,
        "shazam-tool": binary_manager.install_shazam_tool,
        "mdl-tool": binary_manager.install_mdl_tool,
    }
    selected = selected_tools or tuple(installers)

    for tool_name in selected:
        click.echo(f"Installing {tool_name}...")
        try:
            path = installers[tool_name]()
        except (
            Exception
        ) as exc:  # noqa: BLE001 - CLI boundary should print readable errors.
            raise click.ClickException(str(exc)) from exc
        click.echo(f"  installed: {path}")


@tools.command("verify")
@click.option(
    "--timeout", default=10, show_default=True, help="Seconds per tool check."
)
def tools_verify(timeout):
    """Run smoke checks against installed integrated tools."""
    results = binary_manager.verify_tools(timeout=timeout)
    failed = False
    for result in results:
        status = "ok" if result.ok else "failed"
        click.echo(f"{result.name}: {status}")
        click.echo(f"  executable: {result.executable or '-'}")
        if result.returncode is not None:
            click.echo(f"  returncode: {result.returncode}")
        if result.error:
            click.echo(f"  error: {result.error}")
        if result.output:
            first_line = result.output.splitlines()[0]
            click.echo(f"  output: {first_line}")
        failed = failed or not result.ok

    if failed:
        raise click.ClickException("one or more tool checks failed")


if __name__ == "__main__":
    main()
