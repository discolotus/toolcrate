#!/usr/bin/env python3
"""Setup script for backward compatibility."""

import os
import subprocess
import sys
from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install

class SetupSubmodules:
    """Set up git submodules during installation."""
    
    def run_command(self, command):
        subprocess.check_call(command, shell=True)
    
    def initialize_submodules(self):
        """Initialize git submodules or clone the repositories if needed."""
        # Create src directory if it doesn't exist
        src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
        os.makedirs(src_dir, exist_ok=True)
        
        # Check if we're in a git repository
        if os.path.exists('.git'):
            print("Setting up git submodules...")
            # Initialize submodules and clone repositories
            self.run_command("git submodule update --init --recursive")
        else:
            print("Not a git repository, cloning tools directly...")
            # Handle sldl
            sldl_dir = os.path.join(src_dir, 'slsk-batchdl')
            if not os.path.exists(sldl_dir):
                self.run_command(f"git clone https://github.com/gfrancesco-ul/slsk-batchdl.git {sldl_dir}")
                self.run_command(f"cd {sldl_dir} && git checkout v2.4.6")
            
            # Handle Shazam-Tool
            shazam_dir = os.path.join(src_dir, 'Shazam-Tool')
            if not os.path.exists(shazam_dir):
                self.run_command(f"git clone https://github.com/in0vik/Shazam-Tool.git {shazam_dir}")
                self.run_command(f"cd {shazam_dir} && git checkout main")
            
            # Setup for macOS ARM64 version if on macOS
            if sys.platform == 'darwin' and os.uname().machine == 'arm64':
                # Determine if dotnet is available
                try:
                    subprocess.check_call("which dotnet", shell=True)
                    print("Building sldl for macOS ARM64...")
                    self.run_command(f"cd {sldl_dir} && dotnet publish -c Release -r osx-arm64 --self-contained -o bin/osx-arm64")
                except subprocess.CalledProcessError:
                    print("dotnet not found, downloading pre-built binary...")
                    self.run_command(f"mkdir -p {src_dir}/bin")
                    self.run_command(f"curl -L -o {src_dir}/sldl_osx-arm64.zip https://github.com/gfrancesco-ul/slsk-batchdl/releases/download/v2.4.6/sldl_osx-arm64.zip")
                    self.run_command(f"unzip {src_dir}/sldl_osx-arm64.zip -d {src_dir}/bin/")
                    self.run_command(f"chmod +x {src_dir}/bin/sldl")
                    self.run_command(f"rm {src_dir}/sldl_osx-arm64.zip")

class PostDevelopCommand(develop, SetupSubmodules):
    """Post-installation for development mode."""
    def run(self):
        self.initialize_submodules()
        develop.run(self)

class PostInstallCommand(install, SetupSubmodules):
    """Post-installation for installation mode."""
    def run(self):
        self.initialize_submodules()
        install.run(self)

if __name__ == "__main__":
    setup(
        name="toolcrate",
        version="0.1.0",
        description="A unified tool suite for music management and processing",
        author="User",
        author_email="user@example.com",
        package_dir={"": "src"},
        packages=find_packages(where="src"),
        include_package_data=True,
        install_requires=[
            "click>=8.1.3",
            "pydantic>=2.0.0",
            "loguru>=0.7.0",
        ],
        entry_points={
            "console_scripts": [
                "toolcrate=toolcrate.cli.main:main",
                "slsk-tool=toolcrate.cli.wrappers:run_slsk",
                "shazam-tool=toolcrate.cli.wrappers:run_shazam",
                "mdl-tool=toolcrate.cli.wrappers:run_mdl",
                "toolcrate-identify-wishlist=toolcrate.scripts.process_wishlist:main",
                "toolcrate-identify-djsets=toolcrate.scripts.process_wishlist:main",
            ],
        },
        python_requires=">=3.11,<3.13",
        cmdclass={
            'develop': PostDevelopCommand,
            'install': PostInstallCommand,
        },
    ) 