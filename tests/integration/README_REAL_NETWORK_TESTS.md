# Real Network Integration Tests

## Overview

The real network integration tests perform **actual downloads** using dummy credentials to verify end-to-end functionality. These tests are **optional** and disabled by default for safety.

## ⚠️ Important Safety Information

### What These Tests Do
- **Attempt real network connections** to Soulseek, YouTube, and SoundCloud
- **Download actual audio files** (small files, limited to <50MB total)
- **Use dummy Soulseek credentials** (`test_user_toolcrate` / `test_pass_123`)
- **Test real URL processing** with actual network requests
- **Validate Docker container execution** with real commands

### What These Tests DON'T Do
- ❌ **Use your personal credentials** - Only dummy/test credentials
- ❌ **Access your accounts** - No real authentication
- ❌ **Download large files** - Size limits enforced
- ❌ **Leave files behind** - Automatic cleanup after tests
- ❌ **Affect your Soulseek account** - Dummy credentials can't connect

## 🚀 How to Run

### Enable Real Network Tests
```bash
# Enable the tests
export TOOLCRATE_REAL_NETWORK_TESTS=1

# Run Python tests
python -m pytest tests/integration/test_real_network_downloads.py -v

# Or run shell script
./tests/test_real_network.sh
```

### Optional Configuration
```bash
# Customize timeouts
export TOOLCRATE_NETWORK_TIMEOUT_SHORT=180  # 3 minutes (default)
export TOOLCRATE_NETWORK_TIMEOUT_LONG=600   # 10 minutes (default)

# Limit download size
export TOOLCRATE_MAX_DOWNLOAD_SIZE=50MB     # Default limit
```

## 🧪 Test Scenarios

### 1. YouTube Download with yt-dlp Fallback
- **URL**: `https://www.youtube.com/watch?v=dQw4w9WgXcQ` (Rick Roll)
- **Expected**: Successful download via yt-dlp
- **Purpose**: Verify YouTube fallback functionality works

### 2. Spotify URL Processing
- **URL**: `https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh` (Mr. Brightside)
- **Expected**: URL recognized, graceful failure with dummy credentials
- **Purpose**: Verify Spotify URL parsing without real authentication

### 3. Mixed Content Processing
- **Content**: YouTube URLs, Spotify URLs, search terms, SoundCloud URLs
- **Expected**: Different processing paths for each content type
- **Purpose**: Verify comprehensive content type handling

### 4. Docker Container Execution
- **Test**: Build and run Docker container with real commands
- **Expected**: Container builds and executes commands
- **Purpose**: Verify Docker integration works end-to-end

## 📊 Expected Results

### Successful Scenarios
- **YouTube downloads**: Should work via yt-dlp fallback
- **SoundCloud downloads**: Should work via yt-dlp fallback
- **Command recognition**: All URLs should be properly parsed
- **Docker execution**: Container should build and run

### Expected Failures (Normal)
- **Spotify downloads**: Will fail gracefully with dummy credentials
- **Soulseek searches**: Will fail to authenticate with dummy credentials
- **Some timeouts**: Expected with network-dependent operations

## 🛡️ Safety Features

### Automatic Cleanup
- All downloaded files are automatically deleted after tests
- Temporary directories are cleaned up
- No persistent changes to your system

### Dummy Credentials
```
Username: test_user_toolcrate
Password: test_pass_123
```
These credentials are fake and cannot access real Soulseek accounts.

### Size Limits
- Individual files limited by `TOOLCRATE_MAX_DOWNLOAD_SIZE`
- Total test downloads typically <10MB
- Tests timeout to prevent runaway downloads

### Public Content Only
- Only uses public playlists and well-known content
- Rick Roll video (famous, stable, public domain)
- Spotify Top 50 Global (public playlist)
- No personal or private content

## 🔧 Troubleshooting

### Tests Skip/Disabled
```
Real network tests disabled. Set TOOLCRATE_REAL_NETWORK_TESTS=1 to enable.
```
**Solution**: Export the environment variable to enable tests.

### Docker Not Available
```
Docker not available
```
**Solution**: Install Docker or skip Docker-specific tests.

### Network Timeouts
```
Download test timed out after X seconds
```
**Solution**: Increase timeout values or check network connection.

### No Files Downloaded
This is often **expected behavior** when:
- Using dummy Soulseek credentials (can't authenticate)
- Network issues prevent downloads
- Content is not available

The tests validate **command structure and processing logic**, not necessarily successful downloads.

## 📈 Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Run Real Network Tests (Optional)
  if: env.ENABLE_NETWORK_TESTS == 'true'
  env:
    TOOLCRATE_REAL_NETWORK_TESTS: 1
    TOOLCRATE_NETWORK_TIMEOUT_SHORT: 120
    TOOLCRATE_MAX_DOWNLOAD_SIZE: 25MB
  run: |
    python -m pytest tests/integration/test_real_network_downloads.py -v
```

### Local Development
```bash
# Quick test (shorter timeouts)
export TOOLCRATE_REAL_NETWORK_TESTS=1
export TOOLCRATE_NETWORK_TIMEOUT_SHORT=60
export TOOLCRATE_NETWORK_TIMEOUT_LONG=180
python -m pytest tests/integration/test_real_network_downloads.py -v
```

## 🎯 When to Use These Tests

### Recommended For
- **Release testing** - Verify end-to-end functionality before releases
- **Development validation** - Test real URL processing changes
- **Docker verification** - Ensure container builds and runs correctly
- **Network debugging** - Diagnose download issues

### Not Recommended For
- **Regular CI/CD** - Too slow and network-dependent for every commit
- **Unit testing** - Use mocked tests for fast feedback
- **Offline development** - Requires network access

## 📝 Test Output Example

```
🧪 Network Test Configuration:
  Enabled: True
  Short timeout: 180s
  Long timeout: 600s
  Max download size: 50MB
  Dummy credentials: test_user_toolcrate
  Test URLs: 8 configured

🎵 Testing YouTube download with yt-dlp fallback...
🔗 Testing URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
📁 Download directory: /tmp/toolcrate_real_test_xyz/downloads
🚀 Running command: toolcrate sldl --download-path /tmp/... --links-file /tmp/...

📤 Command output:
[yt-dlp output showing download progress]

📁 Files in download directory: 3
🎵 Audio files downloaded: 1
  ✅ Rick Astley - Never Gonna Give You Up.mp3 (3.2 MB)

📊 Final Test Statistics:
  Total files created: 5
  Audio files downloaded: 2
  Total download size: 6.8 MB
  Average file size: 3.4 MB
```

## 🤝 Contributing

When adding new real network tests:

1. **Use dummy credentials only**
2. **Add appropriate timeouts**
3. **Include size limits**
4. **Test with public content only**
5. **Add cleanup in tearDown methods**
6. **Document expected behaviors**

The goal is comprehensive testing while maintaining complete safety for all users and environments.
