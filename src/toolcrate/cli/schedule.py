#!/usr/bin/env python3
"""Schedule management CLI for ToolCrate."""

import click
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from ..config.manager import ConfigManager
from ..wishlist.processor import WishlistProcessor

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def schedule(ctx):
    """Manage scheduled downloads and cron jobs.
    
    The schedule command allows you to manage automated wishlist downloads
    using cron jobs. You can add, remove, or disable scheduled downloads.
    """
    # Ensure we have a config manager in the context
    if not hasattr(ctx, 'obj') or ctx.obj is None:
        ctx.obj = {}
    
    if 'config_manager' not in ctx.obj:
        ctx.obj['config_manager'] = ConfigManager()


@schedule.command()
@click.option('--schedule', '-s', required=True,
              help='Cron schedule expression (e.g., "0 2 * * *" for daily at 2 AM)')
@click.option('--name', '-n', default='wishlist_download',
              help='Name for the scheduled job')
@click.option('--description', '-d', default='Automated wishlist download',
              help='Description for the scheduled job')
@click.pass_context
def add(ctx, schedule: str, name: str, description: str):
    """Add a new scheduled wishlist download.
    
    Examples:
        toolcrate schedule add -s "0 2 * * *"           # Daily at 2 AM
        toolcrate schedule add -s "0 2 * * 0"           # Weekly on Sunday at 2 AM
        toolcrate schedule add -s "0 2 1 * *"           # Monthly on 1st at 2 AM
        toolcrate schedule add -s "*/30 * * * *"        # Every 30 minutes
    
    Use https://crontab.guru/ to help create cron expressions.
    """
    config_manager = ctx.obj['config_manager']
    
    try:
        # Validate cron expression (basic validation)
        parts = schedule.split()
        if len(parts) != 5:
            raise click.BadParameter("Cron schedule must have 5 parts: minute hour day month weekday")
        
        # Load current config
        config_manager.load_config()
        config = config_manager.config
        
        # Ensure cron section exists
        if 'cron' not in config:
            config['cron'] = {'enabled': False, 'jobs': []}
        
        # Check if job with same name already exists
        existing_jobs = config['cron'].get('jobs', [])
        for job in existing_jobs:
            if job.get('name') == name:
                if not click.confirm(f"Job '{name}' already exists. Replace it?"):
                    click.echo("Operation cancelled.")
                    return
                # Remove existing job
                existing_jobs.remove(job)
                break
        
        # Create new job entry
        new_job = {
            'name': name,
            'schedule': schedule,
            'command': 'wishlist',
            'description': description,
            'enabled': True
        }
        
        # Add to jobs list
        config['cron']['jobs'].append(new_job)

        # Save configuration using safer method
        config_manager.update_cron_section(config['cron'])
        
        click.echo(f"✅ Added scheduled job '{name}' with schedule '{schedule}'")
        click.echo(f"📝 Description: {description}")
        click.echo()
        click.echo("To activate the schedule:")
        click.echo("1. Enable cron jobs: toolcrate schedule enable")
        click.echo("2. Install the cron job: toolcrate schedule install")
        
    except Exception as e:
        logger.error(f"Error adding scheduled job: {e}")
        click.echo(f"❌ Error adding scheduled job: {e}")
        raise click.Abort()


@schedule.command()
@click.option('--name', '-n', default='hourly_wishlist',
              help='Name for the scheduled job')
@click.option('--description', '-d', default='Hourly wishlist download',
              help='Description for the scheduled job')
@click.option('--minute', '-m', default=0, type=int,
              help='Minute to run (0-59, default: 0 for top of hour)')
@click.pass_context
def hourly(ctx, name: str, description: str, minute: int):
    """Add an hourly scheduled wishlist download.

    This is a convenience command that sets up hourly execution.

    Examples:
        toolcrate schedule hourly                    # Every hour at minute 0
        toolcrate schedule hourly -m 30              # Every hour at minute 30
        toolcrate schedule hourly -n "frequent"      # Custom name
    """
    if not (0 <= minute <= 59):
        raise click.BadParameter("Minute must be between 0 and 59")

    schedule_expr = f"{minute} * * * *"

    # Call the main add function
    ctx.invoke(add, schedule=schedule_expr, name=name, description=description)


@schedule.command()
@click.option('--name', '-n', default='daily_wishlist',
              help='Name for the scheduled job')
@click.option('--description', '-d', default='Daily wishlist download',
              help='Description for the scheduled job')
@click.option('--hour', '-h', default=2, type=int,
              help='Hour to run (0-23, default: 2 for 2 AM)')
@click.option('--minute', '-m', default=0, type=int,
              help='Minute to run (0-59, default: 0)')
@click.pass_context
def daily(ctx, name: str, description: str, hour: int, minute: int):
    """Add a daily scheduled wishlist download.

    This is a convenience command that sets up daily execution.

    Examples:
        toolcrate schedule daily                     # Daily at 2:00 AM
        toolcrate schedule daily -h 14               # Daily at 2:00 PM
        toolcrate schedule daily -h 9 -m 30          # Daily at 9:30 AM
        toolcrate schedule daily -n "morning"        # Custom name
    """
    if not (0 <= hour <= 23):
        raise click.BadParameter("Hour must be between 0 and 23")
    if not (0 <= minute <= 59):
        raise click.BadParameter("Minute must be between 0 and 59")

    schedule_expr = f"{minute} {hour} * * *"

    # Call the main add function
    ctx.invoke(add, schedule=schedule_expr, name=name, description=description)


@schedule.command()
@click.option('--name', '-n', default='weekly_wishlist',
              help='Name for the scheduled job')
@click.option('--description', '-d', default='Weekly wishlist download',
              help='Description for the scheduled job')
@click.option('--day', '-d', 'weekday', default=0, type=int,
              help='Day of week (0=Sunday, 1=Monday, ..., 6=Saturday, default: 0)')
@click.option('--hour', '-h', default=2, type=int,
              help='Hour to run (0-23, default: 2 for 2 AM)')
@click.option('--minute', '-m', default=0, type=int,
              help='Minute to run (0-59, default: 0)')
@click.pass_context
def weekly(ctx, name: str, description: str, weekday: int, hour: int, minute: int):
    """Add a weekly scheduled wishlist download.

    This is a convenience command that sets up weekly execution.

    Examples:
        toolcrate schedule weekly                    # Weekly on Sunday at 2:00 AM
        toolcrate schedule weekly -d 1               # Weekly on Monday at 2:00 AM
        toolcrate schedule weekly -d 6 -h 14         # Weekly on Saturday at 2:00 PM
        toolcrate schedule weekly -n "weekend"       # Custom name

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
    ctx.invoke(add, schedule=schedule_expr, name=name, description=description)


@schedule.command()
@click.option('--name', '-n', default='monthly_wishlist',
              help='Name for the scheduled job')
@click.option('--description', '-d', default='Monthly wishlist download',
              help='Description for the scheduled job')
@click.option('--day', '-d', 'monthday', default=1, type=int,
              help='Day of month (1-31, default: 1 for first day)')
@click.option('--hour', '-h', default=2, type=int,
              help='Hour to run (0-23, default: 2 for 2 AM)')
@click.option('--minute', '-m', default=0, type=int,
              help='Minute to run (0-59, default: 0)')
@click.pass_context
def monthly(ctx, name: str, description: str, monthday: int, hour: int, minute: int):
    """Add a monthly scheduled wishlist download.

    This is a convenience command that sets up monthly execution.

    Examples:
        toolcrate schedule monthly                   # Monthly on 1st at 2:00 AM
        toolcrate schedule monthly -d 15             # Monthly on 15th at 2:00 AM
        toolcrate schedule monthly -d 1 -h 0         # Monthly on 1st at midnight
        toolcrate schedule monthly -n "month_end"    # Custom name
    """
    if not (1 <= monthday <= 31):
        raise click.BadParameter("Day must be between 1 and 31")
    if not (0 <= hour <= 23):
        raise click.BadParameter("Hour must be between 0 and 23")
    if not (0 <= minute <= 59):
        raise click.BadParameter("Minute must be between 0 and 59")

    schedule_expr = f"{minute} {hour} {monthday} * *"

    # Call the main add function
    ctx.invoke(add, schedule=schedule_expr, name=name, description=description)


@schedule.command()
@click.argument('job_name')
@click.pass_context
def remove(ctx, job_name: str):
    """Remove a scheduled job by name.
    
    Example:
        toolcrate schedule remove wishlist_download
    """
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        config = config_manager.config
        
        if 'cron' not in config or 'jobs' not in config['cron']:
            click.echo("No scheduled jobs found.")
            return
        
        jobs = config['cron']['jobs']
        job_found = False
        
        for i, job in enumerate(jobs):
            if job.get('name') == job_name:
                if click.confirm(f"Remove scheduled job '{job_name}'?"):
                    jobs.pop(i)
                    config_manager.update_cron_section(config['cron'])
                    click.echo(f"✅ Removed scheduled job '{job_name}'")
                    
                    # If no jobs left, suggest disabling cron
                    if not jobs:
                        click.echo("💡 No scheduled jobs remaining. Consider running 'toolcrate schedule disable'")
                else:
                    click.echo("Operation cancelled.")
                job_found = True
                break
        
        if not job_found:
            click.echo(f"❌ Job '{job_name}' not found.")
            click.echo("Available jobs:")
            for job in jobs:
                click.echo(f"  - {job.get('name', 'unnamed')}")
    
    except Exception as e:
        logger.error(f"Error removing scheduled job: {e}")
        click.echo(f"❌ Error removing scheduled job: {e}")
        raise click.Abort()


@schedule.command()
@click.pass_context
def disable(ctx):
    """Disable all scheduled downloads.
    
    This disables cron job execution but keeps the job definitions.
    """
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        config = config_manager.config
        
        if 'cron' not in config:
            config['cron'] = {'enabled': False, 'jobs': []}
        
        config['cron']['enabled'] = False
        config_manager.update_cron_section(config['cron'])
        
        click.echo("✅ Disabled all scheduled downloads")
        click.echo("💡 Job definitions are preserved. Use 'toolcrate schedule enable' to re-enable.")
        
    except Exception as e:
        logger.error(f"Error disabling scheduled jobs: {e}")
        click.echo(f"❌ Error disabling scheduled jobs: {e}")
        raise click.Abort()


@schedule.command()
@click.pass_context
def enable(ctx):
    """Enable scheduled downloads.
    
    This enables cron job execution for all defined jobs.
    """
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        config = config_manager.config
        
        if 'cron' not in config:
            config['cron'] = {'enabled': True, 'jobs': []}
        else:
            config['cron']['enabled'] = True

        config_manager.update_cron_section(config['cron'])
        
        jobs = config['cron'].get('jobs', [])
        if jobs:
            click.echo("✅ Enabled scheduled downloads")
            click.echo(f"📋 {len(jobs)} job(s) will be active")
            click.echo("💡 Run 'toolcrate schedule install' to install the cron jobs")
        else:
            click.echo("✅ Enabled scheduled downloads")
            click.echo("💡 No jobs defined yet. Use 'toolcrate schedule add' to create jobs")
        
    except Exception as e:
        logger.error(f"Error enabling scheduled jobs: {e}")
        click.echo(f"❌ Error enabling scheduled jobs: {e}")
        raise click.Abort()


@schedule.command()
@click.pass_context
def list(ctx):
    """List all scheduled jobs."""
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        config = config_manager.config
        
        cron_config = config.get('cron', {})
        enabled = cron_config.get('enabled', False)
        jobs = cron_config.get('jobs', [])
        
        click.echo(f"Scheduled Downloads: {'✅ Enabled' if enabled else '❌ Disabled'}")
        click.echo()
        
        if not jobs:
            click.echo("No scheduled jobs defined.")
            click.echo("Use 'toolcrate schedule add' to create a job.")
            return
        
        click.echo(f"Jobs ({len(jobs)}):")
        for job in jobs:
            name = job.get('name', 'unnamed')
            schedule = job.get('schedule', 'unknown')
            description = job.get('description', 'No description')
            job_enabled = job.get('enabled', True)
            
            status = "✅" if job_enabled else "❌"
            click.echo(f"  {status} {name}")
            click.echo(f"      Schedule: {schedule}")
            click.echo(f"      Description: {description}")
            click.echo()
        
    except Exception as e:
        logger.error(f"Error listing scheduled jobs: {e}")
        click.echo(f"❌ Error listing scheduled jobs: {e}")
        raise click.Abort()


@schedule.command()
@click.pass_context
def install(ctx):
    """Install cron jobs to the system.
    
    This generates and installs the actual cron jobs based on your configuration.
    """
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        config = config_manager.config
        
        cron_config = config.get('cron', {})
        if not cron_config.get('enabled', False):
            click.echo("❌ Scheduled downloads are disabled.")
            click.echo("Run 'toolcrate schedule enable' first.")
            return
        
        jobs = cron_config.get('jobs', [])
        if not jobs:
            click.echo("❌ No scheduled jobs defined.")
            click.echo("Use 'toolcrate schedule add' to create jobs.")
            return
        
        # Generate cron file
        cron_content = generate_cron_file(config_manager, jobs)
        
        # Write to crontabs directory
        cron_dir = config_manager.config_dir / "crontabs"
        cron_dir.mkdir(exist_ok=True)
        cron_file = cron_dir / "toolcrate"
        
        with open(cron_file, 'w') as f:
            f.write(cron_content)
        
        click.echo(f"✅ Generated cron file: {cron_file}")
        click.echo()
        click.echo("To install the cron jobs, choose one option:")
        click.echo()
        click.echo("Option 1 - System-wide (requires sudo):")
        click.echo(f"  sudo cp {cron_file} /etc/cron.d/toolcrate")
        click.echo()
        click.echo("Option 2 - User-specific:")
        click.echo(f"  crontab {cron_file}")
        click.echo()
        click.echo("💡 Use 'crontab -l' to verify installation")
        
    except Exception as e:
        logger.error(f"Error installing cron jobs: {e}")
        click.echo(f"❌ Error installing cron jobs: {e}")
        raise click.Abort()


def generate_cron_file(config_manager: ConfigManager, jobs: List[Dict[str, Any]]) -> str:
    """Generate cron file content from job definitions."""
    lines = [
        "# ToolCrate Scheduled Downloads",
        "# Generated automatically - do not edit manually",
        "# Use 'toolcrate schedule' commands to manage",
        "",
        "# Format: minute hour day month weekday command",
        ""
    ]
    
    # Get project root for command paths
    project_root = config_manager.config_dir.parent
    
    for job in jobs:
        if not job.get('enabled', True):
            continue
            
        name = job.get('name', 'unnamed')
        schedule = job.get('schedule', '0 2 * * *')
        description = job.get('description', '')
        command = job.get('command', 'wishlist')
        
        lines.append(f"# {name}: {description}")
        
        if command == 'wishlist':
            # Wishlist processing command
            cmd = f"cd {project_root} && poetry run python -m toolcrate.wishlist.processor"
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
    config_manager = ctx.obj['config_manager']
    
    try:
        click.echo("🧪 Testing wishlist processing...")
        
        processor = WishlistProcessor(config_manager)
        results = processor.process_all_entries()
        
        click.echo()
        click.echo(f"Test Results: {results['status']}")
        
        if results['status'] == 'completed':
            click.echo(f"✅ Processed: {results['processed']}/{results['total']}")
            click.echo(f"❌ Failed: {results['failed']}/{results['total']}")
            
            if results['failed'] > 0:
                click.echo()
                click.echo("Failed entries:")
                for result in results['results']:
                    if not result['success']:
                        click.echo(f"  - {result['entry']}")
        
        elif results['status'] == 'disabled':
            click.echo("❌ Wishlist processing is disabled in configuration")
        elif results['status'] == 'empty':
            click.echo("📝 No entries found in wishlist file")
            wishlist_path = processor.get_wishlist_file_path()
            click.echo(f"💡 Add entries to: {wishlist_path}")
        
    except Exception as e:
        logger.error(f"Error testing wishlist processing: {e}")
        click.echo(f"❌ Error testing wishlist processing: {e}")
        raise click.Abort()
