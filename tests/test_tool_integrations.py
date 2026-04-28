import os
import sys
from pathlib import Path

from click.testing import CliRunner

from toolcrate.cli import binary_manager
from toolcrate.cli.main import main


def make_executable(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_verify_tools_runs_managed_commands(monkeypatch, tmp_path):
    monkeypatch.setenv(binary_manager.APP_DIR_ENV, str(tmp_path))
    bin_dir = binary_manager.managed_bin_dir()

    make_executable(bin_dir / "sldl", "#!/usr/bin/env bash\necho sldl-test\n")
    make_executable(bin_dir / "shazam-tool", "#!/usr/bin/env bash\necho shazam-test\n")
    make_executable(bin_dir / "mdl-tool", "#!/usr/bin/env bash\necho mdl-test\n")

    results = binary_manager.verify_tools(timeout=2)

    assert {result.name for result in results} == {
        "slsk-batchdl",
        "shazam-tool",
        "mdl-tool",
    }
    assert all(result.ok for result in results)
    assert "sldl-test" in results[0].output


def test_cli_verify_reports_failures(monkeypatch, tmp_path):
    monkeypatch.setenv(binary_manager.APP_DIR_ENV, str(tmp_path))
    bin_dir = binary_manager.managed_bin_dir()
    make_executable(bin_dir / "sldl", "#!/usr/bin/env bash\necho ok\n")

    result = CliRunner().invoke(main, ["tools", "verify", "--timeout", "2"])

    assert result.exit_code != 0
    assert "slsk-batchdl: ok" in result.output
    assert "shazam-tool: failed" in result.output
    assert "mdl-tool: failed" in result.output


def test_install_sldl_uses_native_binary_provisioner(monkeypatch, tmp_path):
    monkeypatch.setenv(binary_manager.APP_DIR_ENV, str(tmp_path / "home"))
    project = tmp_path / "project"
    provisioned = make_executable(
        tmp_path / "managed" / "sldl", "#!/usr/bin/env bash\necho runtime-ok\n"
    )
    monkeypatch.setattr(binary_manager, "project_root", lambda: project)
    monkeypatch.setattr(
        binary_manager,
        "ensure_sldl_binary",
        lambda project_root: provisioned,
    )

    installed = binary_manager.install_sldl()

    assert installed == provisioned
    assert os.access(installed, os.X_OK)


def test_install_shazam_and_mdl_create_runnable_shims(monkeypatch, tmp_path):
    monkeypatch.setenv(binary_manager.APP_DIR_ENV, str(tmp_path / "home"))
    project = tmp_path / "project"
    shazam_script = project / "src" / "Shazam-Tool" / "shazam.py"
    shazam_script.parent.mkdir(parents=True)
    shazam_script.write_text(
        "import sys\nprint('fake shazam ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(binary_manager, "project_root", lambda: project)

    shazam = binary_manager.install_shazam_tool()
    mdl = binary_manager.install_mdl_tool()

    assert str(shazam_script) in shazam.read_text(encoding="utf-8")
    assert "-m toolcrate.cli.mdl" in mdl.read_text(encoding="utf-8")
    assert sys.executable in shazam.read_text(encoding="utf-8")
