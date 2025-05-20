# SPDX-FileCopyrightText: openSTB contributors
# SPDX-License-Identifier: BSD-2-Clause-Patent

import importlib.machinery
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

import pytest


@pytest.fixture(scope="session")
def unique_src_dir():
    """Unique directory for the source to avoid pip's filename-based caching."""
    with TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="session")
def test_project_venv(tmp_path_factory, unique_src_dir):
    """Virtual environment with the sample project installed."""
    # Create a virtual environment.
    venv_dir = tmp_path_factory.mktemp("venv.i18n_sample_project")
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", "."], cwd=venv_dir
    )
    venv_python = str(venv_dir / "bin" / "python")

    # Copy the openstb-i18n source to a unique directory.
    base = Path(__file__).parent.parent.resolve()
    plugin_dir = unique_src_dir / "i18n"
    shutil.copytree(base / "src", plugin_dir / "src")
    shutil.copytree(base / ".git", plugin_dir / ".git")
    shutil.copy(base / "pyproject.toml", plugin_dir)

    # Copy the test project to a unique directory.
    project_dir = unique_src_dir / "i18n_test_project"
    shutil.copytree(base / "tests" / "test_project", project_dir)

    # Add the build system information to the sample pyproject.toml.
    pyprojfn = project_dir / "pyproject.toml"
    with pyprojfn.open("a") as pyproj:
        pyproj.write(
            f"""
[project]
name = "openstb-i18n-test"
version = "1.0.0"
dependencies = ["openstb-i18n @ {plugin_dir.as_uri()}"]

[build-system]
requires = ["hatchling", "openstb-i18n @ {plugin_dir.as_uri()}"]
build-backend = "hatchling.build"

[tool.hatch.metadata]
allow-direct-references = true
        """
        )

    # And install the sample project into the environment.
    subprocess.run([venv_python, "-m", "pip", "install", "."], cwd=project_dir)

    # Find the site-packages directory.
    res = subprocess.run(
        [venv_python, "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        capture_output=True,
        text=True,
        check=True,
    )
    sitepkgs = Path(res.stdout.strip())

    yield venv_python, sitepkgs


class VenvPathFinder(importlib.machinery.PathFinder):
    def __init__(self, venv_path):
        self.venv_path = venv_path

    def find_spec(self, fullname, path=None, target=None):
        return importlib.machinery.PathFinder.find_spec(
            fullname, path=[self.venv_path], target=target
        )


@pytest.fixture(scope="function")
def inside_venv(test_project_venv):
    """Run this functions tests using the virtual environment packages."""
    venv_python, venv_sitepkgs = test_project_venv

    # Create a finder to locate modules inside the virtual environment.
    finder = VenvPathFinder(str(venv_sitepkgs))
    sys.meta_path.insert(0, finder)

    # Remove any existing imports of openstb modules.
    for name in list(sys.modules.keys()):
        if "openstb" in name:
            del sys.modules[name]

    yield

    # Remove any openstb modules we imported.
    for name in list(sys.modules.keys()):
        if "openstb" in name:
            del sys.modules[name]

    # And remove the finder.
    sys.meta_path.remove(finder)
