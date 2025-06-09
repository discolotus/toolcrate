#!/usr/bin/env python3
"""Wishlist run log management CLI for ToolCrate."""

import click
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)


@click.group(name="wishlist-run")
@click.pass_context
def wishlist_run(ctx):
    """View logs and status from scheduled wishlist runs.

    This command helps you monitor and troubleshoot your scheduled wishlist downloads.
    You can view recent logs, check the status of the last run, or follow logs in real-time.
    """
    # Ensure we have a config manager in the context
    if not hasattr(ctx, "obj") or ctx.obj is None:
        ctx.obj = {}

    if "config_manager" not in ctx.obj:
        ctx.obj["config_manager"] = ConfigManager()


@wishlist_run.command()
@click.option(
    "--lines", "-n", default=50, type=int, help="Number of lines to show (default: 50)"
)
@click.option("--follow", "-f", is_flag=True, help="Follow log output in real-time")
@click.option(
    "--app-logs", is_flag=True, help="Show application logs instead of sldl logs"
)
@click.option(
    "--since", type=str, help='Show logs since time (e.g., "1h", "30m", "2d")'
)
def logs(lines: int, follow: bool, app_logs: bool, since: Optional[str]):
    """Show recent logs from wishlist runs.

    By default, shows the sldl download logs. Use --app-logs to see
    the Python application logs instead.

    Examples:
        toolcrate wishlist-run logs                    # Show last 50 lines
        toolcrate wishlist-run logs -n 100            # Show last 100 lines
        toolcrate wishlist-run logs --follow          # Follow logs in real-time
        toolcrate wishlist-run logs --app-logs        # Show Python app logs
        toolcrate wishlist-run logs --since 1h        # Show logs from last hour
    """
    try:
        if app_logs:
            log_path = Path("logs/app.log")
            log_type = "Application"
        else:
            log_path = Path("data/sldl.log")
            log_type = "SLDL Download"

        if not log_path.exists():
            click.echo(f"❌ {log_type} log file not found: {log_path}")
            return

        click.echo(f"📋 {log_type} Logs ({log_path})")
        click.echo("=" * 60)

        if follow:
            # Follow logs in real-time
            _follow_log_file(log_path)
        else:
            # Show recent logs
            _show_recent_logs(log_path, lines, since)

    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        click.echo(f"❌ Error reading logs: {e}")
        raise click.Abort()


@wishlist_run.command()
def status():
    """Show the status and summary of the last wishlist run.

    This command analyzes recent logs to provide a summary of:
    - When the last run occurred
    - How many items were processed
    - Success/failure counts
    - Recent downloads
    """
    try:
        click.echo("📊 Wishlist Run Status")
        click.echo("=" * 40)

        # Check both log files for recent activity
        app_log_path = Path("logs/app.log")
        sldl_log_path = Path("data/sldl.log")

        # Analyze application logs for wishlist processor activity
        app_status = _analyze_app_logs(app_log_path)

        # Analyze sldl logs for download activity
        sldl_status = _analyze_sldl_logs(sldl_log_path)

        # Display combined status
        _display_status_summary(app_status, sldl_status)

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        click.echo(f"❌ Error getting status: {e}")
        raise click.Abort()


@wishlist_run.command()
@click.option(
    "--lines",
    "-n",
    default=20,
    type=int,
    help="Number of recent lines to show before following",
)
def tail(lines: int):
    """Follow wishlist logs in real-time.

    This is equivalent to 'toolcrate wishlist-run logs --follow' but shows
    both application and download logs in a combined view.
    """
    click.echo("📡 Following Wishlist Logs (Ctrl+C to stop)")
    click.echo("=" * 50)

    try:
        # Show recent lines first
        app_log_path = Path("logs/app.log")
        sldl_log_path = Path("data/sldl.log")

        if app_log_path.exists():
            click.echo("\n🔍 Recent Application Logs:")
            _show_recent_logs(app_log_path, lines // 2, None)

        if sldl_log_path.exists():
            click.echo("\n📥 Recent Download Logs:")
            _show_recent_logs(sldl_log_path, lines // 2, None)

        click.echo("\n📡 Following new log entries...")
        click.echo("-" * 50)

        # Follow both files
        _follow_multiple_logs([app_log_path, sldl_log_path])

    except KeyboardInterrupt:
        click.echo("\n👋 Stopped following logs")
    except Exception as e:
        logger.error(f"Error following logs: {e}")
        click.echo(f"❌ Error following logs: {e}")
        raise click.Abort()


def _show_recent_logs(log_path: Path, lines: int, since: Optional[str]):
    """Show recent lines from a log file."""
    try:
        with open(log_path, "r") as f:
            all_lines = f.readlines()

        # Filter by time if requested
        if since:
            cutoff_time = _parse_time_delta(since)
            filtered_lines = _filter_lines_by_time(all_lines, cutoff_time)
            recent_lines = filtered_lines
        else:
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        for line in recent_lines:
            # Add some basic formatting for readability
            line = line.rstrip()
            if line:
                if "ERROR" in line or "Failed:" in line:
                    click.echo(click.style(line, fg="red"))
                elif "SUCCESS" in line or "Succeeded:" in line or "Succeded:" in line:
                    click.echo(click.style(line, fg="green"))
                elif "WARNING" in line or "WARN" in line:
                    click.echo(click.style(line, fg="yellow"))
                else:
                    click.echo(line)

    except Exception as e:
        click.echo(f"Error reading {log_path}: {e}")


def _follow_log_file(log_path: Path):
    """Follow a log file in real-time."""
    try:
        # Use tail -f equivalent
        process = subprocess.Popen(
            ["tail", "-f", str(log_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            for line in iter(process.stdout.readline, ""):
                line = line.rstrip()
                if line:
                    # Add color formatting
                    if "ERROR" in line or "Failed:" in line:
                        click.echo(click.style(line, fg="red"))
                    elif (
                        "SUCCESS" in line or "Succeeded:" in line or "Succeded:" in line
                    ):
                        click.echo(click.style(line, fg="green"))
                    elif "WARNING" in line or "WARN" in line:
                        click.echo(click.style(line, fg="yellow"))
                    else:
                        click.echo(line)
        except KeyboardInterrupt:
            process.terminate()
            click.echo("\n👋 Stopped following logs")

    except Exception as e:
        click.echo(f"Error following {log_path}: {e}")


def _follow_multiple_logs(log_paths: List[Path]):
    """Follow multiple log files simultaneously."""
    # This is a simplified version - in practice you might want to use a more
    # sophisticated approach like multitail or a custom implementation
    existing_paths = [p for p in log_paths if p.exists()]

    if not existing_paths:
        click.echo("No log files found to follow")
        return

    # For now, just follow the sldl log as it's most relevant for downloads
    sldl_path = next(
        (p for p in existing_paths if "sldl.log" in str(p)), existing_paths[0]
    )
    _follow_log_file(sldl_path)


def _parse_time_delta(time_str: str) -> datetime:
    """Parse time delta string like '1h', '30m', '2d' into a datetime."""
    now = datetime.now()

    if time_str.endswith("m"):
        minutes = int(time_str[:-1])
        return now - timedelta(minutes=minutes)
    elif time_str.endswith("h"):
        hours = int(time_str[:-1])
        return now - timedelta(hours=hours)
    elif time_str.endswith("d"):
        days = int(time_str[:-1])
        return now - timedelta(days=days)
    else:
        raise ValueError(
            f"Invalid time format: {time_str}. Use format like '1h', '30m', '2d'"
        )


def _filter_lines_by_time(lines: List[str], cutoff_time: datetime) -> List[str]:
    """Filter log lines to only include those after cutoff_time."""
    # This is a simplified implementation - you might want to improve
    # the timestamp parsing based on your actual log format
    filtered = []
    for line in lines:
        # Try to extract timestamp from line (this is basic and may need adjustment)
        try:
            # Look for ISO format timestamps or other common formats
            if len(line) > 19 and line[4] == "-" and line[7] == "-":
                # Looks like YYYY-MM-DD format
                timestamp_str = line[:19]
                line_time = datetime.fromisoformat(timestamp_str.replace(" ", "T"))
                if line_time >= cutoff_time:
                    filtered.append(line)
            else:
                # If we can't parse timestamp, include the line
                filtered.append(line)
        except:
            # If timestamp parsing fails, include the line
            filtered.append(line)

    return filtered


def _analyze_app_logs(log_path: Path) -> Dict[str, Any]:
    """Analyze application logs for wishlist processor activity."""
    if not log_path.exists():
        return {"status": "no_logs", "last_run": None}

    try:
        with open(log_path, "r") as f:
            lines = f.readlines()

        # Look for wishlist processor activity in recent lines
        recent_lines = lines[-200:] if len(lines) > 200 else lines

        last_run = None
        processed_count = 0
        failed_count = 0
        status = "unknown"

        for line in recent_lines:
            if "wishlist" in line.lower() and "processing" in line.lower():
                # Extract timestamp if possible
                if len(line) > 19:
                    try:
                        timestamp_str = line[:19]
                        last_run = datetime.fromisoformat(
                            timestamp_str.replace(" ", "T")
                        )
                    except:
                        pass

                if "complete" in line.lower():
                    # Try to extract counts
                    if "successful" in line and "failed" in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part.isdigit() and i < len(parts) - 1:
                                if "successful" in parts[i + 1]:
                                    processed_count = int(part)
                                elif "failed" in parts[i + 1]:
                                    failed_count = int(part)
                    status = "completed"

        return {
            "status": status,
            "last_run": last_run,
            "processed": processed_count,
            "failed": failed_count,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


def _analyze_sldl_logs(log_path: Path) -> Dict[str, Any]:
    """Analyze sldl logs for download activity."""
    if not log_path.exists():
        return {"status": "no_logs", "downloads": []}

    try:
        with open(log_path, "r") as f:
            lines = f.readlines()

        # Look for recent download activity
        recent_lines = lines[-100:] if len(lines) > 100 else lines

        downloads = []
        failed_downloads = []

        for line in recent_lines:
            line = line.strip()
            if "Succeeded:" in line or "Succeded:" in line:
                # Extract filename
                if "\\..\\" in line:
                    filename = line.split("\\..\\")[-1].split(" [")[0]
                    downloads.append(filename)
            elif "Failed:" in line:
                # Extract failed item info
                if ":" in line:
                    failed_item = line.split("Failed:")[-1].strip()
                    failed_downloads.append(failed_item)

        return {
            "status": "active" if downloads or failed_downloads else "idle",
            "downloads": downloads[-10:],  # Last 10 downloads
            "failed": failed_downloads[-5:],  # Last 5 failures
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


def _display_status_summary(app_status: Dict[str, Any], sldl_status: Dict[str, Any]):
    """Display a combined status summary."""

    # Last run information
    if app_status.get("last_run"):
        last_run_time = app_status["last_run"]
        time_ago = datetime.now() - last_run_time
        click.echo(f"🕐 Last Run: {last_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo(f"   ({_format_time_ago(time_ago)} ago)")
    else:
        click.echo("🕐 Last Run: No recent runs found")

    click.echo()

    # Processing statistics
    if app_status.get("status") == "completed":
        processed = app_status.get("processed", 0)
        failed = app_status.get("failed", 0)
        total = processed + failed

        click.echo(f"📊 Processing Results:")
        click.echo(f"   Total items: {total}")
        click.echo(f"   ✅ Successful: {processed}")
        click.echo(f"   ❌ Failed: {failed}")

        if total > 0:
            success_rate = (processed / total) * 100
            click.echo(f"   📈 Success rate: {success_rate:.1f}%")

    click.echo()

    # Recent downloads
    downloads = sldl_status.get("downloads", [])
    if downloads:
        click.echo(f"🎵 Recent Downloads ({len(downloads)}):")
        for download in downloads:
            click.echo(f"   ✅ {download}")
    else:
        click.echo("🎵 Recent Downloads: None found")

    # Recent failures
    failed = sldl_status.get("failed", [])
    if failed:
        click.echo()
        click.echo(f"❌ Recent Failures ({len(failed)}):")
        for failure in failed:
            click.echo(f"   ❌ {failure}")


def _format_time_ago(delta: timedelta) -> str:
    """Format a timedelta into a human-readable string."""
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds} seconds"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes} minutes"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours} hours"
    else:
        days = total_seconds // 86400
        return f"{days} days"
