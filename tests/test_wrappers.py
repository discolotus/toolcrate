"""Tests for the public wrapper entrypoints.

The wrappers (``run_slsk``/``run_shazam``/``run_mdl``) used to inline a Docker
image probe + ``shutil.which`` lookup. After the binary-manager refactor they
delegate to :mod:`toolcrate.cli.binary_manager`. These tests exercise the new
contract.

The lower-level helpers (``check_dependency``, ``check_docker_image``,
``get_project_root``) are covered by :mod:`tests.unit.test_wrappers`.
"""

from pathlib import Path
from unittest.mock import patch

from toolcrate.cli import wrappers
from toolcrate.cli.binary_manager import BinaryError


class TestRunSlsk:
    def test_invokes_provisioned_binary(self, mock_os_execv):
        fake_binary = Path("/fake/bin/sldl")
        with (
            patch("sys.argv", ["slsk-tool", "search", "test"]),
            patch(
                "toolcrate.cli.binary_manager.ensure_sldl_binary",
                return_value=fake_binary,
            ),
            patch("toolcrate.cli.wrappers.get_project_root"),
        ):
            wrappers.run_slsk()

        mock_os_execv.assert_called_once_with(
            str(fake_binary), [fake_binary.name, "search", "test"]
        )

    def test_reports_error_when_binary_unavailable(
        self, mock_click_echo, mock_sys_exit, mock_os_execv
    ):
        with (
            patch("sys.argv", ["slsk-tool", "search", "test"]),
            patch(
                "toolcrate.cli.binary_manager.ensure_sldl_binary",
                side_effect=BinaryError("nope"),
            ),
            patch("toolcrate.cli.wrappers.get_project_root"),
        ):
            wrappers.run_slsk()

        mock_click_echo.assert_called_once()
        mock_sys_exit.assert_called_once_with(1)
        mock_os_execv.assert_not_called()


class TestRunShazam:
    def test_invokes_managed_binary(self, mock_os_execv):
        managed = Path("/fake/share/toolcrate/bin/shazam-tool")
        with (
            patch("sys.argv", ["shazam-tool", "scan"]),
            patch(
                "toolcrate.cli.binary_manager.find_managed",
                return_value=managed,
            ),
        ):
            wrappers.run_shazam()

        mock_os_execv.assert_called_once_with(
            str(managed), ["shazam-tool", "scan"]
        )

    def test_reports_error_when_not_installed(
        self, mock_click_echo, mock_sys_exit, mock_os_execv
    ):
        with (
            patch("sys.argv", ["shazam-tool", "scan"]),
            patch("toolcrate.cli.binary_manager.find_managed", return_value=None),
        ):
            wrappers.run_shazam()

        mock_click_echo.assert_called_once()
        mock_sys_exit.assert_called_once_with(1)
        mock_os_execv.assert_not_called()


class TestRunMdl:
    def test_invokes_managed_binary(self, mock_os_execv):
        managed = Path("/fake/share/toolcrate/bin/mdl-tool")
        with (
            patch("sys.argv", ["mdl-tool", "get-metadata", "file.mp3"]),
            patch(
                "toolcrate.cli.binary_manager.find_managed",
                return_value=managed,
            ),
        ):
            wrappers.run_mdl()

        mock_os_execv.assert_called_once_with(
            str(managed), ["mdl-tool", "get-metadata", "file.mp3"]
        )

    def test_reports_error_when_not_installed(
        self, mock_click_echo, mock_sys_exit, mock_os_execv
    ):
        with (
            patch("sys.argv", ["mdl-tool", "get-metadata", "file.mp3"]),
            patch("toolcrate.cli.binary_manager.find_managed", return_value=None),
        ):
            wrappers.run_mdl()

        mock_click_echo.assert_called_once()
        mock_sys_exit.assert_called_once_with(1)
        mock_os_execv.assert_not_called()
