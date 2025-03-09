#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script to update dependencies for the flatpak build."""
import os
import platform
import subprocess
import sys
from enum import Enum

VENV_PATH = "/tmp/venv1"
BUILDER_REPO_URL = "https://github.com/aleb/flatpak-builder-tools.git"
REPO_CLONE_DIR = "flatpak-builder-tools"
BUILD_DIR = "build/flatpak"
SDK = "47"


class Arch(Enum):
    """Enumeration of supported architectures."""

    AARCH64 = "aarch64"
    X86_64 = "x86_64"

    def __str__(self):
        return self.value


def run_command(command, check=True, cwd=None):
    """Utility function to run a shell command and check for errors."""
    print(f"Running command: {command}")
    result = subprocess.run(command, shell=True, check=check, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed: {command}")
        sys.exit(1)


def setup_virtualenv():
    """Set up the Python virtual environment."""
    if not os.path.exists(VENV_PATH):
        print("Creating virtual environment...")
        run_command(f"python3 -m venv {VENV_PATH}")
    else:
        print("Using existing virtual environment")

    # Install required Python packages
    print("Installing required packages in virtual environment...")
    run_command(f"{VENV_PATH}/bin/pip3 install requirements-parser setuptools")


def clone_flatpak_builder_tools():
    """Clone the flatpak-builder-tools repository."""
    if not os.path.exists(REPO_CLONE_DIR):
        print("Cloning flatpak-builder-tools repository...")
        run_command(f"git clone {BUILDER_REPO_URL}")
    else:
        print("Using existing flatpak-builder-tools repository")

    return os.path.join(REPO_CLONE_DIR, "pip", "flatpak-pip-generator")


def update_runtime_dependencies(venv_python, flatpak_pip_generator, arch):
    """Update runtime dependencies."""
    print("Updating runtime dependencies...")
    run_command(f"{venv_python} ../{flatpak_pip_generator} --runtime org.gnome.Sdk/{arch}/{SDK} librosa", cwd=f"{os.getcwd()}/{arch}")
    run_command(f"{venv_python} ../{flatpak_pip_generator} --runtime org.gnome.Sdk/{arch}/{SDK} matplotlib", cwd=f"{os.getcwd()}/{arch}")


def update_development_tools(venv_python, flatpak_pip_generator, arch):
    """Update development tools."""
    print("Updating development tools...")
    run_command(f"{venv_python} ../{flatpak_pip_generator} --runtime org.gnome.Sdk/{arch}/{SDK} wheezy.template nose setuptools_git setuptools_pep8 sphinx hotdoc", cwd=f"{os.getcwd()}/{arch}")
    run_command(f"{venv_python} ../{flatpak_pip_generator} --runtime org.gnome.Sdk/{arch}/{SDK} ipdb", cwd=f"{os.getcwd()}/{arch}")


def update_pre_commit_framework(venv_python, flatpak_pip_generator, arch):
    """Update the pre-commit framework."""
    print("Updating pre-commit framework...")
    run_command(f"{venv_python} ../{flatpak_pip_generator} --runtime org.gnome.Sdk/{arch}/{SDK} pre-commit", cwd=f"{os.getcwd()}/{arch}")
    run_command(f"{venv_python} ../{flatpak_pip_generator} --runtime org.gnome.Sdk/{arch}/{SDK} setuptools-scm 'pylint<=2.13.5'", cwd=f"{os.getcwd()}/{arch}")


def get_system_arch():
    """Get the system architecture."""
    arch = platform.machine()
    if arch == "aarch64":
        return Arch.AARCH64
    if arch == "x86_64":
        return Arch.X86_64

    print(f"Unsupported architecture: {arch}")
    sys.exit(1)


def main():
    """Main function to automate the setup process."""
    # Don't run this script from the wrong directory
    if os.getcwd()[-len(BUILD_DIR):] != BUILD_DIR:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    arch = get_system_arch()
    setup_virtualenv()
    flatpak_pip_generator = clone_flatpak_builder_tools()

    # Set the path to the Python executable inside the virtual environment
    venv_python = VENV_PATH + "/bin/python3"

    update_runtime_dependencies(venv_python, flatpak_pip_generator, arch)
    update_development_tools(venv_python, flatpak_pip_generator, arch)
    update_pre_commit_framework(venv_python, flatpak_pip_generator, arch)

    print(f"WARNING: Dependencies updated ONLY for the current host architecture - {arch}")
    print("NOTE: You'll need to run this script on different hosts to update dependencies for their respective architectures")
    print("Run `ptvenv --update` inside the dev-env to try out the build")


if __name__ == "__main__":
    main()
