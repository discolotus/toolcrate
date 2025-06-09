"""Integration tests for cron job management functionality."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import shutil


class TestCronManagement(unittest.TestCase):
    """Test cron job management functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_cron_content = """# User crontab
0 2 * * * /usr/bin/backup
30 1 * * 0 /usr/bin/weekly-task
"""
        self.toolcrate_cron_section = """
# ToolCrate Jobs - Start
# daily_wishlist: Download wishlist items daily
0 2 * * * cd /fake/root && poetry run python -m toolcrate.wishlist.processor
# ToolCrate Jobs - End
"""

    @patch('subprocess.run')
    def test_crontab_reading(self, mock_subprocess):
        """Test reading current crontab."""
        # Mock successful crontab read
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = self.test_cron_content
        mock_subprocess.return_value = mock_result
        
        try:
            from toolcrate.cli.schedule import get_current_crontab
            
            result = get_current_crontab()
            self.assertEqual(result, self.test_cron_content)
            
            # Verify crontab -l was called
            mock_subprocess.assert_called_with(
                ['crontab', '-l'],
                capture_output=True,
                text=True,
                check=False
            )
            
        except ImportError:
            self.skipTest("Schedule module not available")

    @patch('subprocess.run')
    def test_crontab_writing(self, mock_subprocess):
        """Test writing to crontab."""
        # Mock successful crontab write
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        try:
            from toolcrate.cli.schedule import update_crontab
            
            new_content = self.test_cron_content + self.toolcrate_cron_section
            result = update_crontab(new_content)
            
            self.assertTrue(result)
            
            # Should have called crontab with temp file
            self.assertEqual(mock_subprocess.call_count, 1)
            call_args = mock_subprocess.call_args[0][0]
            self.assertEqual(call_args[0], 'crontab')
            self.assertTrue(call_args[1].startswith('/tmp/') or call_args[1].startswith('/var/'))
            
        except ImportError:
            self.skipTest("Schedule module not available")

    @patch('toolcrate.cli.schedule.get_current_crontab')
    def test_toolcrate_job_removal(self, mock_get_crontab):
        """Test removing existing ToolCrate jobs from crontab."""
        # Mock crontab with existing ToolCrate jobs
        existing_crontab = self.test_cron_content + self.toolcrate_cron_section
        mock_get_crontab.return_value = existing_crontab
        
        try:
            from toolcrate.cli.schedule import remove_toolcrate_jobs_from_crontab
            
            result = remove_toolcrate_jobs_from_crontab()
            
            # Should remove ToolCrate section but keep other jobs
            self.assertIn('/usr/bin/backup', result)
            self.assertIn('/usr/bin/weekly-task', result)
            self.assertNotIn('ToolCrate Jobs', result)
            self.assertNotIn('toolcrate.wishlist.processor', result)
            
        except ImportError:
            self.skipTest("Schedule module not available")

    @patch('toolcrate.cli.schedule.get_project_root')
    def test_crontab_section_generation(self, mock_get_root):
        """Test generating ToolCrate crontab section."""
        mock_get_root.return_value = Path('/fake/root')
        
        try:
            from toolcrate.cli.schedule import generate_crontab_section
            from toolcrate.config.manager import ConfigManager
            
            # Mock config manager
            mock_config_manager = MagicMock()
            
            # Test jobs
            jobs = [
                {
                    'name': 'daily_wishlist',
                    'schedule': '0 2 * * *',
                    'description': 'Download wishlist items daily',
                    'command': 'wishlist',
                    'enabled': True
                },
                {
                    'name': 'hourly_queue',
                    'schedule': '0 * * * *',
                    'description': 'Process download queue hourly',
                    'command': 'queue',
                    'enabled': False
                }
            ]
            
            result = generate_crontab_section(mock_config_manager, jobs, cron_enabled=True)
            
            # Should contain job definitions
            self.assertIn('ToolCrate Jobs - Start', result)
            self.assertIn('ToolCrate Jobs - End', result)
            self.assertIn('daily_wishlist: Download wishlist items daily', result)
            self.assertIn('0 2 * * *', result)
            self.assertIn('toolcrate.wishlist.processor', result)
            
            # Disabled job should be commented
            self.assertIn('# 0 * * * *', result)
            self.assertIn('toolcrate.queue.processor', result)
            
        except ImportError:
            self.skipTest("Schedule module not available")

    @patch('subprocess.run')
    def test_cron_manager_add_wishlist_job(self, mock_subprocess):
        """Test adding wishlist cron job via cron_manager."""
        # Mock successful operations
        mock_results = [
            MagicMock(returncode=0, stdout=self.test_cron_content),  # crontab -l
            MagicMock(returncode=0),  # crontab <tempfile>
        ]
        mock_subprocess.side_effect = mock_results
        
        # Mock find_command_path
        with patch('toolcrate.scripts.cron_manager.find_command_path', return_value='/usr/bin/toolcrate'):
            with patch('toolcrate.scripts.cron_manager.read_config_file', return_value={'wishlist': '/fake/wishlist.txt'}):
                with patch('os.path.exists', return_value=True):
                    try:
                        from toolcrate.scripts.cron_manager import add_download_wishlist_cron
                        
                        result = add_download_wishlist_cron('daily')
                        
                        self.assertTrue(result)
                        
                        # Should have called crontab commands
                        self.assertEqual(mock_subprocess.call_count, 2)
                        
                    except ImportError:
                        self.skipTest("Cron manager not available")

    def test_schedule_command_integration(self):
        """Test that schedule commands are properly integrated."""
        # Test that schedule command exists
        result = subprocess.run(
            ["toolcrate", "schedule", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("schedule", result.stdout.lower())

    def test_schedule_convenience_commands(self):
        """Test that convenience commands (hourly, daily) exist."""
        # Test hourly command
        result = subprocess.run(
            ["toolcrate", "schedule", "hourly", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("hourly", result.stdout.lower())
        
        # Test daily command
        result = subprocess.run(
            ["toolcrate", "schedule", "daily", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("daily", result.stdout.lower())

    @patch('toolcrate.cli.schedule.add_toolcrate_jobs_to_crontab')
    @patch('toolcrate.config.manager.ConfigManager')
    def test_schedule_add_workflow(self, mock_config_manager, mock_add_to_crontab):
        """Test complete schedule add workflow."""
        # Mock successful crontab addition
        mock_add_to_crontab.return_value = True
        
        # Mock config manager
        mock_config_instance = MagicMock()
        mock_config_manager.return_value = mock_config_instance
        mock_config_instance.config = {
            'cron': {
                'enabled': True,
                'jobs': []
            }
        }
        mock_config_instance.save_config = MagicMock()
        
        try:
            from click.testing import CliRunner
            from toolcrate.cli.schedule import add
            
            runner = CliRunner()
            result = runner.invoke(add, [
                '--schedule', '0 2 * * *',
                '--name', 'test_job',
                '--description', 'Test job description',
                '--type', 'wishlist'
            ])
            
            # Should execute without errors
            self.assertEqual(result.exit_code, 0)
            
            # Should have called save_config
            mock_config_instance.save_config.assert_called_once()
            
        except ImportError:
            self.skipTest("Schedule module not available")

    def test_cron_expression_validation(self):
        """Test that cron expressions are properly validated."""
        valid_expressions = [
            '0 * * * *',      # Every hour
            '0 2 * * *',      # Daily at 2 AM
            '0 0 * * 0',      # Weekly on Sunday
            '*/15 * * * *',   # Every 15 minutes
            '0 9-17 * * 1-5', # Business hours weekdays
        ]
        
        invalid_expressions = [
            '60 * * * *',     # Invalid minute
            '* 25 * * *',     # Invalid hour
            '* * 32 * *',     # Invalid day
            '* * * 13 *',     # Invalid month
            '* * * * 8',      # Invalid weekday
        ]
        
        try:
            from toolcrate.cli.schedule import validate_cron_expression
            
            for expr in valid_expressions:
                with self.subTest(expression=expr):
                    # Should not raise exception
                    validate_cron_expression(expr)
            
            for expr in invalid_expressions:
                with self.subTest(expression=expr):
                    with self.assertRaises(ValueError):
                        validate_cron_expression(expr)
                        
        except ImportError:
            self.skipTest("Schedule validation not available")


class TestCronJobExecution(unittest.TestCase):
    """Test actual cron job execution scenarios."""

    def test_wishlist_processor_module_execution(self):
        """Test that wishlist processor can be executed as module."""
        # Test that the module can be imported and has main execution
        try:
            result = subprocess.run(
                ["python", "-c", "import toolcrate.wishlist.processor; print('Import successful')"],
                capture_output=True,
                text=True,
                check=False,
            )
            
            self.assertEqual(result.returncode, 0)
            self.assertIn("Import successful", result.stdout)
            
        except Exception as e:
            self.fail(f"Could not test wishlist processor module: {e}")

    def test_queue_processor_module_execution(self):
        """Test that queue processor can be executed as module."""
        # Test that the module can be imported and has main execution
        try:
            result = subprocess.run(
                ["python", "-c", "import toolcrate.queue.processor; print('Import successful')"],
                capture_output=True,
                text=True,
                check=False,
            )
            
            self.assertEqual(result.returncode, 0)
            self.assertIn("Import successful", result.stdout)
            
        except Exception as e:
            self.fail(f"Could not test queue processor module: {e}")


if __name__ == "__main__":
    unittest.main()
