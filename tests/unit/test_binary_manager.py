"""Unit tests for the sldl binary manager."""

import io
import json
import os
import stat
import urllib.error
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from toolcrate.cli.binary_manager import (
    BinaryError,
    _binary_name,
    _build_from_source,
    _data_dir,
    _install_from_release,
    _strip_macos_quarantine,
    _verify_executable,
    ensure_sldl_binary,
    get_binary_path,
    get_platform_asset_name,
    resolve_latest_version,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_zip(binary_name: str, content: bytes = b"fake-binary") -> bytes:
    """Return the bytes of a zip archive containing a single fake binary."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(binary_name, content)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------

class TestBinaryName:
    def test_unix_name(self):
        with patch("sys.platform", "linux"):
            assert _binary_name() == "sldl"

    def test_windows_name(self):
        with patch("sys.platform", "win32"):
            assert _binary_name() == "sldl.exe"


class TestGetPlatformAssetName:
    @pytest.mark.parametrize("plat,machine,expected", [
        ("darwin", "arm64",  "sldl_osx-arm64.zip"),
        ("darwin", "aarch64","sldl_osx-arm64.zip"),
        ("darwin", "x86_64", "sldl_osx-x64.zip"),
        ("linux",  "x86_64", "sldl_linux-x64.zip"),
        ("linux",  "arm64",  "sldl_linux-arm64.zip"),
        ("win32",  "amd64",  "sldl_win-x64.zip"),
    ])
    def test_known_platforms(self, plat, machine, expected):
        with patch("sys.platform", plat), patch("platform.machine", return_value=machine):
            assert get_platform_asset_name("v2.4.7") == expected

    def test_unsupported_platform(self):
        with patch("sys.platform", "freebsd"), patch("platform.machine", return_value="x86_64"):
            with pytest.raises(BinaryError, match="Unsupported platform"):
                get_platform_asset_name("v1.0")


# ---------------------------------------------------------------------------
# Data directory
# ---------------------------------------------------------------------------

class TestDataDir:
    def test_uses_xdg_data_home(self, tmp_path):
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path)}):
            result = _data_dir()
            assert result == tmp_path / "toolcrate"
            assert result.exists()

    def test_falls_back_to_home(self, tmp_path):
        env = {k: v for k, v in os.environ.items() if k != "XDG_DATA_HOME"}
        with patch.dict(os.environ, env, clear=True), patch("pathlib.Path.home", return_value=tmp_path):
            result = _data_dir()
            assert result == tmp_path / ".local" / "share" / "toolcrate"


class TestGetBinaryPath:
    def test_path_ends_with_binary_name(self, tmp_path):
        with patch("toolcrate.cli.binary_manager._data_dir", return_value=tmp_path):
            p = get_binary_path()
            assert p.name == _binary_name()
            assert p.parent == tmp_path / "bin"


# ---------------------------------------------------------------------------
# resolve_latest_version
# ---------------------------------------------------------------------------

class TestResolveLatestVersion:
    def test_env_override(self):
        with patch.dict(os.environ, {"TOOLCRATE_SLDL_VERSION": "v9.9.9"}):
            assert resolve_latest_version() == "v9.9.9"

    def test_fetches_from_github(self):
        payload = json.dumps({"tag_name": "v2.5.0"}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert resolve_latest_version() == "v2.5.0"

    def test_network_error_raises(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            with pytest.raises(BinaryError, match="Could not resolve"):
                resolve_latest_version()

    def test_missing_tag_name_raises(self):
        payload = json.dumps({"name": "release"}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(BinaryError, match="missing tag_name"):
                resolve_latest_version()


# ---------------------------------------------------------------------------
# _strip_macos_quarantine
# ---------------------------------------------------------------------------

class TestStripMacosQuarantine:
    def test_noop_on_non_darwin(self, tmp_path):
        f = tmp_path / "sldl"
        f.write_bytes(b"x")
        with patch("sys.platform", "linux"):
            _strip_macos_quarantine(f)  # should not call xattr

    def test_calls_xattr_on_darwin(self, tmp_path):
        f = tmp_path / "sldl"
        f.write_bytes(b"x")
        with patch("sys.platform", "darwin"), \
             patch("shutil.which", return_value="/usr/bin/xattr"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            _strip_macos_quarantine(f)
            mock_run.assert_called_once_with(
                ["xattr", "-dr", "com.apple.quarantine", str(f)],
                check=False,
                capture_output=True,
            )

    def test_silently_skips_when_xattr_missing(self, tmp_path):
        f = tmp_path / "sldl"
        f.write_bytes(b"x")
        with patch("sys.platform", "darwin"), patch("shutil.which", return_value=None):
            _strip_macos_quarantine(f)  # should not raise


# ---------------------------------------------------------------------------
# _verify_executable
# ---------------------------------------------------------------------------

class TestVerifyExecutable:
    def test_returns_true_on_success(self, tmp_path):
        binary = tmp_path / "sldl"
        binary.write_bytes(b"x")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            assert _verify_executable(binary) is True

    def test_returns_false_on_nonzero_exit(self, tmp_path):
        binary = tmp_path / "sldl"
        binary.write_bytes(b"x")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            assert _verify_executable(binary) is False

    def test_returns_false_on_os_error(self, tmp_path):
        binary = tmp_path / "sldl"
        binary.write_bytes(b"x")
        with patch("subprocess.run", side_effect=OSError("permission denied")):
            assert _verify_executable(binary) is False

    def test_returns_false_on_timeout(self, tmp_path):
        import subprocess
        binary = tmp_path / "sldl"
        binary.write_bytes(b"x")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sldl", timeout=15)):
            assert _verify_executable(binary) is False


# ---------------------------------------------------------------------------
# _install_from_release
# ---------------------------------------------------------------------------

class TestInstallFromRelease:
    def test_downloads_and_extracts(self, tmp_path):
        zip_bytes = _make_zip("sldl", b"binary-content")

        with patch("toolcrate.cli.binary_manager._data_dir", return_value=tmp_path), \
             patch("sys.platform", "linux"), \
             patch("platform.machine", return_value="x86_64"), \
             patch("toolcrate.cli.binary_manager._download") as mock_dl, \
             patch("toolcrate.cli.binary_manager._strip_macos_quarantine"), \
             patch("toolcrate.cli.binary_manager._version_file") as mock_vf:

            # Simulate download writing the zip to the tmp file
            def fake_download(url, dest, timeout=120.0):
                dest.write_bytes(zip_bytes)
            mock_dl.side_effect = fake_download
            mock_vf.return_value = tmp_path / "sldl.version"

            result = _install_from_release("v2.5.0")

            assert result.read_bytes() == b"binary-content"
            assert result.stat().st_mode & stat.S_IXUSR

    def test_raises_when_binary_missing_from_zip(self, tmp_path):
        zip_bytes = _make_zip("other_file.txt", b"not a binary")

        with patch("toolcrate.cli.binary_manager._data_dir", return_value=tmp_path), \
             patch("sys.platform", "linux"), \
             patch("platform.machine", return_value="x86_64"), \
             patch("toolcrate.cli.binary_manager._download") as mock_dl:

            def fake_download(url, dest, timeout=120.0):
                dest.write_bytes(zip_bytes)
            mock_dl.side_effect = fake_download

            with pytest.raises(BinaryError, match="did not contain"):
                _install_from_release("v2.5.0")


# ---------------------------------------------------------------------------
# _build_from_source
# ---------------------------------------------------------------------------

class TestBuildFromSource:
    def test_raises_when_submodule_missing(self, tmp_path):
        project_root = tmp_path
        # src/slsk-batchdl doesn't exist
        with pytest.raises(BinaryError, match="Submodule not initialized"):
            _build_from_source(project_root)

    def test_raises_when_dotnet_missing(self, tmp_path):
        src_dir = tmp_path / "src" / "slsk-batchdl"
        src_dir.mkdir(parents=True)
        (src_dir / "dummy.csproj").write_text("<Project/>")

        with patch("shutil.which", return_value=None):
            with pytest.raises(BinaryError, match="dotnet SDK not found"):
                _build_from_source(tmp_path)

    def test_raises_on_dotnet_failure(self, tmp_path):
        src_dir = tmp_path / "src" / "slsk-batchdl"
        src_dir.mkdir(parents=True)
        (src_dir / "dummy.csproj").write_text("<Project/>")

        with patch("shutil.which", return_value="/usr/bin/dotnet"), \
             patch("toolcrate.cli.binary_manager._data_dir", return_value=tmp_path), \
             patch("sys.platform", "linux"), \
             patch("platform.machine", return_value="x86_64"), \
             patch("subprocess.run") as mock_run:

            mock_run.return_value.returncode = 1
            with pytest.raises(BinaryError, match="dotnet publish failed"):
                _build_from_source(tmp_path)

    def test_successful_build(self, tmp_path):
        src_dir = tmp_path / "src" / "slsk-batchdl"
        src_dir.mkdir(parents=True)
        (src_dir / "dummy.csproj").write_text("<Project/>")

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        def fake_run(*args, **kwargs):
            # Simulate dotnet producing the binary
            (bin_dir / "sldl").write_bytes(b"fake-sldl")
            result = MagicMock()
            result.returncode = 0
            return result

        with patch("shutil.which", return_value="/usr/bin/dotnet"), \
             patch("toolcrate.cli.binary_manager._data_dir", return_value=tmp_path), \
             patch("sys.platform", "linux"), \
             patch("platform.machine", return_value="x86_64"), \
             patch("subprocess.run", side_effect=fake_run), \
             patch("toolcrate.cli.binary_manager._version_file") as mock_vf:

            mock_vf.return_value = tmp_path / "sldl.version"
            result = _build_from_source(tmp_path)
            assert result.exists()
            assert result.stat().st_mode & stat.S_IXUSR


# ---------------------------------------------------------------------------
# ensure_sldl_binary — integration of the above
# ---------------------------------------------------------------------------

class TestEnsureSldlBinary:
    def test_returns_existing_valid_binary(self, tmp_path):
        binary = tmp_path / "bin" / "sldl"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"x")

        with patch("toolcrate.cli.binary_manager.get_binary_path", return_value=binary), \
             patch("toolcrate.cli.binary_manager._verify_executable", return_value=True):
            assert ensure_sldl_binary() == binary

    def test_force_refresh_re_downloads(self, tmp_path):
        binary = tmp_path / "bin" / "sldl"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"x")

        with patch("toolcrate.cli.binary_manager.get_binary_path", return_value=binary), \
             patch("toolcrate.cli.binary_manager._verify_executable", return_value=True), \
             patch("toolcrate.cli.binary_manager.resolve_latest_version", return_value="v1.0"), \
             patch("toolcrate.cli.binary_manager._install_from_release", return_value=binary) as mock_install:
            ensure_sldl_binary(force_refresh=True)
            mock_install.assert_called_once_with("v1.0")

    def test_build_from_source_env_var(self, tmp_path):
        binary = tmp_path / "sldl"
        binary.write_bytes(b"x")

        with patch.dict(os.environ, {"TOOLCRATE_SLDL_BUILD_FROM_SOURCE": "1"}), \
             patch("toolcrate.cli.binary_manager.get_binary_path", return_value=tmp_path / "sldl"), \
             patch("toolcrate.cli.binary_manager._verify_executable", return_value=False), \
             patch("toolcrate.cli.binary_manager._build_from_source", return_value=binary) as mock_build:
            result = ensure_sldl_binary(project_root=tmp_path)
            mock_build.assert_called_once_with(tmp_path)
            assert result == binary

    def test_falls_back_to_source_when_download_fails(self, tmp_path):
        binary = tmp_path / "sldl"
        binary.write_bytes(b"x")

        with patch("toolcrate.cli.binary_manager.get_binary_path", return_value=tmp_path / "sldl"), \
             patch("toolcrate.cli.binary_manager._verify_executable", return_value=False), \
             patch("toolcrate.cli.binary_manager.resolve_latest_version", side_effect=BinaryError("no network")), \
             patch("toolcrate.cli.binary_manager._build_from_source", return_value=binary) as mock_build:
            result = ensure_sldl_binary(project_root=tmp_path)
            mock_build.assert_called_once()
            assert result == binary

    def test_falls_back_to_source_when_binary_not_executable(self, tmp_path):
        binary = tmp_path / "sldl"
        binary.write_bytes(b"x")

        with patch("toolcrate.cli.binary_manager.get_binary_path", return_value=tmp_path / "sldl"), \
             patch("toolcrate.cli.binary_manager._verify_executable", return_value=False), \
             patch("toolcrate.cli.binary_manager.resolve_latest_version", return_value="v1.0"), \
             patch("toolcrate.cli.binary_manager._install_from_release", return_value=binary), \
             patch("toolcrate.cli.binary_manager._build_from_source", return_value=binary) as mock_build:
            ensure_sldl_binary(project_root=tmp_path)
            mock_build.assert_called_once_with(tmp_path)

    def test_raises_when_no_project_root_for_fallback(self, tmp_path):
        with patch("toolcrate.cli.binary_manager.get_binary_path", return_value=tmp_path / "sldl"), \
             patch("toolcrate.cli.binary_manager._verify_executable", return_value=False), \
             patch("toolcrate.cli.binary_manager.resolve_latest_version", side_effect=BinaryError("no network")):
            with pytest.raises(BinaryError, match="no project_root"):
                ensure_sldl_binary(project_root=None)
