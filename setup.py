#!/usr/bin/env python3
"""Setuptools compatibility shim.

Tool installation is intentionally explicit. Run `toolcrate tools install`
after installing the Python package to build or link the external binaries.
"""

from setuptools import find_packages, setup

if __name__ == "__main__":
    setup(
        name="toolcrate",
        version="0.1.0",
        description="A unified tool suite for music management and processing",
        author="User",
        author_email="user@example.com",
        package_dir={"": "src"},
        packages=find_packages(where="src"),
        install_requires=[
            "click>=8.1.3",
            "loguru>=0.7.0",
            "pydub>=0.25.1",
            "shazamio>=0.6.0",
            "yt-dlp>=2024.1.0",
        ],
        entry_points={
            "console_scripts": [
                "toolcrate=toolcrate.cli.main:main",
                "slsk-tool=toolcrate.cli.wrappers:run_slsk",
                "shazam-tool=toolcrate.cli.wrappers:run_shazam",
                "mdl-tool=toolcrate.cli.wrappers:run_mdl",
            ],
        },
        python_requires=">=3.8",
    )
