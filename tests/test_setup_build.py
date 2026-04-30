"""Tests for project layout, packaging metadata, and the sldl build path.

These tests were originally written against a setup.py + Poetry layout. The
project has since migrated to uv + pyproject.toml `[project]` and the slsk
binary is now provisioned via :mod:`toolcrate.cli.binary_manager` rather than
shelled-out `dotnet publish` calls inside ``run_slsk``. Tests that exercised
the removed behaviour have been dropped.
"""

from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent


class TestProjectStructure:
    """Validate the on-disk project layout."""

    def test_pyproject_toml_exists(self):
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        assert pyproject_path.exists()

        content = pyproject_path.read_text()
        # uv layout uses PEP 621 [project], not [tool.poetry]
        assert "[project]" in content
        assert 'name = "toolcrate"' in content

    def test_src_directory_structure(self):
        src_path = PROJECT_ROOT / "src"
        assert src_path.exists()

        toolcrate_path = src_path / "toolcrate"
        assert toolcrate_path.exists()

        cli_path = toolcrate_path / "cli"
        assert cli_path.exists()

        assert (toolcrate_path / "__init__.py").exists()
        assert (cli_path / "__init__.py").exists()
        assert (cli_path / "main.py").exists()
        assert (cli_path / "wrappers.py").exists()

    def test_console_scripts_configuration(self):
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        content = pyproject_path.read_text()

        assert 'toolcrate = "toolcrate.cli.main:main"' in content
        assert 'slsk-tool = "toolcrate.cli.wrappers:run_slsk"' in content
        assert 'shazam-tool = "toolcrate.cli.wrappers:run_shazam"' in content
        assert 'mdl-tool = "toolcrate.cli.wrappers:run_mdl"' in content

    def test_dependencies_configuration(self):
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        content = pyproject_path.read_text()

        for dep in ("click", "pydantic", "loguru"):
            assert dep in content, f"runtime dep {dep!r} missing from pyproject.toml"

        for dev_dep in ("pytest", "ruff", "mypy"):
            assert dev_dep in content, f"dev dep {dev_dep!r} missing from pyproject.toml"


class TestSldlBuildPath:
    """run_slsk now delegates to binary_manager.ensure_sldl_binary."""

    def test_run_slsk_provisions_binary_via_binary_manager(self):
        from toolcrate.cli import wrappers

        fake_binary = Path("/fake/bin/sldl")
        with (
            patch("sys.argv", ["slsk-tool", "--help"]),
            patch(
                "toolcrate.cli.binary_manager.ensure_sldl_binary",
                return_value=fake_binary,
            ) as mock_ensure,
            patch("os.execv") as mock_execv,
        ):
            wrappers.run_slsk()

        mock_ensure.assert_called_once()
        mock_execv.assert_called_once_with(
            str(fake_binary), [fake_binary.name, "--help"]
        )

    def test_run_slsk_reports_error_when_binary_unavailable(self):
        from toolcrate.cli import binary_manager, wrappers

        with (
            patch("sys.argv", ["slsk-tool"]),
            patch(
                "toolcrate.cli.binary_manager.ensure_sldl_binary",
                side_effect=binary_manager.BinaryError("nope"),
            ),
            patch("click.echo") as mock_echo,
            patch("sys.exit") as mock_exit,
            patch("os.execv") as mock_execv,
        ):
            wrappers.run_slsk()

        mock_echo.assert_called_once()
        mock_exit.assert_called_once_with(1)
        mock_execv.assert_not_called()


class TestPackageMetadata:
    """Version sanity check across __init__ and pyproject.toml."""

    def test_package_version_matches_pyproject(self):
        from toolcrate import __version__

        pyproject_content = (PROJECT_ROOT / "pyproject.toml").read_text()

        assert (
            f'version = "{__version__}"' in pyproject_content
            or f"version = '{__version__}'" in pyproject_content
        )
