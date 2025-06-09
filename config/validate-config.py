#!/usr/bin/env python3
"""Configuration validation script for ToolCrate."""

import os
import sys

# Check if we're in a virtual environment
if not os.environ.get('VIRTUAL_ENV'):
    print("❌ Virtual environment not active!")
    print("Please activate the virtual environment first:")
    print("  source .venv/bin/activate")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("❌ PyYAML not installed in virtual environment.")
    print("Install with: pip install PyYAML")
    sys.exit(1)

import sys
from pathlib import Path

def validate_config(config_path):
    """Validate the ToolCrate YAML configuration."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        errors = []
        warnings = []

        # Check required sections
        required_sections = ['general', 'slsk_batchdl', 'spotify', 'youtube', 'cron', 'mounts']
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")

        # Validate slsk_batchdl settings
        if 'slsk_batchdl' in config:
            slsk = config['slsk_batchdl']

            if not slsk.get('username'):
                warnings.append("Soulseek username not configured")
            if not slsk.get('password'):
                warnings.append("Soulseek password not configured")

            # Check numeric values
            numeric_fields = ['concurrent_processes', 'search_timeout', 'listen_port']
            for field in numeric_fields:
                if field in slsk and not isinstance(slsk[field], int):
                    errors.append(f"Field {field} must be an integer")

        # Validate directory paths
        if 'general' in config:
            for dir_field in ['data_directory', 'log_directory']:
                if dir_field in config['general']:
                    path = Path(config['general'][dir_field])
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

    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        return False

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "toolcrate.yaml"
    is_valid = validate_config(config_path)
    sys.exit(0 if is_valid else 1)
