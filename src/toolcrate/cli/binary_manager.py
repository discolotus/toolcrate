"""Install and locate ToolCrate-managed command line tools."""

from __future__ import annotations

import os
import importlib.util
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

APP_DIR_ENV = "TOOLCRATE_HOME"


@dataclass(frozen=True)
class ToolStatus:
    name: str
    command: str
    managed_path: Path
    system_path: Optional[str]
    installed: bool
    note: str = ""


@dataclass(frozen=True)
class ToolCheckResult:
    name: str
    command: str
    executable: Optional[str]
    ok: bool
    returncode: Optional[int]
    output: str
    error: str = ""


def project_root() -> Path:
    current_dir = Path(__file__).resolve()
    for parent in current_dir.parents:
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return parent
    return current_dir.parents[3]


def toolcrate_home() -> Path:
    override = os.environ.get(APP_DIR_ENV)
    if override:
        return Path(override).expanduser()

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "toolcrate"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(base) / "toolcrate"
    return (
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        / "toolcrate"
    )


def managed_bin_dir() -> Path:
    return toolcrate_home() / "bin"


def managed_tools_dir() -> Path:
    return toolcrate_home() / "tools"


def managed_executable(command: str) -> Path:
    suffix = ".cmd" if sys.platform == "win32" else ""
    return managed_bin_dir() / f"{command}{suffix}"


def make_executable(path: Path) -> None:
    if sys.platform != "win32":
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def find_managed(command: str) -> Optional[Path]:
    path = managed_executable(command)
    if path.exists() and os.access(path, os.X_OK):
        return path
    return None


def find_executable(command: str) -> Optional[str]:
    managed = find_managed(command)
    if managed:
        return str(managed)
    return shutil.which(command)


def python_module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def tool_statuses() -> List[ToolStatus]:
    commands = [
        ("slsk-batchdl", "sldl", shutil.which("sldl"), "managed sldl or system sldl"),
        ("shazam-tool", "shazam-tool", None, "managed shim only"),
        (
            "mdl-tool",
            "mdl-tool",
            shutil.which("mdl-utils"),
            "managed shim; mdl-utils or built-in metadata fallback",
        ),
    ]
    statuses = []
    for name, command, system, note in commands:
        managed = managed_executable(command)
        statuses.append(
            ToolStatus(
                name=name,
                command=command,
                managed_path=managed,
                system_path=system,
                installed=(managed.exists() and os.access(managed, os.X_OK))
                or system is not None,
                note=note,
            )
        )
    return statuses


def verify_command_for_tool(command: str) -> List[str]:
    if command == "sldl":
        return ["--version"]
    return ["--help"]


def executable_for_status(status: ToolStatus) -> Optional[str]:
    if status.command in {"shazam-tool", "mdl-tool"}:
        managed = find_managed(status.command)
        return str(managed) if managed else None
    return find_executable(status.command)


def verify_tools(timeout: int = 10) -> List[ToolCheckResult]:
    results = []
    for status in tool_statuses():
        executable = executable_for_status(status)
        if executable is None:
            results.append(
                ToolCheckResult(
                    name=status.name,
                    command=status.command,
                    executable=None,
                    ok=False,
                    returncode=None,
                    output="",
                    error="not installed",
                )
            )
            continue

        try:
            completed = subprocess.run(
                [executable] + verify_command_for_tool(status.command),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001 - converted to check result.
            results.append(
                ToolCheckResult(
                    name=status.name,
                    command=status.command,
                    executable=executable,
                    ok=False,
                    returncode=None,
                    output="",
                    error=str(exc),
                )
            )
            continue

        output = "\n".join(
            part.strip()
            for part in [completed.stdout, completed.stderr]
            if part and part.strip()
        )
        results.append(
            ToolCheckResult(
                name=status.name,
                command=status.command,
                executable=executable,
                ok=completed.returncode == 0,
                returncode=completed.returncode,
                output=output,
            )
        )
    return results


def platform_runtime() -> str:
    machine = os.uname().machine if hasattr(os, "uname") else ""
    if sys.platform == "darwin":
        return "osx-arm64" if machine == "arm64" else "osx-x64"
    if sys.platform.startswith("linux"):
        return "linux-arm64" if machine in {"aarch64", "arm64"} else "linux-x64"
    if sys.platform == "win32":
        return "win-x64"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def run(command: List[str], cwd: Optional[Path] = None) -> None:
    subprocess.run(command, cwd=str(cwd) if cwd else None, check=True)


def install_sldl() -> Path:
    """Install the sldl executable into ToolCrate's managed bin directory."""
    managed_bin_dir().mkdir(parents=True, exist_ok=True)
    managed_tools_dir().mkdir(parents=True, exist_ok=True)

    root = project_root()
    source_binary_candidates = [
        root / "src" / "bin" / "sldl",
        root / "src" / "slsk-batchdl" / "bin" / platform_runtime() / "sldl",
    ]
    for candidate in source_binary_candidates:
        if candidate.exists():
            runtime_dir = managed_tools_dir() / "sldl"
            if runtime_dir.exists():
                shutil.rmtree(runtime_dir)
            shutil.copytree(candidate.parent, runtime_dir)
            runtime_binary = runtime_dir / candidate.name
            make_executable(runtime_binary)
            return write_exec_wrapper("sldl", runtime_binary)

    source_dir = root / "src" / "slsk-batchdl"
    if source_dir.exists() and shutil.which("dotnet"):
        output_dir = managed_tools_dir() / "sldl"
        output_dir.mkdir(parents=True, exist_ok=True)
        run(
            [
                "dotnet",
                "publish",
                "slsk-batchdl/slsk-batchdl.csproj",
                "-c",
                "Release",
                "-r",
                platform_runtime(),
                "--self-contained",
                "-o",
                str(output_dir),
            ],
            cwd=source_dir,
        )
        binary_name = "sldl.exe" if sys.platform == "win32" else "sldl"
        built_binary = output_dir / binary_name
        if not built_binary.exists():
            raise RuntimeError(
                f"dotnet publish completed, but {built_binary} was not created"
            )
        make_executable(built_binary)
        return write_exec_wrapper("sldl", built_binary)

    if sys.platform == "darwin" and platform_runtime() == "osx-arm64":
        return download_sldl_release("v2.4.6", "sldl_osx-arm64.zip")

    raise RuntimeError(
        "Could not install sldl. Initialize src/slsk-batchdl and install dotnet, "
        "or place a compatible sldl binary at src/bin/sldl."
    )


def download_sldl_release(version: str, archive_name: str) -> Path:
    managed_bin_dir().mkdir(parents=True, exist_ok=True)
    download_dir = managed_tools_dir() / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    archive_path = download_dir / archive_name
    url = f"https://github.com/gfrancesco-ul/slsk-batchdl/releases/download/{version}/{archive_name}"
    urllib.request.urlretrieve(url, archive_path)

    extract_dir = managed_tools_dir() / "sldl-release"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extract_dir)

    binary = next((path for path in extract_dir.rglob("sldl") if path.is_file()), None)
    if binary is None:
        raise RuntimeError(f"No sldl executable found in {archive_path}")
    make_executable(binary)
    return write_exec_wrapper("sldl", binary)


def write_script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    make_executable(path)
    return path


def write_exec_wrapper(command: str, target: Path) -> Path:
    script = f"""#!/usr/bin/env bash
set -euo pipefail
exec {shlex_quote(str(target))} "$@"
"""
    return write_script(managed_executable(command), script)


def install_shazam_tool() -> Path:
    root = project_root()
    shazam_script = root / "src" / "Shazam-Tool" / "shazam.py"
    if not shazam_script.exists():
        raise RuntimeError(
            "Could not find src/Shazam-Tool/shazam.py. Initialize the Shazam-Tool submodule first."
        )

    script = f"""#!/usr/bin/env bash
set -euo pipefail
exec {shlex_quote(sys.executable)} {shlex_quote(str(shazam_script))} "$@"
"""
    return write_script(managed_executable("shazam-tool"), script)


def install_mdl_tool() -> Path:
    existing = shutil.which("mdl-utils")
    if existing:
        script = f"""#!/usr/bin/env bash
set -euo pipefail
exec {shlex_quote(existing)} "$@"
"""
    elif python_module_available("mdl_utils.cli"):
        script = f"""#!/usr/bin/env bash
set -euo pipefail
exec {shlex_quote(sys.executable)} -m mdl_utils.cli "$@"
"""
    else:
        script = f"""#!/usr/bin/env bash
set -euo pipefail
exec {shlex_quote(sys.executable)} -m toolcrate.cli.mdl "$@"
"""
    return write_script(managed_executable("mdl-tool"), script)


def install_all() -> Dict[str, Path]:
    return {
        "sldl": install_sldl(),
        "shazam-tool": install_shazam_tool(),
        "mdl-tool": install_mdl_tool(),
    }


def shlex_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
