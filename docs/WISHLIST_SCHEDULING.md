# Wishlist & Scheduled Downloads

ToolCrate supports automated wishlist downloading with customizable scheduling. This feature allows you to maintain a list of playlists and tracks that will be automatically downloaded on a schedule, with special configuration optimized for quality and completeness.

## Overview

The wishlist system consists of:
- **Wishlist File**: `config/wishlist.txt` - A simple text file with URLs/search terms
- **Wishlist Configuration**: Special settings in `toolcrate.yaml` for wishlist downloads
- **Schedule Management**: CLI commands to manage cron jobs for automated processing
- **Quality-Focused Downloads**: Downloads go to `data/library` with enhanced quality settings

## Quick Start

### 1. Add Items to Wishlist

Edit `config/wishlist.txt` and add playlist URLs or search terms:

```
# Spotify playlists
https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M

# YouTube playlists  
https://youtube.com/playlist?list=PLrAl6rYgs4IvGFBDEaVGFXt6k2GiOFWpX

# Search terms
"Daft Punk - Get Lucky"
artist:"Miles Davis" album:"Kind of Blue"
```

### 2. Test Wishlist Processing

```bash
# Test without scheduling
make wishlist-test
# or
toolcrate schedule test
```

### 3. Set Up Scheduling

```bash
# Easy way - use convenience commands
toolcrate schedule daily                    # Daily at 2 AM
toolcrate schedule hourly                   # Every hour
toolcrate schedule weekly                   # Weekly on Sunday at 2 AM

# Or add custom schedule
toolcrate schedule add -s "0 2 * * *" -n "daily_wishlist" -d "Daily wishlist download"

# Enable scheduling
toolcrate schedule enable

# Install cron jobs
toolcrate schedule install
```

## Wishlist Configuration

The wishlist system uses special configuration in `toolcrate.yaml`:

```yaml
wishlist:
  enabled: true
  file_path: "config/wishlist.txt"
  download_dir: "/path/to/data/library"          # Downloads go to library, not downloads
  index_in_playlist_folder: true                 # Index files stored in each playlist folder
  check_existing_for_better_quality: true       # Re-check existing files for upgrades
  slower_search: true                            # Allow thorough searches
  
  settings:
    skip_existing: false                         # Always check files even if they exist
    skip_check_pref_cond: true                  # Continue searching for preferred quality
    desperate_search: true                       # Use relaxed matching if needed
    use_ytdlp: true                             # Enable yt-dlp fallback
    search_timeout: 12000                       # Longer timeout (12 seconds)
    max_retries_per_track: 50                   # More retries for wishlist items
    fast_search: false                          # Disable fast search for quality
    
    preferred_conditions:
      formats: ["flac", "wav", "alac", "mp3"]   # Prefer lossless formats
      min_bitrate: 320                          # High quality minimum
      max_sample_rate: 192000                   # Support high-res audio
```

## Schedule Management Commands

### Convenience Commands (Recommended)

```bash
# Easy scheduling with sensible defaults
toolcrate schedule daily                    # Daily at 2:00 AM
toolcrate schedule hourly                   # Every hour at minute 0
toolcrate schedule weekly                   # Weekly on Sunday at 2:00 AM
toolcrate schedule monthly                  # Monthly on 1st at 2:00 AM

# Customize timing
toolcrate schedule daily -h 14              # Daily at 2:00 PM
toolcrate schedule hourly -m 30             # Every hour at minute 30
toolcrate schedule weekly -d 1 -h 9         # Weekly on Monday at 9:00 AM
toolcrate schedule monthly -d 15            # Monthly on 15th at 2:00 AM

# Custom names and descriptions
toolcrate schedule daily -n "morning_sync" -d "Morning wishlist sync"
toolcrate schedule hourly -n "frequent" -d "Frequent updates"
```

### Manual Scheduling (Advanced)

```bash
# Custom cron expressions for complex schedules
toolcrate schedule add -s "0 2 * * *" -n "daily_wishlist"      # Daily at 2 AM
toolcrate schedule add -s "0 2 * * 0" -n "weekly_wishlist"     # Weekly on Sunday at 2 AM
toolcrate schedule add -s "0 */6 * * *" -n "frequent_wishlist" # Every 6 hours
toolcrate schedule add -s "*/30 * * * *" -n "very_frequent"    # Every 30 minutes
```

### Manage Jobs

```bash
# List all scheduled jobs
toolcrate schedule list

# Enable/disable scheduling
toolcrate schedule enable
toolcrate schedule disable

# Remove a specific job
toolcrate schedule remove daily_wishlist

# Install cron jobs to system
toolcrate schedule install
```

## How It Works

### Wishlist Processing

1. **Configuration Generation**: Creates `config/sldl-wishlist.conf` with wishlist-specific settings
2. **File Reading**: Processes each line in `config/wishlist.txt`
3. **Command Execution**: Runs `sldl` in Docker container for each entry
4. **Quality Focus**: Uses settings optimized for finding the best available quality

### Key Differences from Regular Downloads

| Aspect | Regular Downloads | Wishlist Downloads |
|--------|------------------|-------------------|
| **Destination** | `data/downloads` | `data/library` |
| **Index Location** | Global index | Per-playlist folder |
| **Skip Existing** | Yes | No (checks for better quality) |
| **Search Speed** | Fast | Thorough |
| **Retries** | 30 | 50 |
| **Timeout** | 6 seconds | 12 seconds |
| **Quality Priority** | Balanced | Lossless preferred |

### Cron Integration

The system generates standard cron files that can be installed system-wide or per-user:

```bash
# System-wide installation (requires sudo)
sudo cp config/crontabs/toolcrate /etc/cron.d/toolcrate

# User-specific installation
crontab config/crontabs/toolcrate
```

## Supported Wishlist Formats

### Playlist URLs
- Spotify: `https://open.spotify.com/playlist/ID`
- YouTube: `https://youtube.com/playlist?list=ID`
- Apple Music: `https://music.apple.com/playlist/ID`

### Search Terms
- Simple: `"Artist - Song Title"`
- Artist search: `artist:"Artist Name"`
- Album search: `album:"Album Name"`
- Combined: `artist:"Artist" album:"Album"`
- With format: `"Song Title" format=flac`

### Comments and Organization
```
# This is a comment
# You can organize your wishlist with comments

# Weekly discoveries
https://open.spotify.com/playlist/discover-weekly

# Favorite albums to upgrade
artist:"Pink Floyd" album:"Dark Side of the Moon"
artist:"Miles Davis" album:"Kind of Blue"
```

## Make Commands

```bash
# Test wishlist processing
make wishlist-test

# Run wishlist processing once
make wishlist-run

# Generate wishlist-specific config
make config-generate-wishlist-sldl
```

## Troubleshooting

### Common Issues

1. **No entries processed**: Check that `config/wishlist.txt` has non-comment lines
2. **Docker errors**: Ensure Docker is running and `sldl` container exists
3. **Permission errors**: Check file permissions on config directory
4. **Cron not running**: Verify cron installation with `crontab -l`

### Debug Commands

```bash
# Test configuration
toolcrate schedule test

# Check configuration
make config-validate

# View generated config
cat config/sldl-wishlist.conf

# Check cron file
cat config/crontabs/toolcrate
```

### Logs

Wishlist processing logs are written to the same location as regular sldl logs:
- Log file: `logs/sldl.log`
- Docker logs: `docker logs sldl`

## Advanced Usage

### Convenience Commands Reference

All convenience commands support customization options:

#### Daily Scheduling
```bash
toolcrate schedule daily                     # Daily at 2:00 AM (default)
toolcrate schedule daily -h 14               # Daily at 2:00 PM
toolcrate schedule daily -h 9 -m 30          # Daily at 9:30 AM
toolcrate schedule daily -n "morning_sync"   # Custom name
```

#### Hourly Scheduling
```bash
toolcrate schedule hourly                    # Every hour at minute 0 (default)
toolcrate schedule hourly -m 15              # Every hour at minute 15
toolcrate schedule hourly -n "frequent"      # Custom name
```

#### Weekly Scheduling
```bash
toolcrate schedule weekly                    # Weekly on Sunday at 2:00 AM (default)
toolcrate schedule weekly -d 1               # Weekly on Monday at 2:00 AM
toolcrate schedule weekly -d 5 -h 18         # Weekly on Friday at 6:00 PM
toolcrate schedule weekly -n "weekend"       # Custom name

# Day codes: 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
```

#### Monthly Scheduling
```bash
toolcrate schedule monthly                   # Monthly on 1st at 2:00 AM (default)
toolcrate schedule monthly -d 15             # Monthly on 15th at 2:00 AM
toolcrate schedule monthly -d 1 -h 0         # Monthly on 1st at midnight
toolcrate schedule monthly -n "month_end"    # Custom name
```

### Custom Schedules

For complex schedules not covered by convenience commands, use [crontab.guru](https://crontab.guru/) to create custom schedules:

```bash
# Every 30 minutes
toolcrate schedule add -s "*/30 * * * *" -n "frequent"

# Weekdays at 9 AM
toolcrate schedule add -s "0 9 * * 1-5" -n "weekday_morning"

# Every 6 hours
toolcrate schedule add -s "0 */6 * * *" -n "six_hourly"

# Twice daily (6 AM and 6 PM)
toolcrate schedule add -s "0 6,18 * * *" -n "twice_daily"
```

### Multiple Wishlist Files

You can create multiple wishlist configurations by modifying `toolcrate.yaml`:

```yaml
wishlist:
  file_path: "config/priority-wishlist.txt"
  # ... other settings
```

### Integration with Existing Workflows

The wishlist system integrates with:
- Docker containers (uses existing `sldl` container)
- Configuration management (extends `toolcrate.yaml`)
- Mount points (respects existing volume mounts)
- Quality profiles (can use existing profiles)
