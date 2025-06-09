#!/usr/bin/env python3
"""
ToolCrate Configuration Manager

This script helps manage the YAML configuration and generates compatible
configuration files for integrated tools.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Check if we're in a virtual environment (Poetry or manual)
# Skip this check in Docker containers or when TOOLCRATE_SKIP_VENV_CHECK is set
skip_venv_check = (
    os.environ.get("TOOLCRATE_SKIP_VENV_CHECK")
    or os.environ.get("TOOLCRATE_TESTING")
    or os.environ.get("PYTEST_CURRENT_TEST")
    or "pytest" in sys.modules
    or "test" in sys.argv[0].lower()
    or os.path.exists("/.dockerenv")  # Docker container indicator
    or os.environ.get("CONTAINER")  # Generic container indicator
    or os.environ.get("DOCKER_CONTAINER")  # Another container indicator
)

if not skip_venv_check:
    # Poetry runs in its own environment, so we check for both
    in_venv = os.environ.get("VIRTUAL_ENV") or os.environ.get("POETRY_ACTIVE")
    if not in_venv:
        # Try to detect if we're running under Poetry
        import subprocess

        try:
            result = subprocess.run(
                ["poetry", "env", "info", "--path"],
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip():
                # We're likely running under Poetry
                in_venv = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    if not in_venv:
        print("❌ Virtual environment not active!")
        print("Please use one of these methods:")
        print("  poetry run python config_manager.py <command>")
        print("  source .venv/bin/activate && python config_manager.py <command>")
        print("  make config-<command>")
        sys.exit(1)

try:
    import yaml
except ImportError:
    print("❌ PyYAML not installed in virtual environment.")
    print("Install with: pip install PyYAML")
    sys.exit(1)


class ConfigManager:
    """Manages ToolCrate configuration files."""

    def __init__(self, config_path: str = "config/toolcrate.yaml"):
        # Import here to avoid circular imports
        from ..cli.wrappers import get_project_root

        # Determine the project root
        self.project_root = get_project_root()

        # Handle both absolute and relative config paths
        if Path(config_path).is_absolute():
            self.config_path = Path(config_path)
        else:
            self.config_path = self.project_root / config_path

        self.config_dir = self.config_path.parent
        self.config = {}

        # Ensure config directory exists (but don't fail if we can't create it)
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            # In test environments or restricted environments, we might not be able to create directories
            # This is okay - we'll handle missing directories when we actually need to write files
            pass

    def load_config(self) -> Dict[str, Any]:
        """Load the YAML configuration."""
        try:
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f)
            return self.config
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"❌ YAML parsing error: {e}")
            sys.exit(1)

    def save_config(self):
        """Save the YAML configuration.

        Note: This will reformat the YAML file and remove comments.
        For preserving comments, manually edit the file instead.
        """
        import warnings

        warnings.warn(
            "save_config() will reformat YAML and remove comments. "
            "Consider manually editing config/toolcrate.yaml to preserve formatting.",
            UserWarning,
        )

        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
        print(f"✅ Configuration saved to {self.config_path}")
        print("⚠️  Note: YAML formatting and comments may have been lost.")

    def update_cron_section(self, cron_config):
        """Update just the cron section in the YAML file while preserving formatting.

        This is a safer alternative to save_config() for cron updates.
        """
        import re

        try:
            with open(self.config_path, "r") as f:
                content = f.read()

            # Find the cron section and replace it
            cron_yaml = yaml.dump(
                {"cron": cron_config}, default_flow_style=False, indent=2
            )
            cron_section = cron_yaml.replace("cron:\n", "").rstrip()

            # Use regex to replace the cron section
            pattern = r"^cron:\s*\n((?:  .*\n)*)"
            replacement = f"cron:\n{cron_section}\n"

            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

            with open(self.config_path, "w") as f:
                f.write(new_content)

            # Update our in-memory config
            self.config["cron"] = cron_config

            print(f"✅ Updated cron section in {self.config_path}")

        except Exception as e:
            print(f"⚠️  Could not update cron section safely: {e}")
            print("💡 Falling back to full config save...")
            self.save_config()

    def generate_sldl_conf(self):
        """Generate sldl.conf from YAML configuration."""
        if not self.config:
            self.load_config()

        slsk_config = self.config.get("slsk_batchdl", {})
        spotify_config = self.config.get("spotify", {})
        youtube_config = self.config.get("youtube", {})

        sldl_conf_path = self.config_dir / "sldl.conf"

        with open(sldl_conf_path, "w") as f:
            f.write("# sldl.conf - Generated from toolcrate.yaml\n")
            f.write(
                "# This file is automatically generated. Edit toolcrate.yaml instead.\n\n"
            )

            # Authentication
            if slsk_config.get("username"):
                f.write(f"username = {slsk_config['username']}\n")
            if slsk_config.get("password"):
                f.write(f"password = {slsk_config['password']}\n")
            f.write("\n")

            # Directories
            dir_mappings = {
                "parent_dir": "path",
                "skip_music_dir": "skip-music-dir",
                "index_file_path": "index-path",
                "m3u_file_path": "playlist-path",
                "failed_album_path": "failed-album-path",
                "log_file_path": "log-file",
            }

            for yaml_key, conf_key in dir_mappings.items():
                if slsk_config.get(yaml_key):
                    # Convert host paths to container paths for Docker execution
                    path_value = slsk_config[yaml_key]
                    if isinstance(path_value, str):
                        # Convert toolcrate paths to container paths
                        if "toolcrate/data" in path_value:
                            # Replace toolcrate/data with /data
                            container_path = (
                                "/data" + path_value.split("toolcrate/data")[1]
                            )
                        elif "toolcrate/logs" in path_value:
                            # Replace toolcrate/logs with /data (logs go in data directory)
                            container_path = (
                                "/data" + path_value.split("toolcrate/logs")[1]
                            )
                        else:
                            # Default: assume it should go in /data
                            container_path = "/data/" + path_value.split("/")[-1]

                        f.write(f"{conf_key} = {container_path}\n")
                    else:
                        f.write(f"{conf_key} = {path_value}\n")
            f.write("\n")

            # Preferred conditions
            pref_cond = slsk_config.get("preferred_conditions", {})
            if pref_cond.get("formats"):
                formats = ",".join(pref_cond["formats"])
                f.write(f"pref-format = {formats}\n")

            pref_mappings = {
                "min_bitrate": "pref-min-bitrate",
                "max_bitrate": "pref-max-bitrate",
                "max_sample_rate": "pref-max-samplerate",
                "length_tolerance": "pref-length-tol",
            }

            for yaml_key, conf_key in pref_mappings.items():
                if pref_cond.get(yaml_key) is not None:
                    f.write(f"{conf_key} = {pref_cond[yaml_key]}\n")

            if pref_cond.get("strict_title"):
                f.write("strict-title = true\n")
            if pref_cond.get("strict_album"):
                f.write("strict-album = true\n")
            f.write("\n")

            # Search and download settings
            search_mappings = {
                "concurrent_processes": "concurrent-downloads",
                "search_timeout": "search-timeout",
                "listen_port": "listen-port",
                "max_stale_time": "max-stale-time",
                "searches_per_time": "searches-per-time",
                "search_renew_time": "searches-renew-time",
                "min_shares_aggregate": "min-shares-aggregate",
                "aggregate_length_tol": "aggregate-length-tol",
            }

            for yaml_key, conf_key in search_mappings.items():
                if slsk_config.get(yaml_key) is not None:
                    f.write(f"{conf_key} = {slsk_config[yaml_key]}\n")

            # Boolean flags (using inverted logic for skip/write flags)
            bool_mappings = {
                "fast_search": "fast-search",
                "interactive_mode": "interactive",
                "remove_tracks_from_source": "remove-from-source",
                "desperate_search": "desperate",
                "album": "album",
                "aggregate": "aggregate",
                "album_art_only": "album-art-only",
                "artist_maybe_wrong": "artist-maybe-wrong",
                "yt_parse": "yt-parse",
                "remove_ft": "remove-ft",
                "reverse": "reverse",
                "use_ytdlp": "yt-dlp",
                "get_deleted": "get-deleted",
                "deleted_only": "deleted-only",
                "no_browse_folder": "no-browse-folder",
                "no_progress": "no-progress",
                "write_playlist": "write-playlist",
            }

            for yaml_key, conf_key in bool_mappings.items():
                if slsk_config.get(yaml_key) is True:
                    f.write(f"{conf_key} = true\n")

            # Handle inverted boolean flags
            if not slsk_config.get("skip_existing", True):
                f.write("no-skip-existing = true\n")
            if not slsk_config.get("write_index", True):
                f.write("no-write-index = true\n")
            f.write("\n")

            # String settings (only write non-empty values)
            string_mappings = {
                "ytdlp_argument": "yt-dlp-argument",
                "parse_title_template": "parse-title-template",
            }

            for yaml_key, conf_key in string_mappings.items():
                value = slsk_config.get(yaml_key)
                if value and str(value).strip():
                    f.write(f"{conf_key} = {value}\n")

            # API credentials
            if spotify_config.get("client_id"):
                f.write(f"spotify-id = {spotify_config['client_id']}\n")
            if spotify_config.get("client_secret"):
                f.write(f"spotify-secret = {spotify_config['client_secret']}\n")
            if youtube_config.get("api_key"):
                f.write(f"youtube-key = {youtube_config['api_key']}\n")
            f.write("\n")

            # Profiles
            profiles = self.config.get("profiles", {})
            for profile_name, profile_config in profiles.items():
                f.write(f"[{profile_name}]\n")
                profile_settings = profile_config.get("settings", {})

                # Handle profile-specific settings
                if "preferred_conditions" in profile_settings:
                    pref = profile_settings["preferred_conditions"]
                    if pref.get("formats"):
                        formats = ",".join(pref["formats"])
                        f.write(f"pref-format = {formats}\n")
                    for yaml_key, conf_key in pref_mappings.items():
                        if pref.get(yaml_key) is not None:
                            f.write(f"{conf_key} = {pref[yaml_key]}\n")

                # Handle other profile settings
                for yaml_key, conf_key in bool_mappings.items():
                    if profile_settings.get(yaml_key) is True:
                        f.write(f"{conf_key} = true\n")

                f.write("\n")

        print(f"✅ Generated sldl.conf at {sldl_conf_path}")

    def generate_wishlist_sldl_conf(self):
        """Generate a wishlist-specific sldl.conf from YAML configuration."""
        if not self.config:
            self.load_config()

        # Get base slsk config and wishlist overrides
        slsk_config = self.config.get("slsk_batchdl", {})
        wishlist_config = self.config.get("wishlist", {})
        wishlist_settings = wishlist_config.get("settings", {})

        # Merge settings (wishlist settings override base settings)
        merged_config = slsk_config.copy()
        merged_config.update(wishlist_settings)

        spotify_config = self.config.get("spotify", {})
        youtube_config = self.config.get("youtube", {})

        sldl_conf_path = self.config_dir / "sldl-wishlist.conf"

        with open(sldl_conf_path, "w") as f:
            f.write(
                "# sldl-wishlist.conf - Generated from toolcrate.yaml for wishlist processing\n"
            )
            f.write(
                "# This file is automatically generated. Edit toolcrate.yaml instead.\n\n"
            )

            # Authentication
            if merged_config.get("username"):
                f.write(f"username = {merged_config['username']}\n")
            if merged_config.get("password"):
                f.write(f"password = {merged_config['password']}\n")
            f.write("\n")

            # Directories - use wishlist-specific paths with container path conversion
            download_dir = wishlist_config.get(
                "download_dir", merged_config.get("parent_dir", "/data/library")
            )
            # Convert host paths to container paths for Docker execution
            if isinstance(download_dir, str):
                if download_dir.startswith("/data"):
                    # Already a container path
                    pass
                elif "toolcrate/data" in download_dir:
                    download_dir = "/data" + download_dir.split("toolcrate/data")[1]
                elif "toolcrate/logs" in download_dir:
                    download_dir = "/data" + download_dir.split("toolcrate/logs")[1]
                else:
                    # Default: use library subdirectory
                    download_dir = "/data/library"
            f.write(f"path = {download_dir}\n")

            # Handle other directory paths with conversion
            dir_mappings = {
                "skip_music_dir": "skip-music-dir",
                "m3u_file_path": "playlist-path",
                "failed_album_path": "failed-album-path",
                "log_file_path": "log-file",
            }

            for yaml_key, conf_key in dir_mappings.items():
                if merged_config.get(yaml_key):
                    path_value = merged_config[yaml_key]
                    if isinstance(path_value, str):
                        # Convert toolcrate paths to container paths
                        if path_value.startswith("/data"):
                            # Already a container path
                            container_path = path_value
                        elif "toolcrate/data" in path_value:
                            container_path = (
                                "/data" + path_value.split("toolcrate/data")[1]
                            )
                        elif "toolcrate/logs" in path_value:
                            container_path = (
                                "/data" + path_value.split("toolcrate/logs")[1]
                            )
                        else:
                            # Default: use filename in /data
                            container_path = "/data/" + path_value.split("/")[-1]
                        f.write(f"{conf_key} = {container_path}\n")
                    else:
                        f.write(f"{conf_key} = {path_value}\n")

            # Index path handling for wishlist
            if wishlist_config.get("index_in_playlist_folder", True):
                # Let slsk-batchdl use default behavior (index in playlist folder)
                pass
            else:
                # Use global wishlist index
                f.write("index-path = /data/wishlist-index.sldl\n")
            f.write("\n")

            # Audio quality preferences
            if "preferred_conditions" in merged_config:
                pref = merged_config["preferred_conditions"]
                if pref.get("formats"):
                    formats_str = ",".join(pref["formats"])
                    f.write(f"pref-format = {formats_str}\n")
                if pref.get("min_bitrate"):
                    f.write(f"pref-min-bitrate = {pref['min_bitrate']}\n")
                if pref.get("max_bitrate"):
                    f.write(f"pref-max-bitrate = {pref['max_bitrate']}\n")
                if pref.get("max_sample_rate"):
                    f.write(f"pref-max-samplerate = {pref['max_sample_rate']}\n")
                if pref.get("length_tolerance"):
                    f.write(f"pref-length-tol = {pref['length_tolerance']}\n")
                if pref.get("strict_title"):
                    f.write(
                        f"pref-strict-title = {str(pref['strict_title']).lower()}\n"
                    )
                if pref.get("strict_album"):
                    f.write(
                        f"pref-strict-album = {str(pref['strict_album']).lower()}\n"
                    )
            f.write("\n")

            # Necessary conditions
            if "necessary_conditions" in merged_config:
                nec = merged_config["necessary_conditions"]
                if nec.get("formats"):
                    formats_str = ",".join(nec["formats"])
                    f.write(f"format = {formats_str}\n")
            f.write("\n")

            # Search and download settings
            search_mappings = {
                "concurrent_processes": "concurrent-downloads",
                "search_timeout": "search-timeout",
                "listen_port": "listen-port",
                "max_stale_time": "max-stale-time",
                "searches_per_time": "searches-per-time",
                "search_renew_time": "searches-renew-time",
                "min_shares_aggregate": "min-shares-aggregate",
                "aggregate_length_tol": "aggregate-length-tol",
                "max_retries_per_track": "max-retries",
                "unknown_error_retries": "unknown-error-retries",
            }

            for yaml_key, conf_key in search_mappings.items():
                if merged_config.get(yaml_key) is not None:
                    f.write(f"{conf_key} = {merged_config[yaml_key]}\n")
            f.write("\n")

            # Boolean settings
            bool_mappings = {
                "skip_existing": "skip-existing",
                "write_index": "write-index",
                "interactive_mode": "interactive",
                "remove_tracks_from_source": "remove-from-source",
                "desperate_search": "desperate",
                "fast_search": "fast-search",
                "use_ytdlp": "yt-dlp",
                "skip_check_pref_cond": "skip-check-pref-cond",
            }

            for yaml_key, conf_key in bool_mappings.items():
                if yaml_key in merged_config:
                    value = str(merged_config[yaml_key]).lower()
                    f.write(f"{conf_key} = {value}\n")
            f.write("\n")

            # API configurations
            if spotify_config.get("client_id"):
                f.write(f"spotify-id = {spotify_config['client_id']}\n")
            if spotify_config.get("client_secret"):
                f.write(f"spotify-secret = {spotify_config['client_secret']}\n")
            if youtube_config.get("api_key"):
                f.write(f"youtube-key = {youtube_config['api_key']}\n")

        print(f"✅ Generated wishlist sldl.conf at {sldl_conf_path}")

    def validate_config(self):
        """Validate the configuration."""
        if not self.config:
            self.load_config()

        errors = []
        warnings = []

        # Check required sections
        required_sections = [
            "general",
            "slsk_batchdl",
            "spotify",
            "youtube",
            "wishlist",
            "cron",
            "mounts",
        ]
        for section in required_sections:
            if section not in self.config:
                errors.append(f"Missing required section: {section}")

        # Validate slsk_batchdl settings
        if "slsk_batchdl" in self.config:
            slsk = self.config["slsk_batchdl"]

            if not slsk.get("username"):
                warnings.append("Soulseek username not configured")
            if not slsk.get("password"):
                warnings.append("Soulseek password not configured")

            # Check numeric values
            numeric_fields = ["concurrent_processes", "search_timeout", "listen_port"]
            for field in numeric_fields:
                if field in slsk and not isinstance(slsk[field], int):
                    errors.append(f"Field {field} must be an integer")

        # Validate directory paths
        if "general" in self.config:
            for dir_field in ["data_directory", "log_directory"]:
                if dir_field in self.config["general"]:
                    path = Path(self.config["general"][dir_field])
                    if not path.exists():
                        warnings.append(f"Directory does not exist: {path}")

        # Print results
        if errors:
            print("❌ Configuration errors found:")
            for error in errors:
                print(f"  - {error}")

        if warnings:
            print("⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"  - {warning}")

        if not errors and not warnings:
            print("✅ Configuration is valid!")

        return len(errors) == 0

    def generate_docker_compose(self):
        """Generate docker-compose.yml from YAML configuration."""
        if not self.config:
            self.load_config()

        mounts = self.config.get("mounts", {})
        environment = self.config.get("environment", {})

        # Get mount paths
        config_mount = mounts.get("config", {}).get("host_path", "./config")
        data_mount = mounts.get("data", {}).get("host_path", "./data")

        # Get environment variables
        tz = environment.get("TZ", "UTC")
        puid = environment.get("PUID", 1000)
        pgid = environment.get("PGID", 1000)

        docker_compose_path = self.config_dir / "docker-compose.yml"

        with open(docker_compose_path, "w") as f:
            f.write("# Docker Compose configuration for ToolCrate\n")
            import datetime

            f.write(
                f"# Generated from toolcrate.yaml on {datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Z %Y')}\n"
            )
            f.write("#\n")
            f.write(f"# Mount paths: {config_mount} → /config, {data_mount} → /data\n")
            f.write("# Run from project root directory when using relative paths\n\n")

            f.write("services:\n")

            # ToolCrate main service
            f.write("  toolcrate:\n")
            f.write("    build:\n")
            f.write("      context: ..\n")
            f.write("      dockerfile: Dockerfile\n")
            f.write("    image: toolcrate:latest\n")
            f.write("    container_name: toolcrate\n")
            f.write("    environment:\n")
            f.write(f"      - TZ={tz}\n")
            f.write(f"      - PUID={puid}\n")
            f.write(f"      - PGID={pgid}\n")
            f.write("      - PYTHONPATH=/app/src\n")
            f.write("      - PYTHONUNBUFFERED=1\n")
            f.write("    volumes:\n")
            f.write(f"      - {config_mount}:/config\n")
            f.write(f"      - {data_mount}:/data\n")
            f.write("    restart: unless-stopped\n")
            f.write("    networks:\n")
            f.write("      - toolcrate-network\n")
            f.write("    working_dir: /app\n")
            f.write('    command: ["tail", "-f", "/dev/null"]\n\n')

            # SLDL service
            f.write("  sldl:\n")
            f.write("    build:\n")
            f.write("      context: ../src/slsk-batchdl\n")
            f.write("      dockerfile: Dockerfile\n")
            f.write("    image: slsk-batchdl:latest\n")
            f.write("    container_name: sldl\n")
            f.write("    environment:\n")
            f.write(f"      - TZ={tz}\n")
            f.write(f"      - PUID={puid}\n")
            f.write(f"      - PGID={pgid}\n")
            f.write("    volumes:\n")
            f.write(f"      - {config_mount}:/config\n")
            f.write(f"      - {data_mount}:/data\n")
            f.write("    restart: unless-stopped\n")
            f.write("    networks:\n")
            f.write("      - toolcrate-network\n\n")

            f.write("networks:\n")
            f.write("  toolcrate-network:\n")
            f.write("    driver: bridge\n\n")

            f.write("volumes:\n")
            f.write("  config:\n")
            f.write("    driver: local\n")
            f.write("    driver_opts:\n")
            f.write("      type: none\n")
            f.write("      o: bind\n")
            f.write(f"      device: {config_mount}\n")
            f.write("  data:\n")
            f.write("    driver: local\n")
            f.write("    driver_opts:\n")
            f.write("      type: none\n")
            f.write("      o: bind\n")
            f.write(f"      device: {data_mount}\n")

        print(f"✅ Generated docker-compose.yml at {docker_compose_path}")

    def check_mount_changes(self):
        """Check if mount paths have changed and rebuild containers if needed."""
        if not self.config:
            self.load_config()

        docker_compose_path = self.config_dir / "docker-compose.yml"

        if not docker_compose_path.exists():
            print("📦 No existing docker-compose.yml found, generating new one...")
            self.generate_docker_compose()
            return

        # Read current docker-compose.yml to check mount paths
        try:
            with open(docker_compose_path, "r") as f:
                current_compose = f.read()

            # Get current mount paths from config
            mounts = self.config.get("mounts", {})
            config_mount = mounts.get("config", {}).get("host_path", "./config")
            data_mount = mounts.get("data", {}).get("host_path", "./data")

            # Check if mount paths in docker-compose.yml match current config
            if (
                f"- {config_mount}:/config" in current_compose
                and f"- {data_mount}:/data" in current_compose
            ):
                print("✅ Mount paths unchanged, no container rebuild needed")
                return

            print("🔄 Mount paths changed, rebuilding containers...")

            # Stop and remove existing containers
            try:
                import subprocess

                print("🛑 Stopping existing containers...")
                subprocess.run(
                    ["docker-compose", "-f", str(docker_compose_path), "down"],
                    check=False,
                    capture_output=True,
                )

                # Remove containers if they exist
                for container in ["toolcrate", "sldl"]:
                    subprocess.run(
                        ["docker", "rm", "-f", container],
                        check=False,
                        capture_output=True,
                    )

            except Exception as e:
                print(f"⚠️  Warning: Could not stop containers: {e}")

            # Generate new docker-compose.yml
            self.generate_docker_compose()

            print("✅ Containers will use new mount paths on next startup")
            print(
                f"💡 To start containers: docker-compose -f {docker_compose_path} up -d"
            )

        except Exception as e:
            print(f"❌ Error checking mount changes: {e}")
            print("🔄 Regenerating docker-compose.yml...")
            self.generate_docker_compose()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ToolCrate Configuration Manager")
    parser.add_argument(
        "--config",
        "-c",
        default="config/toolcrate.yaml",
        help="Path to the YAML configuration file",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    subparsers.add_parser("validate", help="Validate the configuration")

    # Generate command
    subparsers.add_parser("generate-sldl", help="Generate sldl.conf from YAML")

    # Generate wishlist sldl command
    subparsers.add_parser(
        "generate-wishlist-sldl", help="Generate wishlist-specific sldl.conf from YAML"
    )

    # Generate docker-compose command
    subparsers.add_parser(
        "generate-docker", help="Generate docker-compose.yml from YAML"
    )

    # Check mount changes command
    subparsers.add_parser(
        "check-mounts", help="Check for mount changes and rebuild containers if needed"
    )

    # Show command
    subparsers.add_parser("show", help="Show current configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    config_manager = ConfigManager(args.config)

    if args.command == "validate":
        is_valid = config_manager.validate_config()
        sys.exit(0 if is_valid else 1)

    elif args.command == "generate-sldl":
        config_manager.generate_sldl_conf()

    elif args.command == "generate-wishlist-sldl":
        config_manager.generate_wishlist_sldl_conf()

    elif args.command == "generate-docker":
        config_manager.generate_docker_compose()

    elif args.command == "check-mounts":
        config_manager.check_mount_changes()

    elif args.command == "show":
        config = config_manager.load_config()
        print(yaml.dump(config, default_flow_style=False, indent=2))


if __name__ == "__main__":
    main()
