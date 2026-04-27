# Download Queue

ToolCrate supports a download queue system for processing individual links that are automatically removed after processing. This is separate from the wishlist system and is designed for one-time downloads that go to the downloads directory.

## Overview

The download queue system consists of:
- **Queue File**: `config/download-queue.txt` - A simple text file with URLs/search terms
- **Queue Configuration**: Settings in `toolcrate.yaml` for queue processing
- **CLI Commands**: Commands to manage the queue (`toolcrate queue`)
- **Scheduling**: Integration with cron system for automatic processing
- **Downloads Directory**: Downloads go to `data/downloads` (not `data/library` like wishlist)

## Key Differences from Wishlist

| Feature | Wishlist | Download Queue |
|---------|----------|----------------|
| **Purpose** | Library building with quality focus | One-time downloads |
| **Destination** | `data/library` | `data/downloads` |
| **Processing** | Keeps entries, processes repeatedly | Removes entries after processing |
| **Quality Settings** | Optimized for best quality | Standard download settings |
| **Scheduling** | Typically daily/hourly | Typically hourly (offset) |

## Quick Start

### 1. Add Items to Queue

```bash
# Add individual links
toolcrate queue add "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
toolcrate queue add "https://youtube.com/playlist?list=PLrAl6rYgs4IvGFBDEaVGFXt6k2GiOFWpX"
toolcrate queue add "Artist - Song Title"

# Or edit the file directly
nano config/download-queue.txt
```

### 2. Process Queue

```bash
# Process immediately
toolcrate queue run

# Test without scheduling
toolcrate schedule test-queue
```

### 3. Set Up Automatic Processing

```bash
# Add hourly queue processing (30 minutes past each hour)
toolcrate schedule add-queue

# Enable scheduling
toolcrate schedule enable

# Install cron jobs
toolcrate schedule install
```

## Queue Management Commands

### Adding Items

```bash
# Add a Spotify playlist
toolcrate queue add "https://open.spotify.com/playlist/..."

# Add a YouTube playlist
toolcrate queue add "https://youtube.com/playlist?list=..."

# Add a search term
toolcrate queue add "Artist Name - Song Title"
toolcrate queue add 'artist:"Miles Davis" album:"Kind of Blue"'
```

### Viewing Queue

```bash
# List current queue entries
toolcrate queue list

# Show queue status and configuration
toolcrate queue status
```

### Processing Queue

```bash
# Process all entries immediately
toolcrate queue run

# Test queue processing
toolcrate schedule test-queue
```

### Queue Control

```bash
# Clear all entries from queue
toolcrate queue clear

# Enable/disable queue processing
toolcrate queue enable
toolcrate queue disable
```

## Configuration

The queue system is configured in `toolcrate.yaml`:

```yaml
queue:
  enabled: true
  file_path: "config/download-queue.txt"              # Path to download queue file
  download_dir: "/path/to/data/downloads"             # Download to downloads directory
  lock_file: "config/.queue-lock"                     # Lock file to prevent concurrent processing
  backup_processed: true                             # Keep backup of processed entries
  backup_file: "config/download-queue-processed.txt" # Backup file for processed entries

  # Queue-specific slsk-batchdl settings (use standard download settings)
  settings:
    skip_existing: true                               # Skip files that already exist
    desperate_search: false                          # Use standard matching
    use_ytdlp: true                                  # Enable yt-dlp fallback
    search_timeout: 6000                             # Standard timeout
    max_retries_per_track: 30                        # Standard retry count
    fast_search: true                                # Enable fast search for queue
```

## Scheduling

### Automatic Processing

The queue system integrates with ToolCrate's scheduling system:

```bash
# Add hourly queue processing (recommended)
toolcrate schedule add-queue

# Or add custom schedule
toolcrate schedule add -s "30 * * * *" -n "hourly_queue" -d "Hourly download queue processing"
```

### Conflict Prevention

Queue processing is automatically offset from wishlist processing to prevent Soulseek connection conflicts:

- **Wishlist**: Typically runs on the hour (e.g., 2:00 AM, 3:00 AM)
- **Queue**: Runs at 30 minutes past the hour (e.g., 2:30 AM, 3:30 AM)

This ensures only one process connects to Soulseek at a time.

## How It Works

### Processing Flow

1. **Lock Acquisition**: Prevents concurrent processing
2. **File Reading**: Reads non-comment lines from `config/download-queue.txt`
3. **Command Execution**: Runs `toolcrate sldl <link>` for each entry
4. **Success Handling**: Backs up and removes successfully processed entries
5. **Error Handling**: Logs failures but continues processing
6. **Lock Release**: Cleans up lock file

### Entry Removal

Successfully processed entries are:
1. **Backed up** to `config/download-queue-processed.txt` (if enabled)
2. **Removed** from `config/download-queue.txt`
3. **Logged** with timestamps

Failed entries remain in the queue for retry on next run.

## File Formats

### Queue File Format

```
# Download Queue
# Add playlist URLs, album URLs, or search terms below
# Each line will be processed and then removed from this file
# Lines starting with # are comments and will be ignored

# Added 2024-01-15 10:30:00
https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M

# Added 2024-01-15 10:31:00
"Artist Name - Song Title"
```

### Backup File Format

```
# Processed at 2024-01-15T10:35:00
https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M

# Processed at 2024-01-15T10:36:00
"Artist Name - Song Title"
```

## Troubleshooting

### Common Issues

1. **Queue not processing**: Check if queue is enabled and scheduled
2. **Lock file errors**: Remove `config/.queue-lock` if stuck
3. **Docker errors**: Ensure Docker is running and `sldl` container exists
4. **Permission errors**: Check file permissions on config directory

### Debug Commands

```bash
# Check queue status
toolcrate queue status

# Test queue processing
toolcrate schedule test-queue

# View queue configuration
cat config/toolcrate.yaml | grep -A 20 "queue:"

# Check for lock file
ls -la config/.queue-lock

# View processed entries backup
cat config/download-queue-processed.txt
```

### Logs

Queue processing logs are written to:
- **Application logs**: `logs/app.log`
- **Download logs**: `data/sldl.log`

Use `toolcrate wishlist-run logs` to view recent activity.

## Integration with Other Features

### With Wishlist System

- Queue and wishlist can run simultaneously with different schedules
- Both use the same Docker container but with different configurations
- Queue uses standard `sldl.conf`, wishlist uses `sldl-wishlist.conf`

### With Scheduling System

- Queue jobs appear in `toolcrate schedule list`
- Can be enabled/disabled with other scheduled jobs
- Uses same cron installation process

### With Docker Integration

- Queue processing uses the same `sldl` Docker container
- Automatically regenerates configuration before processing
- Supports `--build` flag for container rebuilding
