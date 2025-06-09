#!/usr/bin/env python3
"""Schedule management CLI for ToolCrate."""

import builtins
import logging
import os
import subprocess
import tempfile
from typing import Any

import click

from ..config.manager import ConfigManager
from ..wishlist.processor import WishlistProcessor

logger = logging.getLogger(__name__)


def get_current_crontab() -> str:
    """Get the current user's crontab content."""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            # No crontab exists yet
            return ""
    except Exception as e:
        logger.debug(f"Error reading crontab: {e}")
        return ""


def update_crontab(content: str) -> bool:
    """Update the user's crontab with new content."""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cron", delete=False) as f:
            f.write(content)
            temp_file = f.name

        result = subprocess.run(["crontab", temp_file], capture_output=True, text=True)
        os.unlink(temp_file)

        if result.returncode == 0:
            return True
        else:
            logger.error(f"Error updating crontab: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error updating crontab: {e}")
        return False


def remove_toolcrate_jobs_from_crontab() -> str:
    """Remove all ToolCrate jobs from crontab and return the cleaned content."""
    current_crontab = get_current_crontab()
    if not current_crontab:
        return ""

    lines = current_crontab.split("\n")
    cleaned_lines = []
    in_toolcrate_section = False

    for line in lines:
        if line.strip() == "# ToolCrate Scheduled Downloads":
            in_toolcrate_section = True
            continue
        elif (
            in_toolcrate_section
            and line.strip()
            and not line.startswith("#")
            and "toolcrate" not in line.lower()
        ):
            # End of ToolCrate section
            in_toolcrate_section = False
            cleaned_lines.append(line)
        elif not in_toolcrate_section:
            cleaned_lines.append(line)

    # Remove trailing empty lines
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)


def add_toolcrate_jobs_to_crontab(
    config_manager: ConfigManager, jobs: list[dict[str, Any]], cron_enabled: bool = True
) -> bool:
    """Add ToolCrate jobs to the user's crontab."""
    # Remove existing ToolCrate jobs first
    current_crontab = remove_toolcrate_jobs_from_crontab()

    # Generate new ToolCrate section
    toolcrate_section = generate_crontab_section(config_manager, jobs, cron_enabled)

    # Combine existing crontab with new ToolCrate section
    if current_crontab.strip():
        new_crontab = current_crontab + "\n\n" + toolcrate_section
    else:
        new_crontab = toolcrate_section

    return update_crontab(new_crontab)


def generate_crontab_section(
    config_manager: ConfigManager, jobs: list[dict[str, Any]], cron_enabled: bool = True
) -> str:
    """Generate the ToolCrate section for crontab."""
    lines = [
        "# ToolCrate Scheduled Downloads",
        "# Generated automatically - do not edit manually",
        "# Use 'toolcrate schedule' commands to manage",
        "",
    ]

    if not jobs:
        lines.append("# No jobs defined")
        return "\n".join(lines)

    # Get project root for command paths
    project_root = config_manager.config_dir.parent

    for job in jobs:
        name = job.get("name", "unnamed")
        schedule = job.get("schedule", "0 2 * * *")
        description = job.get("description", "")
        command = job.get("command", "wishlist")
        job_enabled = job.get("enabled", True)

        lines.append(f"# {name}: {description}")

        if command == "wishlist":
            # Wishlist processing command
            cmd = f"cd {project_root} && poetry run python -m toolcrate.wishlist.processor"
        elif command == "queue":
            # Queue processing command
            cmd = f"cd {project_root} && poetry run python -m toolcrate.queue.processor"
        else:
            # Custom command
            cmd = f"cd {project_root} && {command}"

        # Comment out the job if cron is disabled or job is disabled
        if not cron_enabled or not job_enabled:
            lines.append(f"# {schedule} {cmd}")
        else:
            lines.append(f"{schedule} {cmd}")

        lines.append("")

    return "\n".join(lines)


@click.group()
@click.pass_context
def schedule(ctx):
    """Manage scheduled downloads and cron jobs.

    The schedule command allows you to manage automated wishlist downloads
    using cron jobs. You can add, remove, or disable scheduled downloads.
    """
    # Ensure we have a config manager in the context
    if not hasattr(ctx, "obj") or ctx.obj is None:
        ctx.obj = {}

    if "config_manager" not in ctx.obj:
        ctx.obj["config_manager"] = ConfigManager()


@schedule.command()
@click.option(
    "--schedule",
    "-s",
    required=True,
    help='Cron schedule expression (e.g., "0 2 * * *" for daily at 2 AM)',
)
@click.option(
    "--name",
    "-n",
    default=None,
    help="Name for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Description for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--type",
    "-t",
    type=click.Choice(["wishlist", "download"]),
    default="wishlist",
    help="Type of scheduled job: wishlist (default) or download queue",
)
@click.pass_context
def add(ctx, schedule: str, name: str, description: str, type: str):
    """Add a new scheduled download job.

    Examples:
        toolcrate schedule add -s "0 2 * * *"                    # Daily wishlist at 2 AM
        toolcrate schedule add -s "0 2 * * *" --type download     # Daily download queue at 2 AM
        toolcrate schedule add -s "0 2 * * 0"                    # Weekly wishlist on Sunday at 2 AM
        toolcrate schedule add -s "0 2 1 * *"                    # Monthly wishlist on 1st at 2 AM
        toolcrate schedule add -s "*/30 * * * *" --type download  # Download queue every 30 minutes

    Use https://crontab.guru/ to help create cron expressions.
    """
    config_manager = ctx.obj["config_manager"]

    try:
        # Validate cron expression (basic validation)
        parts = schedule.split()
        if len(parts) != 5:
            raise click.BadParameter(
                "Cron schedule must have 5 parts: minute hour day month weekday"
            )

        # Auto-generate name and description if not provided
        if name is None:
            if type == "wishlist":
                name = "wishlist_download"
            else:
                name = "download_queue"

        if description is None:
            if type == "wishlist":
                description = "Automated wishlist download"
            else:
                description = "Automated download queue processing"

        # Load current config
        config_manager.load_config()
        config = config_manager.config

        # Ensure cron section exists
        if "cron" not in config:
            config["cron"] = {
                "enabled": True,
                "jobs": [],
            }  # Default to enabled for new cron section

        # Check if job with same name already exists
        existing_jobs = config["cron"].get("jobs", [])
        for job in existing_jobs:
            if job.get("name") == name:
                if not click.confirm(f"Job '{name}' already exists. Replace it?"):
                    click.echo("Operation cancelled.")
                    return
                # Remove existing job
                existing_jobs.remove(job)
                break

        # Create new job entry
        command = "wishlist" if type == "wishlist" else "queue"
        new_job = {
            "name": name,
            "schedule": schedule,
            "command": command,
            "description": description,
            "enabled": True,
        }

        # Add to jobs list
        config["cron"]["jobs"].append(new_job)

        # Save configuration using safer method
        config_manager.update_cron_section(config["cron"])

        # Automatically install to crontab
        cron_enabled = config["cron"].get("enabled", False)
        if add_toolcrate_jobs_to_crontab(
            config_manager, config["cron"]["jobs"], cron_enabled
        ):
            click.echo(f"✅ Added scheduled job '{name}' with schedule '{schedule}'")
            click.echo(f"📝 Description: {description}")
            if cron_enabled:
                click.echo("🕒 Job automatically installed to crontab and is active")
            else:
                click.echo("🕒 Job installed to crontab but is disabled")
                click.echo("💡 Run 'toolcrate schedule enable' to activate all jobs")
        else:
            click.echo(f"✅ Added scheduled job '{name}' with schedule '{schedule}'")
            click.echo(f"📝 Description: {description}")
            click.echo("⚠️  Could not automatically install to crontab")
            click.echo("💡 Run 'toolcrate schedule install' to install manually")

    except Exception as e:
        logger.error(f"Error adding scheduled job: {e}")
        click.echo(f"❌ Error adding scheduled job: {e}")
        raise click.Abort() from None


@schedule.command()
@click.option(
    "--name",
    "-n",
    default=None,
    help="Name for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Description for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--minute",
    "-m",
    default=0,
    type=int,
    help="Minute to run (0-59, default: 0 for top of hour)",
)
@click.option(
    "--type",
    "-t",
    type=click.Choice(["wishlist", "download"]),
    default="wishlist",
    help="Type of scheduled job: wishlist (default) or download queue",
)
@click.pass_context
def hourly(ctx, name: str, description: str, minute: int, type: str):
    """Add an hourly scheduled download job.

    This is a convenience command that sets up hourly execution.

    Examples:
        toolcrate schedule hourly                         # Hourly wishlist at minute 0
        toolcrate schedule hourly -m 30                   # Hourly wishlist at minute 30
        toolcrate schedule hourly --type download         # Hourly download queue at minute 0
        toolcrate schedule hourly -m 15 --type download   # Hourly download queue at minute 15
        toolcrate schedule hourly -n "frequent"           # Custom name
    """
    if not (0 <= minute <= 59):
        raise click.BadParameter("Minute must be between 0 and 59")

    schedule_expr = f"{minute} * * * *"

    # Call the main add function
    ctx.invoke(
        add, schedule=schedule_expr, name=name, description=description, type=type
    )


@schedule.command()
@click.option(
    "--name",
    "-n",
    default=None,
    help="Name for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Description for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--hour", "-h", default=2, type=int, help="Hour to run (0-23, default: 2 for 2 AM)"
)
@click.option(
    "--minute", "-m", default=0, type=int, help="Minute to run (0-59, default: 0)"
)
@click.option(
    "--type",
    "-t",
    type=click.Choice(["wishlist", "download"]),
    default="wishlist",
    help="Type of scheduled job: wishlist (default) or download queue",
)
@click.pass_context
def daily(ctx, name: str, description: str, hour: int, minute: int, type: str):
    """Add a daily scheduled download job.

    This is a convenience command that sets up daily execution.

    Examples:
        toolcrate schedule daily                          # Daily wishlist at 2:00 AM
        toolcrate schedule daily -h 14                    # Daily wishlist at 2:00 PM
        toolcrate schedule daily -h 9 -m 30               # Daily wishlist at 9:30 AM
        toolcrate schedule daily --type download          # Daily download queue at 2:00 AM
        toolcrate schedule daily -h 14 --type download    # Daily download queue at 2:00 PM
        toolcrate schedule daily -n "morning"             # Custom name
    """
    if not (0 <= hour <= 23):
        raise click.BadParameter("Hour must be between 0 and 23")
    if not (0 <= minute <= 59):
        raise click.BadParameter("Minute must be between 0 and 59")

    schedule_expr = f"{minute} {hour} * * *"

    # Call the main add function
    ctx.invoke(
        add, schedule=schedule_expr, name=name, description=description, type=type
    )


@schedule.command()
@click.option(
    "--name",
    "-n",
    default=None,
    help="Name for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Description for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--day",
    "-w",
    "weekday",
    default=0,
    type=int,
    help="Day of week (0=Sunday, 1=Monday, ..., 6=Saturday, default: 0)",
)
@click.option(
    "--hour", "-h", default=2, type=int, help="Hour to run (0-23, default: 2 for 2 AM)"
)
@click.option(
    "--minute", "-m", default=0, type=int, help="Minute to run (0-59, default: 0)"
)
@click.option(
    "--type",
    "-t",
    type=click.Choice(["wishlist", "download"]),
    default="wishlist",
    help="Type of scheduled job: wishlist (default) or download queue",
)
@click.pass_context
def weekly(
    ctx, name: str, description: str, weekday: int, hour: int, minute: int, type: str
):
    """Add a weekly scheduled download job.

    This is a convenience command that sets up weekly execution.

    Examples:
        toolcrate schedule weekly                         # Weekly wishlist on Sunday at 2:00 AM
        toolcrate schedule weekly -d 1                    # Weekly wishlist on Monday at 2:00 AM
        toolcrate schedule weekly -d 6 -h 14              # Weekly wishlist on Saturday at 2:00 PM
        toolcrate schedule weekly --type download         # Weekly download queue on Sunday at 2:00 AM
        toolcrate schedule weekly -d 1 --type download    # Weekly download queue on Monday at 2:00 AM
        toolcrate schedule weekly -n "weekend"            # Custom name

    Day codes: 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
    """
    if not (0 <= weekday <= 6):
        raise click.BadParameter("Day must be between 0 (Sunday) and 6 (Saturday)")
    if not (0 <= hour <= 23):
        raise click.BadParameter("Hour must be between 0 and 23")
    if not (0 <= minute <= 59):
        raise click.BadParameter("Minute must be between 0 and 59")

    schedule_expr = f"{minute} {hour} * * {weekday}"

    # Call the main add function
    ctx.invoke(
        add, schedule=schedule_expr, name=name, description=description, type=type
    )


@schedule.command()
@click.option(
    "--name",
    "-n",
    default=None,
    help="Name for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Description for the scheduled job (auto-generated if not provided)",
)
@click.option(
    "--day",
    "--monthday",
    "monthday",
    default=1,
    type=int,
    help="Day of month (1-31, default: 1 for first day)",
)
@click.option(
    "--hour", "-h", default=2, type=int, help="Hour to run (0-23, default: 2 for 2 AM)"
)
@click.option(
    "--minute", "-m", default=0, type=int, help="Minute to run (0-59, default: 0)"
)
@click.option(
    "--type",
    "-t",
    type=click.Choice(["wishlist", "download"]),
    default="wishlist",
    help="Type of scheduled job: wishlist (default) or download queue",
)
@click.pass_context
def monthly(
    ctx, name: str, description: str, monthday: int, hour: int, minute: int, type: str
):
    """Add a monthly scheduled download job.

    This is a convenience command that sets up monthly execution.

    Examples:
        toolcrate schedule monthly                        # Monthly wishlist on 1st at 2:00 AM
        toolcrate schedule monthly -d 15                  # Monthly wishlist on 15th at 2:00 AM
        toolcrate schedule monthly -d 1 -h 0              # Monthly wishlist on 1st at midnight
        toolcrate schedule monthly --type download        # Monthly download queue on 1st at 2:00 AM
        toolcrate schedule monthly -d 15 --type download  # Monthly download queue on 15th at 2:00 AM
        toolcrate schedule monthly -n "month_end"         # Custom name
    """
    if not (1 <= monthday <= 31):
        raise click.BadParameter("Day must be between 1 and 31")
    if not (0 <= hour <= 23):
        raise click.BadParameter("Hour must be between 0 and 23")
    if not (0 <= minute <= 59):
        raise click.BadParameter("Minute must be between 0 and 59")

    schedule_expr = f"{minute} {hour} {monthday} * *"

    # Call the main add function
    ctx.invoke(
        add, schedule=schedule_expr, name=name, description=description, type=type
    )


@schedule.command()
@click.option("--name", "-n", required=True, help="Name of the scheduled job to remove")
@click.pass_context
def remove(ctx, name: str):
    """Remove a scheduled job by name.

    Examples:
        toolcrate schedule remove -n wishlist_download
        toolcrate schedule remove --name hourly_queue
    """
    config_manager = ctx.obj["config_manager"]

    try:
        config_manager.load_config()
        config = config_manager.config

        if "cron" not in config or "jobs" not in config["cron"]:
            click.echo("No scheduled jobs found.")
            return

        jobs = config["cron"]["jobs"]
        job_found = False

        for i, job in enumerate(jobs):
            if job.get("name") == name:
                if click.confirm(f"Remove scheduled job '{name}'?"):
                    jobs.pop(i)
                    config_manager.update_cron_section(config["cron"])

                    # Update crontab
                    cron_enabled = config["cron"].get("enabled", False)
                    if add_toolcrate_jobs_to_crontab(
                        config_manager, jobs, cron_enabled
                    ):
                        click.echo(
                            f"✅ Removed scheduled job '{name}' from config and crontab"
                        )
                    else:
                        click.echo(f"✅ Removed scheduled job '{name}' from config")
                        click.echo("⚠️  Could not update crontab automatically")

                    # If no jobs left, suggest disabling cron
                    if not jobs:
                        click.echo(
                            "💡 No scheduled jobs remaining. Consider running 'toolcrate schedule disable'"
                        )
                else:
                    click.echo("Operation cancelled.")
                job_found = True
                break

        if not job_found:
            click.echo(f"❌ Job '{name}' not found.")
            click.echo("Available jobs:")
            for job in jobs:
                click.echo(f"  - {job.get('name', 'unnamed')}")

    except Exception as e:
        logger.error(f"Error removing scheduled job: {e}")
        click.echo(f"❌ Error removing scheduled job: {e}")
        raise click.Abort() from None


@schedule.command()
@click.option("--name", "-n", required=True, help="Name of the scheduled job to edit")
@click.option(
    "--schedule",
    "-s",
    required=True,
    help='New cron schedule expression (e.g., "0 2 * * *" for daily at 2 AM)',
)
@click.pass_context
def edit(ctx, name: str, schedule: str):
    """Edit the schedule of an existing job.

    Examples:
        toolcrate schedule edit -n wishlist_download -s "0 3 * * *"    # Change to 3 AM daily
        toolcrate schedule edit -n hourly_queue -s "*/15 * * * *"      # Change to every 15 minutes
        toolcrate schedule edit --name daily_backup --schedule "0 1 * * 0"  # Change to weekly Sunday 1 AM

    Use https://crontab.guru/ to help create cron expressions.
    """
    config_manager = ctx.obj["config_manager"]

    try:
        # Validate cron expression (basic validation)
        parts = schedule.split()
        if len(parts) != 5:
            raise click.BadParameter(
                "Cron schedule must have 5 parts: minute hour day month weekday"
            )

        config_manager.load_config()
        config = config_manager.config

        if "cron" not in config or "jobs" not in config["cron"]:
            click.echo("No scheduled jobs found.")
            return

        jobs = config["cron"]["jobs"]
        job_found = False

        for job in jobs:
            if job.get("name") == name:
                old_schedule = job.get("schedule", "unknown")
                job["schedule"] = schedule
                config_manager.update_cron_section(config["cron"])

                # Update crontab
                cron_enabled = config["cron"].get("enabled", False)
                if add_toolcrate_jobs_to_crontab(config_manager, jobs, cron_enabled):
                    click.echo(f"✅ Updated scheduled job '{name}'")
                    click.echo(f"📅 Old schedule: {old_schedule}")
                    click.echo(f"📅 New schedule: {schedule}")
                    if cron_enabled:
                        click.echo("🕒 Changes automatically applied to crontab")
                    else:
                        click.echo("🕒 Changes saved but cron is disabled")
                        click.echo("💡 Run 'toolcrate schedule enable' to activate")
                else:
                    click.echo(f"✅ Updated scheduled job '{name}' in config")
                    click.echo(f"📅 Old schedule: {old_schedule}")
                    click.echo(f"📅 New schedule: {schedule}")
                    click.echo("⚠️  Could not update crontab automatically")
                    click.echo(
                        "💡 Run 'toolcrate schedule install' to install manually"
                    )

                job_found = True
                break

        if not job_found:
            click.echo(f"❌ Job '{name}' not found.")
            click.echo("Available jobs:")
            for job in jobs:
                click.echo(f"  - {job.get('name', 'unnamed')}")

    except Exception as e:
        logger.error(f"Error editing scheduled job: {e}")
        click.echo(f"❌ Error editing scheduled job: {e}")
        raise click.Abort() from None


@schedule.command()
@click.pass_context
def disable(ctx):
    """Disable all scheduled downloads.

    This disables cron job execution but keeps the job definitions.
    """
    config_manager = ctx.obj["config_manager"]

    try:
        config_manager.load_config()
        config = config_manager.config

        if "cron" not in config:
            config["cron"] = {"enabled": False, "jobs": []}

        config["cron"]["enabled"] = False
        config_manager.update_cron_section(config["cron"])

        # Update crontab to comment out jobs
        jobs = config["cron"].get("jobs", [])
        if jobs and add_toolcrate_jobs_to_crontab(config_manager, jobs, False):
            click.echo("✅ Disabled all scheduled downloads")
            click.echo(f"📋 {len(jobs)} job(s) are now commented out in crontab")
            click.echo(
                "💡 Job definitions are preserved. Use 'toolcrate schedule enable' to re-enable."
            )
        else:
            click.echo("✅ Disabled all scheduled downloads in config")
            click.echo(
                "💡 Job definitions are preserved. Use 'toolcrate schedule enable' to re-enable."
            )
            if jobs:
                click.echo("⚠️  Could not update crontab automatically")

    except Exception as e:
        logger.error(f"Error disabling scheduled jobs: {e}")
        click.echo(f"❌ Error disabling scheduled jobs: {e}")
        raise click.Abort() from None


@schedule.command()
@click.pass_context
def enable(ctx):
    """Enable scheduled downloads.

    This enables cron job execution for all defined jobs.
    """
    config_manager = ctx.obj["config_manager"]

    try:
        config_manager.load_config()
        config = config_manager.config

        if "cron" not in config:
            config["cron"] = {"enabled": True, "jobs": []}
        else:
            config["cron"]["enabled"] = True

        config_manager.update_cron_section(config["cron"])

        jobs = config["cron"].get("jobs", [])
        if jobs:
            # Update crontab to enable jobs
            if add_toolcrate_jobs_to_crontab(config_manager, jobs, True):
                click.echo("✅ Enabled scheduled downloads")
                click.echo(f"📋 {len(jobs)} job(s) are now active in crontab")
            else:
                click.echo("✅ Enabled scheduled downloads in config")
                click.echo(f"📋 {len(jobs)} job(s) will be active")
                click.echo("⚠️  Could not update crontab automatically")
                click.echo("💡 Run 'toolcrate schedule install' to install manually")
        else:
            click.echo("✅ Enabled scheduled downloads")
            click.echo(
                "💡 No jobs defined yet. Use 'toolcrate schedule add' to create jobs"
            )

    except Exception as e:
        logger.error(f"Error enabling scheduled jobs: {e}")
        click.echo(f"❌ Error enabling scheduled jobs: {e}")
        raise click.Abort() from None


@schedule.command()
@click.pass_context
def list(ctx):
    """List all scheduled jobs."""
    config_manager = ctx.obj["config_manager"]

    try:
        config_manager.load_config()
        config = config_manager.config

        cron_config = config.get("cron", {})
        enabled = cron_config.get("enabled", False)
        jobs = cron_config.get("jobs", [])

        click.echo(f"Scheduled Downloads: {'✅ Enabled' if enabled else '❌ Disabled'}")
        click.echo()

        if not jobs:
            click.echo("No scheduled jobs defined.")
            click.echo("Use 'toolcrate schedule add' to create a job.")
            return

        click.echo(f"Jobs ({len(jobs)}):")
        for job in jobs:
            name = job.get("name", "unnamed")
            schedule = job.get("schedule", "unknown")
            description = job.get("description", "No description")
            job_enabled = job.get("enabled", True)

            status = "✅" if job_enabled else "❌"
            click.echo(f"  {status} {name}")
            click.echo(f"      Schedule: {schedule}")
            click.echo(f"      Description: {description}")
            click.echo()

    except Exception as e:
        logger.error(f"Error listing scheduled jobs: {e}")
        click.echo(f"❌ Error listing scheduled jobs: {e}")
        raise click.Abort() from None


@schedule.command()
@click.pass_context
def status(ctx):
    """Show crontab installation status."""
    config_manager = ctx.obj["config_manager"]

    try:
        config_manager.load_config()
        config = config_manager.config

        cron_config = config.get("cron", {})
        enabled = cron_config.get("enabled", False)
        jobs = cron_config.get("jobs", [])

        click.echo("📋 ToolCrate Cron Status")
        click.echo("=" * 25)
        click.echo(f"Config Status: {'✅ Enabled' if enabled else '❌ Disabled'}")
        click.echo(f"Defined Jobs: {len(jobs)}")

        # Check crontab status
        current_crontab = get_current_crontab()
        has_toolcrate_section = "# ToolCrate Scheduled Downloads" in current_crontab

        if has_toolcrate_section:
            # Count active vs commented jobs in crontab
            lines = current_crontab.split("\n")
            active_jobs = 0
            commented_jobs = 0

            for line in lines:
                line = line.strip()
                if "toolcrate" in line.lower() and not line.startswith("# "):
                    if line.startswith("#"):
                        commented_jobs += 1
                    elif line and not line.startswith("# "):
                        active_jobs += 1

            click.echo("Crontab Status: ✅ Installed")
            click.echo(f"Active Jobs: {active_jobs}")
            click.echo(f"Disabled Jobs: {commented_jobs}")
        else:
            click.echo("Crontab Status: ❌ Not installed")

        click.echo()
        if jobs:
            click.echo("Jobs in config:")
            for job in jobs:
                name = job.get("name", "unnamed")
                schedule = job.get("schedule", "unknown")
                job_enabled = job.get("enabled", True)
                status_icon = "✅" if job_enabled else "❌"
                click.echo(f"  {status_icon} {name} ({schedule})")

        if not has_toolcrate_section and jobs:
            click.echo()
            click.echo("💡 Run 'toolcrate schedule install' to install jobs to crontab")

    except Exception as e:
        logger.error(f"Error checking cron status: {e}")
        click.echo(f"❌ Error checking cron status: {e}")
        raise click.Abort() from None


@schedule.command()
@click.pass_context
def install(ctx):
    """Install cron jobs to the system crontab.

    This command is usually not needed as jobs are automatically installed
    when added/enabled. Use this for manual installation or troubleshooting.
    """
    config_manager = ctx.obj["config_manager"]

    try:
        config_manager.load_config()
        config = config_manager.config

        cron_config = config.get("cron", {})
        jobs = cron_config.get("jobs", [])

        if not jobs:
            click.echo("❌ No scheduled jobs defined.")
            click.echo("Use 'toolcrate schedule add' to create jobs.")
            return

        cron_enabled = cron_config.get("enabled", False)

        # Try automatic installation first
        if add_toolcrate_jobs_to_crontab(config_manager, jobs, cron_enabled):
            status = "active" if cron_enabled else "disabled (commented out)"
            click.echo(f"✅ Successfully installed {len(jobs)} job(s) to crontab")
            click.echo(f"📋 Jobs are {status}")
            click.echo("💡 Use 'crontab -l' to verify installation")
        else:
            # Fall back to manual installation instructions
            click.echo("⚠️  Automatic installation failed. Using manual method...")

            # Generate cron file for manual installation
            cron_content = generate_cron_file(config_manager, jobs)

            # Write to crontabs directory
            cron_dir = config_manager.config_dir / "crontabs"
            cron_dir.mkdir(exist_ok=True)
            cron_file = cron_dir / "toolcrate"

            with open(cron_file, "w") as f:
                f.write(cron_content)

            click.echo(f"✅ Generated cron file: {cron_file}")
            click.echo()
            click.echo("To install the cron jobs manually, choose one option:")
            click.echo()
            click.echo("Option 1 - User-specific (recommended):")
            click.echo(f"  crontab {cron_file}")
            click.echo()
            click.echo("Option 2 - System-wide (requires sudo):")
            click.echo(f"  sudo cp {cron_file} /etc/cron.d/toolcrate")
            click.echo()
            click.echo("💡 Use 'crontab -l' to verify installation")

    except Exception as e:
        logger.error(f"Error installing cron jobs: {e}")
        click.echo(f"❌ Error installing cron jobs: {e}")
        raise click.Abort() from None


def generate_cron_file(
    config_manager: ConfigManager, jobs: builtins.list[dict[str, Any]]
) -> str:
    """Generate cron file content from job definitions."""
    lines = [
        "# ToolCrate Scheduled Downloads",
        "# Generated automatically - do not edit manually",
        "# Use 'toolcrate schedule' commands to manage",
        "",
        "# Format: minute hour day month weekday command",
        "",
    ]

    # Get project root for command paths
    project_root = config_manager.config_dir.parent

    for job in jobs:
        if not job.get("enabled", True):
            continue

        name = job.get("name", "unnamed")
        schedule = job.get("schedule", "0 2 * * *")
        description = job.get("description", "")
        command = job.get("command", "wishlist")

        lines.append(f"# {name}: {description}")

        if command == "wishlist":
            # Wishlist processing command
            cmd = f"cd {project_root} && poetry run python -m toolcrate.wishlist.processor"
        elif command == "queue":
            # Queue processing command
            cmd = f"cd {project_root} && poetry run python -m toolcrate.queue.processor"
        else:
            # Custom command
            cmd = f"cd {project_root} && {command}"

        lines.append(f"{schedule} {cmd}")
        lines.append("")

    return "\n".join(lines)


@schedule.command()
@click.pass_context
def test(ctx):
    """Test wishlist processing without scheduling.

    This runs the wishlist processor once to test your configuration.
    """
    config_manager = ctx.obj["config_manager"]

    try:
        click.echo("🧪 Testing wishlist processing...")

        processor = WishlistProcessor(config_manager)
        results = processor.process_all_entries()

        click.echo()
        click.echo(f"Test Results: {results['status']}")

        if results["status"] == "completed":
            click.echo(f"✅ Processed: {results['processed']}/{results['total']}")
            click.echo(f"❌ Failed: {results['failed']}/{results['total']}")

            if results["failed"] > 0:
                click.echo()
                click.echo("Failed entries:")
                for result in results["results"]:
                    if not result["success"]:
                        click.echo(f"  - {result['entry']}")

        elif results["status"] == "disabled":
            click.echo("❌ Wishlist processing is disabled in configuration")
        elif results["status"] == "empty":
            click.echo("📝 No entries found in wishlist file")
            wishlist_path = processor.get_wishlist_file_path()
            click.echo(f"💡 Add entries to: {wishlist_path}")

    except Exception as e:
        logger.error(f"Error testing wishlist processing: {e}")
        click.echo(f"❌ Error testing wishlist processing: {e}")
        raise click.Abort() from None


@schedule.command()
@click.pass_context
def test_queue(ctx):
    """Test queue processing without scheduling.

    This runs the queue processor once to test your configuration.
    """
    config_manager = ctx.obj["config_manager"]

    try:
        click.echo("🧪 Testing queue processing...")

        from ..queue.processor import QueueProcessor

        processor = QueueProcessor(config_manager)
        results = processor.process_all_entries()

        click.echo()
        click.echo(f"Test Results: {results['status']}")

        if results["status"] == "completed":
            click.echo(f"✅ Processed: {results['processed']}/{results['total']}")
            click.echo(f"❌ Failed: {results['failed']}/{results['total']}")

            if results["failed"] > 0:
                click.echo()
                click.echo("Failed entries:")
                for result in results["results"]:
                    if not result["success"]:
                        click.echo(f"  - {result['entry']}")

        elif results["status"] == "disabled":
            click.echo("❌ Queue processing is disabled in configuration")
        elif results["status"] == "empty":
            click.echo("📝 No entries found in queue file")
            click.echo(f"💡 Add entries to: {processor.queue_file_path}")
            click.echo("💡 Use: toolcrate queue add <link>")
        elif results["status"] == "locked":
            click.echo("🔒 Queue processing is already running")

    except Exception as e:
        logger.error(f"Error testing queue processing: {e}")
        click.echo(f"❌ Error testing queue processing: {e}")
        raise click.Abort() from None
