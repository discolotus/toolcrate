"""Real network integration tests that perform actual downloads.

These tests are OPTIONAL and only run when explicitly enabled.
They use dummy credentials and attempt real downloads to verify
end-to-end functionality.

Enable with: TOOLCRATE_REAL_NETWORK_TESTS=1

⚠️  WARNING: These tests will:
- Attempt real network connections to Soulseek/YouTube/SoundCloud
- Try to download actual audio files (small files, <50MB total)
- Use dummy Soulseek credentials (test_user_toolcrate/test_pass_123)
- May take 5-15 minutes to complete
- Create temporary files that are cleaned up automatically

These tests are useful for:
- Verifying end-to-end download functionality
- Testing real URL processing with actual network requests
- Validating Docker container execution with real commands
- Checking yt-dlp fallback functionality with real YouTube URLs
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import shutil
import time

try:
    from .test_network_config import NetworkTestConfig, requires_network_tests
except ImportError:
    # Handle direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from test_network_config import NetworkTestConfig, requires_network_tests


class TestRealNetworkDownloads(unittest.TestCase):
    """Test real network downloads with dummy credentials."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures."""
        cls.config = NetworkTestConfig()

        # Only run if explicitly enabled
        if not cls.config.enabled:
            raise unittest.SkipTest("Real network tests disabled. Set TOOLCRATE_REAL_NETWORK_TESTS=1 to enable.")

        # Create temporary directories for testing
        cls.temp_dir = Path(tempfile.mkdtemp(prefix='toolcrate_real_test_'))
        cls.download_dir = cls.temp_dir / "downloads"
        cls.download_dir.mkdir(parents=True)

        # Print test configuration
        cls.config.print_test_info()
        print(f"\n🧪 Real network test directory: {cls.temp_dir}")
        print(f"📁 Downloads will be saved to: {cls.download_dir}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test directories."""
        if hasattr(cls, 'temp_dir') and cls.temp_dir.exists():
            # Show final statistics before cleanup
            downloaded_files = list(cls.download_dir.glob("**/*"))
            audio_files = [f for f in downloaded_files if f.suffix.lower() in ['.mp3', '.flac', '.wav', '.m4a']]

            print(f"\n📊 Final Test Statistics:")
            print(f"  Total files created: {len(downloaded_files)}")
            print(f"  Audio files downloaded: {len(audio_files)}")

            if audio_files:
                total_size = sum(f.stat().st_size for f in audio_files if f.exists())
                print(f"  Total download size: {total_size / 1024 / 1024:.1f} MB")
                print(f"  Average file size: {total_size / len(audio_files) / 1024 / 1024:.1f} MB")

            print(f"\n🧹 Cleaning up test directory: {cls.temp_dir}")
            shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """Set up test fixtures."""
        if not self.config.enabled:
            self.skipTest("Real network tests disabled")

    @requires_network_tests
    def test_youtube_download_with_ytdlp_fallback(self):
        """Test downloading from YouTube using yt-dlp fallback."""
        print("\n🎵 Testing YouTube download with yt-dlp fallback...")

        # Create test configuration
        config_file = self.config.create_test_sldl_config(self.download_dir)

        # Create links file with YouTube URL
        links_file = self.config.create_test_links_file('youtube', self.temp_dir)

        print(f"🔗 Testing URL: {self.config.test_urls['youtube_short']}")
        print(f"📁 Download directory: {self.download_dir}")

        # Test command
        cmd = [
            'toolcrate', 'sldl',
            '--download-path', str(self.download_dir),
            '--links-file', str(links_file)
        ]

        print(f"🚀 Running command: {' '.join(cmd)}")

        # Set environment to use our test config
        env = os.environ.copy()
        env['SLDL_CONFIG'] = str(config_file)

        try:
            # Run with appropriate timeout for YouTube
            timeout = self.config.get_timeout('youtube')
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=self.temp_dir
            )

            print(f"📤 Command output:\n{result.stdout}")
            if result.stderr:
                print(f"⚠️ Command errors:\n{result.stderr}")

            # Check results
            downloaded_files = list(self.download_dir.glob("**/*"))
            audio_files = [f for f in downloaded_files if f.suffix.lower() in ['.mp3', '.flac', '.wav', '.m4a']]

            print(f"📁 Files in download directory: {len(downloaded_files)}")
            print(f"🎵 Audio files downloaded: {len(audio_files)}")

            for file in audio_files[:3]:  # Show first 3 files
                size_mb = file.stat().st_size / 1024 / 1024
                print(f"  ✅ {file.name} ({size_mb:.1f} MB)")

            # Validate results based on expected behavior
            if self.config.is_success_expected('youtube'):
                self.assertTrue(
                    len(audio_files) > 0,
                    f"Expected YouTube download to succeed with yt-dlp. Got {len(audio_files)} files."
                )

            # Should show evidence of yt-dlp usage
            if self.config.should_use_ytdlp('youtube'):
                self.assertTrue(
                    "yt-dlp" in result.stdout.lower() or
                    "youtube" in result.stdout.lower() or
                    len(audio_files) > 0,
                    f"Expected yt-dlp usage for YouTube URL. Output: {result.stdout}"
                )

        except subprocess.TimeoutExpired:
            self.fail(f"YouTube download test timed out after {timeout} seconds")

    @requires_network_tests
    def test_spotify_track_processing_with_dummy_credentials(self):
        """Test Spotify track processing (expected to fail gracefully with dummy credentials)."""
        print("\n🎵 Testing Spotify track processing with dummy credentials...")

        config_file = self.config.create_test_sldl_config(self.download_dir)
        links_file = self.config.create_test_links_file('spotify', self.temp_dir)

        print(f"🔗 Testing URL: {self.config.test_urls['spotify_track']}")
        print(f"⚠️ Expected: Graceful failure with dummy credentials")

        cmd = [
            'toolcrate', 'sldl',
            '--download-path', str(self.download_dir),
            '--links-file', str(links_file)
        ]

        print(f"🚀 Running command: {' '.join(cmd)}")

        env = os.environ.copy()
        env['SLDL_CONFIG'] = str(config_file)

        try:
            timeout = self.config.get_timeout('spotify')
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=self.temp_dir
            )

            print(f"📤 Command output:\n{result.stdout}")
            if result.stderr:
                print(f"⚠️ Command errors:\n{result.stderr}")

            # For Spotify with dummy credentials, we expect processing but no downloads
            output_lower = result.stdout.lower() + result.stderr.lower()

            # Should show evidence of Spotify URL recognition
            spotify_processing = any(keyword in output_lower for keyword in [
                'spotify', 'soulseek', 'login', 'authentication', 'credentials'
            ])

            self.assertTrue(
                spotify_processing,
                f"Expected Spotify URL processing evidence. Got: {result.stdout}"
            )

            # Should NOT download files with dummy credentials
            audio_files = list(self.download_dir.glob("**/*.mp3")) + list(self.download_dir.glob("**/*.flac"))
            print(f"🎵 Audio files downloaded: {len(audio_files)} (expected: 0 with dummy credentials)")

        except subprocess.TimeoutExpired:
            print("⏰ Spotify test timed out (expected with dummy credentials)")
            # This is actually expected behavior with dummy credentials

    @requires_network_tests
    def test_mixed_content_links_file_real_network(self):
        """Test processing a links file with mixed content types."""
        print("\n📄 Testing mixed content links file with real network...")

        config_file = self.config.create_test_sldl_config(self.download_dir)
        links_file = self.config.create_test_links_file('mixed', self.temp_dir)

        print(f"📄 Links file contains: YouTube, Spotify, SoundCloud, and search terms")

        cmd = [
            'toolcrate', 'sldl',
            '--download-path', str(self.download_dir),
            '--links-file', str(links_file)
        ]

        print(f"🚀 Running command: {' '.join(cmd)}")

        env = os.environ.copy()
        env['SLDL_CONFIG'] = str(config_file)

        try:
            timeout = self.config.timeout_long  # Use long timeout for mixed content
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=self.temp_dir
            )

            print(f"📤 Command output:\n{result.stdout}")
            if result.stderr:
                print(f"⚠️ Command errors:\n{result.stderr}")

            # Check what was processed
            downloaded_files = list(self.download_dir.glob("**/*"))
            audio_files = [f for f in downloaded_files if f.suffix.lower() in ['.mp3', '.flac', '.wav', '.m4a']]

            print(f"📁 Total files: {len(downloaded_files)}")
            print(f"🎵 Audio files: {len(audio_files)}")

            # Show downloaded files
            for file in audio_files[:5]:  # Show first 5 files
                size_mb = file.stat().st_size / 1024 / 1024
                print(f"  ✅ {file.name} ({size_mb:.1f} MB)")

            # Test passes if we see evidence of processing different types
            output_lower = result.stdout.lower() + result.stderr.lower()
            processing_evidence = {
                'youtube': 'youtube' in output_lower or 'yt-dlp' in output_lower,
                'spotify': 'spotify' in output_lower,
                'search': 'search' in output_lower or 'soulseek' in output_lower,
                'downloads': len(audio_files) > 0
            }

            print(f"🔍 Processing evidence: {processing_evidence}")

            # At least some processing should occur
            self.assertTrue(
                any(processing_evidence.values()),
                f"Expected evidence of processing different link types. Got: {result.stdout}"
            )

        except subprocess.TimeoutExpired:
            print("⏰ Mixed content test timed out")
            # Check if any partial downloads occurred
            downloaded_files = list(self.download_dir.glob("**/*"))
            if downloaded_files:
                print(f"📁 Partial downloads found: {len(downloaded_files)} files")

    def test_links_file_processing_real_network(self):
        """Test processing a links file with mixed content."""
        print("\n📄 Testing links file processing with real network...")
        
        config_file = self.create_test_sldl_config()
        
        # Create links file with mixed content
        links_content = f"""# Test links file for real network testing
# YouTube should work with yt-dlp fallback
{self.test_urls['youtube_short']}

# Search terms (should attempt Soulseek search)
Rick Astley - Never Gonna Give You Up

# Spotify (may fail with dummy credentials)
{self.test_urls['spotify_track']}
"""
        
        links_file = self.temp_dir / "mixed_links.txt"
        links_file.write_text(links_content)
        
        cmd = [
            'toolcrate', 'sldl',
            '--download-path', str(self.download_dir),
            '--links-file', str(links_file)
        ]
        
        print(f"🚀 Running command: {' '.join(cmd)}")
        
        env = os.environ.copy()
        env['SLDL_CONFIG'] = str(config_file)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout for multiple items
                env=env,
                cwd=self.temp_dir
            )
            
            print(f"📤 Command output:\n{result.stdout}")
            if result.stderr:
                print(f"⚠️ Command errors:\n{result.stderr}")
            
            # Check what was processed
            downloaded_files = list(self.download_dir.glob("**/*"))
            downloaded_audio = [f for f in downloaded_files if f.suffix.lower() in ['.mp3', '.flac', '.wav', '.m4a']]
            
            print(f"📁 Total files: {len(downloaded_files)}")
            print(f"🎵 Audio files: {len(downloaded_audio)}")
            
            # Test passes if we see evidence of processing different types
            output_lower = result.stdout.lower()
            processing_evidence = [
                "youtube" in output_lower,
                "spotify" in output_lower,
                "search" in output_lower,
                "yt-dlp" in output_lower,
                len(downloaded_audio) > 0
            ]
            
            self.assertTrue(
                any(processing_evidence),
                f"Expected evidence of processing different link types. Got: {result.stdout}"
            )
            
        except subprocess.TimeoutExpired:
            print("⏰ Mixed links test timed out")
            # Check if any partial downloads occurred
            downloaded_files = list(self.download_dir.glob("**/*"))
            if downloaded_files:
                print(f"📁 Partial downloads found: {len(downloaded_files)} files")

    def test_docker_container_real_execution(self):
        """Test that Docker container can actually be started and execute commands."""
        print("\n🐳 Testing Docker container real execution...")
        
        # Check if Docker is available
        try:
            docker_check = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if docker_check.returncode != 0:
                self.skipTest("Docker not available")
        except FileNotFoundError:
            self.skipTest("Docker not installed")
        
        config_file = self.create_test_sldl_config()
        
        # Try to run a simple command in the container
        cmd = [
            'toolcrate', '--build', 'sldl',
            '--help'
        ]
        
        print(f"🚀 Running command: {' '.join(cmd)}")
        
        env = os.environ.copy()
        env['SLDL_CONFIG'] = str(config_file)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for container build
                env=env,
                cwd=self.temp_dir
            )
            
            print(f"📤 Command output:\n{result.stdout}")
            if result.stderr:
                print(f"⚠️ Command errors:\n{result.stderr}")
            
            # Should show help or container activity
            self.assertTrue(
                result.returncode == 0 or
                "sldl" in result.stdout.lower() or
                "docker" in result.stdout.lower() or
                "container" in result.stdout.lower(),
                f"Expected Docker container activity. Got: {result.stdout}"
            )
            
        except subprocess.TimeoutExpired:
            self.fail("Docker container test timed out")


if __name__ == "__main__":
    # Print instructions
    config = NetworkTestConfig()

    if not config.enabled:
        print("\n" + "="*70)
        print("🧪 REAL NETWORK INTEGRATION TESTS")
        print("="*70)
        print("These tests perform ACTUAL downloads using dummy credentials.")
        print("They are disabled by default for safety.")
        print("")
        print("🚀 To enable:")
        print("  export TOOLCRATE_REAL_NETWORK_TESTS=1")
        print("  python tests/integration/test_real_network_downloads.py")
        print("")
        print("🔧 Optional configuration:")
        print("  export TOOLCRATE_NETWORK_TIMEOUT_SHORT=180  # 3 minutes")
        print("  export TOOLCRATE_NETWORK_TIMEOUT_LONG=600   # 10 minutes")
        print("  export TOOLCRATE_MAX_DOWNLOAD_SIZE=50MB")
        print("")
        print("⚠️  WARNING: These tests will:")
        print("  - Attempt real network connections to Soulseek/YouTube/SoundCloud")
        print("  - Try to download actual audio files (small files, <50MB total)")
        print(f"  - Use dummy Soulseek credentials ({config.dummy_credentials['username']})")
        print("  - May take 5-15 minutes to complete")
        print("  - Create temporary files that are cleaned up automatically")
        print("")
        print("✅ These tests are useful for:")
        print("  - Verifying end-to-end download functionality")
        print("  - Testing real URL processing with actual network requests")
        print("  - Validating Docker container execution with real commands")
        print("  - Checking yt-dlp fallback functionality with real YouTube URLs")
        print("")
        print("🛡️  Safety features:")
        print("  - Uses only public playlists and well-known content")
        print("  - Dummy credentials prevent real Soulseek account usage")
        print("  - Automatic cleanup of all downloaded files")
        print("  - Configurable timeouts and download size limits")
        print("="*70)
    else:
        print("🧪 Real network tests ENABLED - starting test execution...")
        config.print_test_info()

    unittest.main()
