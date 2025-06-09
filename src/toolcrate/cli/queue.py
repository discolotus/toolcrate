#!/usr/bin/env python3
"""CLI commands for download queue management."""

import click
import logging
from pathlib import Path
from datetime import datetime
from ..config.manager import ConfigManager
from ..queue.processor import QueueProcessor

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def queue(ctx):
    """Manage download queue for individual links.
    
    The download queue processes individual links from config/download-queue.txt,
    downloading each to the downloads directory and removing processed entries.
    This is separate from the wishlist system which downloads to the library.
    """
    # Initialize config manager if not already done
    if 'config_manager' not in ctx.obj:
        ctx.obj['config_manager'] = ConfigManager()


@queue.command()
@click.argument('link')
@click.pass_context
def add(ctx, link):
    """Add a link to the download queue.
    
    LINK can be a playlist URL, album URL, or search term.
    
    Examples:
        toolcrate queue add "https://open.spotify.com/playlist/..."
        toolcrate queue add "https://youtube.com/playlist?list=..."
        toolcrate queue add "Artist - Song Title"
    """
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        queue_config = config_manager.config.get('queue', {})
        
        # Get queue file path
        queue_file_path = Path(config_manager.config_dir) / queue_config.get('file_path', 'download-queue.txt').replace('config/', '')
        
        # Ensure queue file exists
        queue_file_path.parent.mkdir(parents=True, exist_ok=True)
        if not queue_file_path.exists():
            # Create with header comment
            with open(queue_file_path, 'w', encoding='utf-8') as f:
                f.write("# Download Queue\n")
                f.write("# Add playlist URLs, album URLs, or search terms below\n")
                f.write("# Each line will be processed and then removed from this file\n")
                f.write("# Lines starting with # are comments and will be ignored\n\n")
        
        # Add the link to the queue
        with open(queue_file_path, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"# Added {timestamp}\n")
            f.write(f"{link}\n\n")
        
        click.echo(f"✅ Added to download queue: {link}")
        click.echo(f"📁 Queue file: {queue_file_path}")
        click.echo()
        click.echo("The link will be processed during the next queue run.")
        click.echo("To process immediately: toolcrate queue run")
        
    except Exception as e:
        logger.error(f"Error adding link to queue: {e}")
        click.echo(f"❌ Error adding link to queue: {e}")
        raise click.Abort()


@queue.command()
@click.pass_context
def list(ctx):
    """List current entries in the download queue."""
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        processor = QueueProcessor(config_manager)
        
        entries = processor.read_queue_entries()
        
        if not entries:
            click.echo("📭 Download queue is empty")
            click.echo(f"📁 Queue file: {processor.queue_file_path}")
            click.echo()
            click.echo("Add items with: toolcrate queue add <link>")
            return
        
        click.echo(f"📋 Download Queue ({len(entries)} entries)")
        click.echo("=" * 50)
        
        for i, entry in enumerate(entries, 1):
            click.echo(f"{i:2d}. {entry}")
        
        click.echo()
        click.echo(f"📁 Queue file: {processor.queue_file_path}")
        click.echo("To process queue: toolcrate queue run")
        
    except Exception as e:
        logger.error(f"Error listing queue: {e}")
        click.echo(f"❌ Error listing queue: {e}")
        raise click.Abort()


@queue.command()
@click.pass_context
def clear(ctx):
    """Clear all entries from the download queue."""
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        processor = QueueProcessor(config_manager)
        
        entries = processor.read_queue_entries()
        
        if not entries:
            click.echo("📭 Download queue is already empty")
            return
        
        # Confirm before clearing
        click.echo(f"⚠️  This will remove {len(entries)} entries from the download queue:")
        for i, entry in enumerate(entries[:5], 1):  # Show first 5
            click.echo(f"  {i}. {entry}")
        if len(entries) > 5:
            click.echo(f"  ... and {len(entries) - 5} more")
        
        if not click.confirm("\nAre you sure you want to clear the queue?"):
            click.echo("❌ Queue clear cancelled")
            return
        
        # Clear the queue file (keep header comments)
        with open(processor.queue_file_path, 'w', encoding='utf-8') as f:
            f.write("# Download Queue\n")
            f.write("# Add playlist URLs, album URLs, or search terms below\n")
            f.write("# Each line will be processed and then removed from this file\n")
            f.write("# Lines starting with # are comments and will be ignored\n\n")
        
        click.echo(f"✅ Cleared {len(entries)} entries from download queue")
        
    except Exception as e:
        logger.error(f"Error clearing queue: {e}")
        click.echo(f"❌ Error clearing queue: {e}")
        raise click.Abort()


@queue.command()
@click.pass_context
def run(ctx):
    """Process all entries in the download queue immediately.
    
    This runs the queue processor once to process all current entries.
    Entries are downloaded to the downloads directory and removed from the queue.
    """
    config_manager = ctx.obj['config_manager']
    
    try:
        click.echo("🚀 Processing download queue...")
        
        processor = QueueProcessor(config_manager)
        results = processor.process_all_entries()
        
        click.echo()
        click.echo(f"Queue Processing Results: {results['status']}")
        
        if results['status'] == 'completed':
            click.echo(f"✅ Processed: {results['processed']}/{results['total']}")
            click.echo(f"❌ Failed: {results['failed']}/{results['total']}")
            
            if results['failed'] > 0:
                click.echo()
                click.echo("Failed entries:")
                for result in results['results']:
                    if not result['success']:
                        click.echo(f"  - {result['entry']}")
        elif results['status'] == 'empty':
            click.echo("📭 No entries found in download queue")
        elif results['status'] == 'disabled':
            click.echo("❌ Queue processing is disabled in configuration")
        elif results['status'] == 'locked':
            click.echo("🔒 Queue processing is already running")
        
    except Exception as e:
        logger.error(f"Error processing queue: {e}")
        click.echo(f"❌ Error processing queue: {e}")
        raise click.Abort()


@queue.command()
@click.pass_context
def status(ctx):
    """Show queue status and configuration."""
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        processor = QueueProcessor(config_manager)
        queue_config = config_manager.config.get('queue', {})
        
        click.echo("📊 Download Queue Status")
        click.echo("=" * 40)
        
        # Queue configuration
        enabled = queue_config.get('enabled', True)
        click.echo(f"Status: {'✅ Enabled' if enabled else '❌ Disabled'}")
        click.echo(f"Queue file: {processor.queue_file_path}")
        click.echo(f"Download directory: {queue_config.get('download_dir', '/data/downloads')}")
        
        # Check if queue file exists and count entries
        if processor.queue_file_path.exists():
            entries = processor.read_queue_entries()
            click.echo(f"Current entries: {len(entries)}")
            
            if entries:
                click.echo()
                click.echo("Next 3 entries to process:")
                for i, entry in enumerate(entries[:3], 1):
                    click.echo(f"  {i}. {entry}")
                if len(entries) > 3:
                    click.echo(f"  ... and {len(entries) - 3} more")
        else:
            click.echo("Current entries: 0 (queue file not found)")
        
        # Check lock status
        if processor.lock_file_path.exists():
            click.echo()
            click.echo("🔒 Queue processing lock is active")
            try:
                with open(processor.lock_file_path, 'r') as f:
                    lock_info = f.read().strip()
                click.echo(f"Lock info: {lock_info}")
            except:
                pass
        
        # Backup file info
        if queue_config.get('backup_processed', True) and processor.backup_file_path.exists():
            try:
                with open(processor.backup_file_path, 'r') as f:
                    backup_lines = f.readlines()
                processed_count = len([line for line in backup_lines if line.strip() and not line.startswith('#')])
                click.echo(f"Processed entries (backed up): {processed_count}")
            except:
                pass
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        click.echo(f"❌ Error getting queue status: {e}")
        raise click.Abort()


@queue.command()
@click.pass_context
def enable(ctx):
    """Enable queue processing."""
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        config = config_manager.config
        
        if 'queue' not in config:
            config['queue'] = {}
        
        config['queue']['enabled'] = True
        
        # Update configuration
        config_manager.update_cron_section(config.get('cron', {}))
        
        click.echo("✅ Queue processing enabled")
        click.echo("To schedule automatic processing: toolcrate schedule add-queue")
        
    except Exception as e:
        logger.error(f"Error enabling queue: {e}")
        click.echo(f"❌ Error enabling queue: {e}")
        raise click.Abort()


@queue.command()
@click.pass_context
def disable(ctx):
    """Disable queue processing."""
    config_manager = ctx.obj['config_manager']
    
    try:
        config_manager.load_config()
        config = config_manager.config
        
        if 'queue' not in config:
            config['queue'] = {}
        
        config['queue']['enabled'] = False
        
        # Update configuration
        config_manager.update_cron_section(config.get('cron', {}))
        
        click.echo("✅ Queue processing disabled")
        click.echo("Scheduled queue processing will be skipped until re-enabled")
        
    except Exception as e:
        logger.error(f"Error disabling queue: {e}")
        click.echo(f"❌ Error disabling queue: {e}")
        raise click.Abort()
