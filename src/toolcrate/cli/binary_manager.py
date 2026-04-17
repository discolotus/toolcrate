"""Manage the sldl (slsk-batchdl) binary: download or build from source.

Resolves the latest upstream release on first run, caches the resolved version,
and falls back to building from the git submodule if the downloaded binary
cannot be executed (e.g. macOS Gatekeeper quarantine on unsigned binaries).
"""

from __future__ import annotations

import io
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from loguru import logger

UPSTREAM_REPO = "fiso64/slsk-batchdl"
GITHUB_API_LATEST = f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/latest"
GITHUB_DOWNLOAD = f"https://github.com/{UPSTREAM_REPO}/releases/download"

# Environment variable to override the pinned version (e.g. to test a specific tag)
ENV_VERSION = "TOOLCRATE_SLDL_VERSION"
# Environment variable to force rebuild-from-source path
ENV_BUILD_FROM_SOURCE = "TOOLCRATE_SLDL_BUILD_FROM_SOURCE"


class BinaryError(RuntimeError):
    """Raised when the sldl binary cannot be provisioned."""


def _data_dir() -> Path:
    """Return the toolcrate data directory (~/.local/share/toolcrate)."""
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    path = base / "toolcrate"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _binary_name() -> str:
    return "sldl.exe" if sys.platform == "win32" else "sldl"


def get_binary_path() -> Path:
    """Return the on-disk path where the sldl binary should live."""
    return _data_dir() / "bin" / _binary_name()


def _version_file() -> Path:
    return _data_dir() / "bin" / "sldl.version"


def get_platform_asset_name(version: str) -> str:
    """Return the upstream release asset filename for this host.

    Upstream publishes assets like `sldl_linux-x64.zip`, `sldl_osx-arm64.zip`,
    `sldl_win-x64.zip`. Version tags look like `v2.4.7` but asset names don't
    embed the version.
    """
    del version  # unused; asset names are version-independent upstream
    system = sys.platform
    machine = platform.machine().lower()

    if system == "darwin":
        rid = "osx-arm64" if machine in ("arm64", "aarch64") else "osx-x64"
    elif system == "linux":
        rid = "linux-arm64" if machine in ("arm64", "aarch64") else "linux-x64"
    elif system == "win32":
        rid = "win-x64"
    else:
        raise BinaryError(f"Unsupported platform: {system}/{machine}")

    return f"sldl_{rid}.zip"


def resolve_latest_version(timeout: float = 10.0) -> str:
    """Query GitHub for the latest release tag of slsk-batchdl."""
    override = os.environ.get(ENV_VERSION)
    if override:
        logger.info(f"Using pinned sldl version from {ENV_VERSION}: {override}")
        return override

    req = urllib.request.Request(
        GITHUB_API_LATEST,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "toolcrate"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as e:
        raise BinaryError(f"Could not resolve latest sldl version: {e}") from e

    tag = payload.get("tag_name")
    if not tag:
        raise BinaryError("GitHub release response missing tag_name")
    return tag


def _download(url: str, dest: Path, timeout: float = 120.0) -> None:
    logger.info(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "toolcrate"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dest.write_bytes(resp.read())
    except (urllib.error.URLError, TimeoutError) as e:
        raise BinaryError(f"Failed to download {url}: {e}") from e


def _strip_macos_quarantine(path: Path) -> None:
    """Remove the com.apple.quarantine xattr so Gatekeeper won't block execution.

    Downloaded binaries get quarantined by macOS. Stripping the attribute is the
    standard workaround for unsigned tools when building from source isn't
    viable. This is a no-op on non-macOS platforms.
    """
    if sys.platform != "darwin":
        return
    if not shutil.which("xattr"):
        logger.warning("xattr not found; cannot strip macOS quarantine flag")
        return
    try:
        subprocess.run(
            ["xattr", "-dr", "com.apple.quarantine", str(path)],
            check=False,
            capture_output=True,
        )
        logger.info(f"Stripped com.apple.quarantine from {path}")
    except Exception as e:  # pragma: no cover - best-effort
        logger.warning(f"Could not strip quarantine on {path}: {e}")


def _verify_executable(path: Path) -> bool:
    """Return True if the binary can produce a version string."""
    try:
        result = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.warning(f"Binary {path} failed to execute: {e}")
        return False


def _install_from_release(version: str) -> Path:
    binary_path = get_binary_path()
    binary_path.parent.mkdir(parents=True, exist_ok=True)

    asset = get_platform_asset_name(version)
    url = f"{GITHUB_DOWNLOAD}/{version}/{asset}"

    tmp_zip = binary_path.parent / asset
    _download(url, tmp_zip)

    try:
        with zipfile.ZipFile(io.BytesIO(tmp_zip.read_bytes())) as zf:
            # Find the sldl binary inside the archive
            wanted = _binary_name()
            members = [m for m in zf.namelist() if m.endswith(wanted)]
            if not members:
                raise BinaryError(f"{asset} did not contain {wanted}")
            with zf.open(members[0]) as src, open(binary_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
    finally:
        tmp_zip.unlink(missing_ok=True)

    binary_path.chmod(binary_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    _strip_macos_quarantine(binary_path)

    _version_file().write_text(version)
    logger.info(f"Installed sldl {version} at {binary_path}")
    return binary_path


def _build_from_source(project_root: Path) -> Path:
    """Build sldl from the src/slsk-batchdl submodule using `dotnet publish`.

    Used as a fallback when the downloaded binary is blocked (e.g. unsigned on
    macOS) and on platforms/architectures without a prebuilt release.
    """
    src_dir = project_root / "src" / "slsk-batchdl"
    if not src_dir.exists() or not any(src_dir.iterdir()):
        raise BinaryError(
            f"Submodule not initialized at {src_dir}. "
            "Run: git submodule update --init --recursive"
        )
    if not shutil.which("dotnet"):
        raise BinaryError(
            "dotnet SDK not found. Install .NET 8 SDK to build sldl from source, "
            "or set TOOLCRATE_SLDL_VERSION to a working prebuilt release."
        )

    system = sys.platform
    machine = platform.machine().lower()
    if system == "darwin":
        rid = "osx-arm64" if machine in ("arm64", "aarch64") else "osx-x64"
    elif system == "linux":
        rid = "linux-arm64" if machine in ("arm64", "aarch64") else "linux-x64"
    elif system == "win32":
        rid = "win-x64"
    else:
        raise BinaryError(f"Unsupported platform: {system}/{machine}")

    out_dir = _data_dir() / "bin"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Building sldl from source ({rid}) — this may take a minute")
    result = subprocess.run(
        [
            "dotnet", "publish",
            "-c", "Release",
            "-r", rid,
            "--self-contained",
            "-o", str(out_dir),
        ],
        cwd=str(src_dir),
    )
    if result.returncode != 0:
        raise BinaryError(f"dotnet publish failed with exit code {result.returncode}")

    binary_path = out_dir / _binary_name()
    if not binary_path.exists():
        raise BinaryError(f"Build succeeded but {binary_path} is missing")

    binary_path.chmod(binary_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    _version_file().write_text("source-build")
    logger.info(f"Built sldl at {binary_path}")
    return binary_path


def ensure_sldl_binary(
    project_root: Path | None = None,
    force_refresh: bool = False,
) -> Path:
    """Return a path to a working sldl binary, installing or building if needed.

    Order of operations:
      1. If the binary already exists and executes, return it (unless force_refresh).
      2. If TOOLCRATE_SLDL_BUILD_FROM_SOURCE is set, build from submodule.
      3. Otherwise, download the pinned/latest release, strip quarantine, verify.
      4. If verification fails (common on macOS due to code signing), fall back
         to building from source.
    """
    binary_path = get_binary_path()

    if not force_refresh and binary_path.exists() and _verify_executable(binary_path):
        return binary_path

    if os.environ.get(ENV_BUILD_FROM_SOURCE):
        if project_root is None:
            raise BinaryError("project_root required for source build")
        return _build_from_source(project_root)

    try:
        version = resolve_latest_version()
        installed = _install_from_release(version)
        if _verify_executable(installed):
            return installed
        logger.warning(
            "Downloaded sldl binary failed to execute (likely a macOS signing "
            "issue). Falling back to building from source."
        )
    except BinaryError as e:
        logger.warning(f"Release download failed: {e}. Attempting source build.")

    if project_root is None:
        raise BinaryError(
            "Downloaded sldl binary is not executable and no project_root was "
            "provided for the source-build fallback."
        )
    return _build_from_source(project_root)
