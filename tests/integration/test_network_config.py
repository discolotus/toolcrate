"""Configuration and utilities for real network integration tests."""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any


class NetworkTestConfig:
    """Configuration for real network integration tests."""
    
    def __init__(self):
        """Initialize network test configuration."""
        self.enabled = os.environ.get('TOOLCRATE_REAL_NETWORK_TESTS') == '1'
        self.timeout_short = int(os.environ.get('TOOLCRATE_NETWORK_TIMEOUT_SHORT', '180'))  # 3 minutes
        self.timeout_long = int(os.environ.get('TOOLCRATE_NETWORK_TIMEOUT_LONG', '600'))   # 10 minutes
        self.max_download_size = os.environ.get('TOOLCRATE_MAX_DOWNLOAD_SIZE', '50MB')
        
        # Dummy credentials for testing
        self.dummy_credentials = {
            'username': 'test_user_toolcrate',
            'password': 'test_pass_123'
        }
        
        # Test URLs - carefully selected for testing
        self.test_urls = {
            # YouTube URLs that should work with yt-dlp
            'youtube_short': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',  # Rick Roll - famous, stable
            'youtube_music': 'https://music.youtube.com/watch?v=dQw4w9WgXcQ',  # Same but YouTube Music
            
            # Spotify URLs (will likely fail with dummy credentials, but should be processed)
            'spotify_track': 'https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh',  # Mr. Brightside
            'spotify_album': 'https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy',  # Hot Fuss album
            
            # SoundCloud (public tracks)
            'soundcloud_track': 'https://soundcloud.com/rick-astley-official/never-gonna-give-you-up-4',
            
            # Search terms that should work on Soulseek (if credentials were real)
            'search_popular': 'Rick Astley - Never Gonna Give You Up',
            'search_common': 'The Beatles - Hey Jude',
        }
        
        # Expected behaviors for different URL types
        self.expected_behaviors = {
            'youtube': {
                'should_use_ytdlp': True,
                'should_download': True,
                'timeout': self.timeout_short,
                'expected_formats': ['.mp3', '.m4a', '.webm']
            },
            'spotify': {
                'should_use_ytdlp': False,
                'should_download': False,  # Not with dummy credentials
                'timeout': self.timeout_short,
                'expected_errors': ['login', 'authentication', 'credentials']
            },
            'soundcloud': {
                'should_use_ytdlp': True,
                'should_download': True,
                'timeout': self.timeout_short,
                'expected_formats': ['.mp3', '.m4a']
            },
            'search': {
                'should_use_ytdlp': False,
                'should_download': False,  # Not with dummy credentials
                'timeout': self.timeout_long,
                'expected_errors': ['login', 'authentication', 'no results']
            }
        }

    def create_test_sldl_config(self, download_dir: Path) -> Path:
        """Create a test sldl.conf file with dummy credentials.
        
        Args:
            download_dir: Directory where downloads should be saved
            
        Returns:
            Path to the created config file
        """
        config_content = f"""# Test SLDL Configuration
# Generated for integration testing with dummy credentials
# DO NOT USE IN PRODUCTION

# Dummy Soulseek credentials (will not work for real downloads)
username = {self.dummy_credentials['username']}
password = {self.dummy_credentials['password']}

# Download settings
path = {download_dir}
fast-search = true
search-timeout = {self.timeout_short // 3}
max-stale-time = 300

# Prefer smaller files for testing
min-bitrate = 128
max-bitrate = 320
pref-format = mp3
max-track-results = 3

# Enable yt-dlp for YouTube/SoundCloud fallback
yt-dlp = true
yt-dlp-args = --audio-quality 5 --extract-flat false --max-filesize {self.max_download_size}

# Conservative settings for testing
concurrent-processes = 1
album-parallel-search = false
skip-existing = true

# Shorter timeouts to prevent hanging
max-search-time = {self.timeout_short // 6}
"""
        
        config_file = download_dir.parent / "sldl.conf"
        config_file.write_text(config_content)
        return config_file

    def create_test_links_file(self, content_type: str, temp_dir: Path) -> Path:
        """Create a test links file with specific content type.
        
        Args:
            content_type: Type of content ('youtube', 'spotify', 'mixed', etc.)
            temp_dir: Temporary directory for the file
            
        Returns:
            Path to the created links file
        """
        links_file = temp_dir / f"test_{content_type}.txt"
        
        if content_type == 'youtube':
            content = f"""# YouTube test links
{self.test_urls['youtube_short']}
"""
        elif content_type == 'spotify':
            content = f"""# Spotify test links  
{self.test_urls['spotify_track']}
"""
        elif content_type == 'soundcloud':
            content = f"""# SoundCloud test links
{self.test_urls['soundcloud_track']}
"""
        elif content_type == 'search':
            content = f"""# Search term test
{self.test_urls['search_popular']}
"""
        elif content_type == 'mixed':
            content = f"""# Mixed content test file
# YouTube (should work with yt-dlp)
{self.test_urls['youtube_short']}

# Search term (will attempt Soulseek)
{self.test_urls['search_popular']}

# Spotify (will fail gracefully with dummy credentials)
{self.test_urls['spotify_track']}

# SoundCloud (should work with yt-dlp)
{self.test_urls['soundcloud_track']}
"""
        else:
            raise ValueError(f"Unknown content type: {content_type}")
        
        links_file.write_text(content)
        return links_file

    def get_expected_behavior(self, url_or_type: str) -> Dict[str, Any]:
        """Get expected behavior for a URL or content type.
        
        Args:
            url_or_type: URL string or content type
            
        Returns:
            Dictionary of expected behaviors
        """
        if 'youtube.com' in url_or_type or 'youtu.be' in url_or_type:
            return self.expected_behaviors['youtube']
        elif 'spotify.com' in url_or_type:
            return self.expected_behaviors['spotify']
        elif 'soundcloud.com' in url_or_type:
            return self.expected_behaviors['soundcloud']
        elif url_or_type in self.expected_behaviors:
            return self.expected_behaviors[url_or_type]
        else:
            # Default to search behavior
            return self.expected_behaviors['search']

    def is_success_expected(self, url_or_type: str) -> bool:
        """Check if successful download is expected for this URL/type.
        
        Args:
            url_or_type: URL string or content type
            
        Returns:
            True if download success is expected
        """
        behavior = self.get_expected_behavior(url_or_type)
        return behavior.get('should_download', False)

    def should_use_ytdlp(self, url_or_type: str) -> bool:
        """Check if yt-dlp should be used for this URL/type.
        
        Args:
            url_or_type: URL string or content type
            
        Returns:
            True if yt-dlp should be used
        """
        behavior = self.get_expected_behavior(url_or_type)
        return behavior.get('should_use_ytdlp', False)

    def get_timeout(self, url_or_type: str) -> int:
        """Get appropriate timeout for this URL/type.
        
        Args:
            url_or_type: URL string or content type
            
        Returns:
            Timeout in seconds
        """
        behavior = self.get_expected_behavior(url_or_type)
        return behavior.get('timeout', self.timeout_short)

    @staticmethod
    def skip_if_disabled():
        """Decorator to skip tests if real network tests are disabled."""
        def decorator(test_func):
            def wrapper(self, *args, **kwargs):
                if not getattr(self, 'config', NetworkTestConfig()).enabled:
                    self.skipTest("Real network tests disabled. Set TOOLCRATE_REAL_NETWORK_TESTS=1 to enable.")
                return test_func(self, *args, **kwargs)
            return wrapper
        return decorator

    def print_test_info(self):
        """Print information about the test configuration."""
        print(f"\n🧪 Network Test Configuration:")
        print(f"  Enabled: {self.enabled}")
        print(f"  Short timeout: {self.timeout_short}s")
        print(f"  Long timeout: {self.timeout_long}s")
        print(f"  Max download size: {self.max_download_size}")
        print(f"  Dummy credentials: {self.dummy_credentials['username']}")
        print(f"  Test URLs: {len(self.test_urls)} configured")


# Global configuration instance
network_config = NetworkTestConfig()


def requires_network_tests(test_func):
    """Decorator to skip tests if real network tests are disabled."""
    def wrapper(*args, **kwargs):
        if not network_config.enabled:
            import unittest
            raise unittest.SkipTest("Real network tests disabled. Set TOOLCRATE_REAL_NETWORK_TESTS=1 to enable.")
        return test_func(*args, **kwargs)
    return wrapper
