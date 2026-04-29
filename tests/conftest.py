"""Shared fixtures and configuration for ToolCrate tests."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from toolcrate.db.models import Base
from toolcrate.db.session import create_engine_for_url, get_async_session_factory


TEST_TOKEN = "test-token"
TEST_TOKEN_HASH = hashlib.sha256(TEST_TOKEN.encode()).hexdigest()


@pytest.fixture
async def session_factory():
    engine = create_engine_for_url("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_async_session_factory(engine)
    yield factory
    await engine.dispose()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_TOKEN}", "Host": "localhost"}


@pytest.fixture
async def app(session_factory):
    """Build a wired FastAPI app for integration tests."""
    from toolcrate.web.app import create_app, AppDeps
    from toolcrate.web.routers.health import build_router as build_health
    from toolcrate.web.routers.lists import build_router as build_lists
    from toolcrate.web.routers.tracks import build_router as build_tracks
    from toolcrate.web.routers.jobs import build_router as build_jobs
    from toolcrate.core.jobs import JobQueue
    from toolcrate.core.source_lists import SourceListService

    src = SourceListService(session_factory, music_root="/tmp/m")
    queue = JobQueue(session_factory)

    deps = AppDeps(
        api_token_hash=TEST_TOKEN_HASH,
        allowed_hosts={"localhost", "127.0.0.1", "testserver"},
        routers=[
            build_health(version="0.1.0-test"),
            build_lists(src=src, queue=queue, token_hash=TEST_TOKEN_HASH),
            build_tracks(src=src, session_factory=session_factory, queue=queue, token_hash=TEST_TOKEN_HASH),
            build_jobs(queue=queue, session_factory=session_factory, token_hash=TEST_TOKEN_HASH),
        ],
    )
    return create_app(deps)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_project_root(temp_dir):
    """Mock project root directory with setup.py."""
    setup_py = temp_dir / "setup.py"
    setup_py.write_text("# Mock setup.py")
    return temp_dir


@pytest.fixture
def mock_subprocess():
    """Mock subprocess module."""
    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.CalledProcessError") as mock_error,
    ):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def mock_shutil():
    """Mock shutil module."""
    with patch("shutil.which") as mock_which:
        yield mock_which


@pytest.fixture
def mock_os_execv():
    """Mock os.execv to prevent actual execution."""
    with patch("os.execv") as mock_execv:
        yield mock_execv


@pytest.fixture
def mock_os_execvp():
    """Mock os.execvp to prevent actual execution."""
    with patch("os.execvp") as mock_execvp:
        yield mock_execvp


@pytest.fixture
def mock_sys_exit():
    """Mock sys.exit to prevent actual exit."""
    with patch("sys.exit") as mock_exit:
        yield mock_exit


@pytest.fixture
def mock_click_echo():
    """Mock click.echo for testing output."""
    with patch("click.echo") as mock_echo:
        yield mock_echo


@pytest.fixture
def mock_logger():
    """Mock loguru logger."""
    with patch("loguru.logger") as mock_log:
        yield mock_log


@pytest.fixture
def mock_file_system(temp_dir):
    """Mock file system operations."""
    # Create mock directory structure
    src_dir = temp_dir / "src"
    src_dir.mkdir()

    # Mock bin directory
    bin_dir = src_dir / "bin"
    bin_dir.mkdir()

    # Mock slsk-batchdl directory
    slsk_dir = src_dir / "slsk-batchdl"
    slsk_dir.mkdir()

    # Mock Shazam-Tool directory
    shazam_dir = src_dir / "Shazam-Tool"
    shazam_dir.mkdir()

    return {
        "root": temp_dir,
        "src": src_dir,
        "bin": bin_dir,
        "slsk": slsk_dir,
        "shazam": shazam_dir,
    }


@pytest.fixture
def mock_audio_file(temp_dir):
    """Create a mock audio file for testing."""
    audio_file = temp_dir / "test_audio.mp3"
    audio_file.write_bytes(b"fake mp3 content")
    return audio_file


@pytest.fixture
def mock_shazam_dependencies():
    """Mock Shazam tool dependencies."""
    with (
        patch("pydub.AudioSegment") as mock_audio,
        patch("shazamio.Shazam") as mock_shazam,
        patch("yt_dlp.YoutubeDL") as mock_ytdl,
    ):
        yield {"audio": mock_audio, "shazam": mock_shazam, "ytdl": mock_ytdl}


@pytest.fixture
def sample_shazam_response():
    """Sample Shazam API response for testing."""
    return {"track": {"title": "Test Song", "subtitle": "Test Artist"}}


@pytest.fixture
def mock_environment_variables():
    """Mock environment variables."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
