# Copyright (c) 2026 Tobias Erbsland - https://erbsland.dev
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from lib.error import UtilityError
from lib.path_safety import require_safe_existing_file
from lib.safe_tool import safe_subprocess_environment
from lib.utility import UtilityApp


class RebuildDocApp(UtilityApp):
    """Safely rebuild the Sphinx documentation."""

    description = "Remove generated documentation output and rebuild the Sphinx documentation."

    def __init__(self) -> None:
        super().__init__()
        self.project_root = Path()

    def handle_command_line_args(self, args) -> None:
        self.project_root = self.project_directory

    def generated_directory(self, name: str) -> Path:
        """Get a generated documentation directory below the project root."""
        if name not in {"_doxygen_input", "_build"}:
            raise UtilityError(f"Unexpected generated documentation directory: {name}")
        project_root = self.project_root.resolve()
        path = (project_root / name).resolve(strict=False)
        if path.parent != project_root:
            raise UtilityError(f"Generated documentation directory is not below the project root: {path}")
        return path

    def remove_generated_directory(self, name: str) -> None:
        """Remove one generated documentation directory if it exists."""
        path = self.generated_directory(name)
        if path.is_symlink():
            raise UtilityError(f"Refusing to remove symbolic link: {path}")
        if not path.exists():
            self.print_verbose(f"Skipping missing {name}")
            return
        if not path.is_dir():
            raise UtilityError(f"Refusing to remove non-directory path: {path}")
        if self.verbose:
            print(f"Removing {name}", flush=True)
        shutil.rmtree(path)

    def sphinx_build_executable(self) -> Path:
        """Get the sphinx-build executable from the project virtual environment."""
        executable = self.project_root / ".venv" / "bin" / "sphinx-build"
        require_safe_existing_file(executable, "sphinx-build executable", 1024 * 1024)
        if not executable.exists():
            raise UtilityError(f"Could not find sphinx-build in the project virtual environment: {executable}")
        if not os.access(executable, os.X_OK):
            raise UtilityError(f"sphinx-build is not executable: {executable}")
        return executable

    def sphinx_environment(self) -> dict[str, str]:
        """Create an environment equivalent to activating the project virtual environment."""
        venv_dir = self.project_root / ".venv"
        venv_bin_dir = venv_dir / "bin"
        environment = safe_subprocess_environment()
        path = environment.get("PATH", "")
        environment["PATH"] = f"{venv_bin_dir}{os.pathsep}{path}" if path else str(venv_bin_dir)
        environment["VIRTUAL_ENV"] = str(venv_dir)
        return environment

    def rebuild_documentation(self) -> None:
        """Run sphinx-build to rebuild the documentation."""
        executable = self.sphinx_build_executable()
        command = [str(executable), "doc", "_build"]
        if self.verbose:
            print("Running sphinx-build doc _build", flush=True)
        try:
            subprocess.run(command, check=True, cwd=self.project_root, env=self.sphinx_environment())
        except subprocess.CalledProcessError as error:
            raise UtilityError("sphinx-build failed.") from error

    def run(self, argv=None) -> None:
        """Remove generated output and rebuild the documentation."""
        super().run(argv)
        self.remove_generated_directory("_doxygen_input")
        self.remove_generated_directory("_build")
        self.rebuild_documentation()
        print("Documentation rebuild completed.")


def main() -> None:
    """Main entry point for rebuilding documentation."""
    raise SystemExit(RebuildDocApp().main())


if __name__ == "__main__":
    main()
