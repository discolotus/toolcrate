"""Tests for Shazam tool functionality."""

import os
import sys
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, call
import pytest

# Add the Shazam-Tool directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "Shazam-Tool"))

try:
    import shazam
except ImportError:
    # If we can't import shazam, we'll skip these tests
    shazam = None


@pytest.mark.skipif(shazam is None, reason="Shazam tool not available")
class TestShazamTool:
    """Test cases for Shazam tool functionality."""

    def test_segment_length_constant(self):
        """Test that segment length constant is defined."""
        assert hasattr(shazam, 'SEGMENT_LENGTH')
        assert shazam.SEGMENT_LENGTH == 60 * 1000  # 1 minute in milliseconds

    def test_downloads_dir_constant(self):
        """Test that downloads directory constant is defined."""
        assert hasattr(shazam, 'DOWNLOADS_DIR')
        assert shazam.DOWNLOADS_DIR == 'downloads'

    def test_ensure_directory_exists(self, temp_dir):
        """Test ensure_directory_exists function."""
        test_dir = temp_dir / "test_directory"
        assert not test_dir.exists()
        
        shazam.ensure_directory_exists(str(test_dir))
        
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_ensure_directory_exists_already_exists(self, temp_dir):
        """Test ensure_directory_exists when directory already exists."""
        test_dir = temp_dir / "existing_directory"
        test_dir.mkdir()
        
        # Should not raise an error
        shazam.ensure_directory_exists(str(test_dir))
        
        assert test_dir.exists()

    def test_remove_files(self, temp_dir):
        """Test remove_files function."""
        # Create test directory with files
        test_dir = temp_dir / "test_remove"
        test_dir.mkdir()
        
        test_file1 = test_dir / "file1.txt"
        test_file2 = test_dir / "file2.txt"
        test_file1.write_text("content1")
        test_file2.write_text("content2")
        
        shazam.remove_files(str(test_dir))
        
        # Directory should be empty
        assert list(test_dir.iterdir()) == []

    def test_remove_files_nonexistent_directory(self):
        """Test remove_files with nonexistent directory."""
        # Should not raise an error
        shazam.remove_files("nonexistent_directory")

    @patch('shazam.AudioSegment')
    def test_segment_audio(self, mock_audio_segment, temp_dir):
        """Test segment_audio function."""
        # Mock audio file
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=180000)  # 3 minutes
        mock_audio.__getitem__ = Mock(return_value=Mock())
        mock_audio_segment.from_file.return_value = mock_audio
        
        output_dir = temp_dir / "segments"
        audio_file = temp_dir / "test.mp3"
        audio_file.write_bytes(b"fake mp3 content")
        
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_executor.return_value.__enter__.return_value.map = Mock()
            
            shazam.segment_audio(str(audio_file), str(output_dir))
            
            mock_audio_segment.from_file.assert_called_once_with(str(audio_file), format="mp3")
            assert output_dir.exists()

    @pytest.mark.asyncio
    async def test_get_name_success(self, sample_shazam_response):
        """Test get_name function with successful recognition."""
        with patch('shazam.Shazam') as mock_shazam_class:
            mock_shazam = AsyncMock()
            mock_shazam.recognize.return_value = sample_shazam_response
            mock_shazam_class.return_value = mock_shazam
            
            result = await shazam.get_name("test_file.mp3")
            
            assert result == "Test Artist - Test Song"
            mock_shazam.recognize.assert_called_once_with("test_file.mp3")

    @pytest.mark.asyncio
    async def test_get_name_not_found(self):
        """Test get_name function when song is not found."""
        with patch('shazam.Shazam') as mock_shazam_class:
            mock_shazam = AsyncMock()
            mock_shazam.recognize.return_value = {}  # No track data
            mock_shazam_class.return_value = mock_shazam
            
            result = await shazam.get_name("test_file.mp3")
            
            assert result == "Not found"

    @pytest.mark.asyncio
    async def test_get_name_with_retries(self):
        """Test get_name function with retry logic."""
        with patch('shazam.Shazam') as mock_shazam_class, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_shazam = AsyncMock()
            # First two calls return empty, third succeeds
            mock_shazam.recognize.side_effect = [
                {},  # First attempt fails
                {},  # Second attempt fails
                {'track': {'title': 'Success', 'subtitle': 'Artist'}}  # Third succeeds
            ]
            mock_shazam_class.return_value = mock_shazam
            
            result = await shazam.get_name("test_file.mp3", max_retries=3)
            
            assert result == "Artist - Success"
            assert mock_shazam.recognize.call_count == 3
            assert mock_sleep.call_count == 2

    def test_setup_logging_debug(self):
        """Test setup_logging function with debug enabled."""
        with patch('logging.basicConfig') as mock_config:
            shazam.setup_logging(debug=True)
            
            mock_config.assert_called_once()
            args, kwargs = mock_config.call_args
            assert kwargs['level'] == shazam.logging.DEBUG

    def test_setup_logging_no_debug(self):
        """Test setup_logging function with debug disabled."""
        with patch('logging.basicConfig') as mock_config:
            shazam.setup_logging(debug=False)
            
            mock_config.assert_called_once()
            args, kwargs = mock_config.call_args
            assert kwargs['level'] == shazam.logging.INFO

    @patch('shazam.YoutubeDL')
    def test_download_from_url(self, mock_ytdl):
        """Test download_from_url function."""
        mock_ytdl_instance = Mock()
        mock_ytdl.return_value = mock_ytdl_instance
        
        test_url = "https://www.youtube.com/watch?v=test"
        
        with patch('shazam.ensure_directory_exists'):
            shazam.download_from_url(test_url)
            
            mock_ytdl.assert_called_once()
            mock_ytdl_instance.download.assert_called_once_with([test_url])

    def test_process_downloads(self, temp_dir):
        """Test process_downloads function."""
        # Create mock downloads directory with MP3 files
        downloads_dir = temp_dir / "downloads"
        downloads_dir.mkdir()
        
        mp3_file1 = downloads_dir / "song1.mp3"
        mp3_file2 = downloads_dir / "song2.mp3"
        txt_file = downloads_dir / "readme.txt"
        
        mp3_file1.write_bytes(b"fake mp3 content")
        mp3_file2.write_bytes(b"fake mp3 content")
        txt_file.write_text("readme content")
        
        with patch('shazam.DOWNLOADS_DIR', str(downloads_dir)), \
             patch('shazam.process_audio_file') as mock_process:
            
            shazam.process_downloads()
            
            # Should process only MP3 files
            assert mock_process.call_count == 2
            processed_files = [call[0][0] for call in mock_process.call_args_list]
            assert str(mp3_file1) in processed_files
            assert str(mp3_file2) in processed_files

    def test_print_usage(self):
        """Test print_usage function."""
        with patch('builtins.print') as mock_print:
            shazam.print_usage()
            
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            assert "Usage: python shazam.py" in output
            assert "Commands:" in output
            assert "scan" in output
            assert "download" in output
            assert "recognize" in output

    @patch('shazam.process_downloads')
    @patch('shazam.download_from_url')
    def test_main_download_command(self, mock_download, mock_process):
        """Test main function with download command."""
        test_args = ['shazam.py', 'download', 'https://test.com/video']

        with patch('sys.argv', test_args), \
             patch('shazam.setup_logging'), \
             patch('shazam.ensure_directory_exists'), \
             patch('builtins.open', create=True):

            shazam.main()

            mock_download.assert_called_once_with('https://test.com/video')
            mock_process.assert_called_once()

    @patch('shazam.process_downloads')
    def test_main_scan_command(self, mock_process):
        """Test main function with scan command."""
        test_args = ['shazam.py', 'scan']

        with patch('sys.argv', test_args), \
             patch('shazam.setup_logging'):

            shazam.main()

            mock_process.assert_called_once()

    @patch('shazam.process_audio_file')
    def test_main_recognize_command(self, mock_process):
        """Test main function with recognize command."""
        test_args = ['shazam.py', 'recognize', 'test_file.mp3']

        with patch('sys.argv', test_args), \
             patch('shazam.setup_logging'), \
             patch('shazam.ensure_directory_exists'), \
             patch('builtins.open', create=True):

            shazam.main()

            mock_process.assert_called_once()

    @patch('shazam.print_usage')
    @patch('sys.exit')
    def test_main_no_command(self, mock_exit, mock_usage):
        """Test main function with no command."""
        test_args = ['shazam.py']

        with patch('sys.argv', test_args):
            shazam.main()

            mock_usage.assert_called_once()
            mock_exit.assert_called_once_with(1)

    @patch('sys.exit')
    def test_main_download_no_url(self, mock_exit):
        """Test main function with download command but no URL."""
        test_args = ['shazam.py', 'download']

        with patch('sys.argv', test_args), \
             patch('shazam.setup_logging'):

            shazam.main()

            mock_exit.assert_called_once_with(1)

    @patch('sys.exit')
    def test_main_recognize_no_file(self, mock_exit):
        """Test main function with recognize command but no file."""
        test_args = ['shazam.py', 'recognize']

        with patch('sys.argv', test_args), \
             patch('shazam.setup_logging'):

            shazam.main()

            mock_exit.assert_called_once_with(1)

    def test_main_debug_flag(self):
        """Test main function with debug flag."""
        test_args = ['shazam.py', 'scan', '--debug']

        with patch('sys.argv', test_args), \
             patch('shazam.setup_logging') as mock_setup, \
             patch('shazam.process_downloads'):

            shazam.main()

            mock_setup.assert_called_once_with(True)

    @patch('shazam.segment_audio')
    @patch('shazam.remove_files')
    @patch('shazam.get_name')
    def test_process_audio_file(self, mock_get_name, mock_remove, mock_segment, temp_dir):
        """Test process_audio_file function."""
        # Create mock audio file
        audio_file = temp_dir / "test.mp3"
        audio_file.write_bytes(b"fake mp3 content")

        # Create mock output file
        output_file = temp_dir / "output.txt"

        # Mock temporary files
        tmp_dir = temp_dir / "tmp"
        tmp_dir.mkdir()
        (tmp_dir / "1.mp3").write_bytes(b"segment1")
        (tmp_dir / "2.mp3").write_bytes(b"segment2")

        # Mock get_name to return different results
        mock_get_name.side_effect = asyncio.coroutine(lambda x: "Artist - Song" if "1.mp3" in x else "Not found")

        with patch('os.listdir', return_value=["1.mp3", "2.mp3"]), \
             patch('builtins.open', create=True) as mock_open, \
             patch('asyncio.run') as mock_asyncio_run:

            # Mock asyncio.run to execute the coroutine
            mock_asyncio_run.side_effect = lambda coro: asyncio.get_event_loop().run_until_complete(coro)

            shazam.process_audio_file(str(audio_file), str(output_file))

            mock_segment.assert_called_once()
            mock_remove.assert_called()

    def test_logger_setup(self):
        """Test that logger is properly configured."""
        assert hasattr(shazam, 'logger')
        assert shazam.logger.name == 'shazam_tool'
