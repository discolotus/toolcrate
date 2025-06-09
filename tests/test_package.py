"""Tests for ToolCrate package metadata and structure."""


def test_package_version():
    """Test that package version is accessible."""
    from toolcrate import __version__

    assert __version__ == "0.1.0"


def test_package_structure():
    """Test that package has expected structure."""
    import toolcrate
    import toolcrate.cli
    import toolcrate.cli.main
    import toolcrate.cli.wrappers

    # Verify modules can be imported without errors
    assert hasattr(toolcrate.cli.main, "main")
    assert hasattr(toolcrate.cli.wrappers, "run_slsk")
    assert hasattr(toolcrate.cli.wrappers, "run_shazam")
    assert hasattr(toolcrate.cli.wrappers, "run_mdl")


def test_package_docstring():
    """Test that package has proper docstring."""
    import toolcrate

    assert toolcrate.__doc__ is not None
    assert "ToolCrate" in toolcrate.__doc__
    assert "music management" in toolcrate.__doc__


def test_cli_module_docstring():
    """Test that CLI module has proper docstring."""
    import toolcrate.cli

    assert toolcrate.cli.__doc__ is not None
    assert "CLI module" in toolcrate.cli.__doc__
