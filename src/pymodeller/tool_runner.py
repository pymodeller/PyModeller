"""Tool runner."""

import shutil
import subprocess  # noqa: S404
import sys
from collections.abc import Sequence
from logging import getLogger

logger = getLogger(__name__)


class ToolRunner:
    """Helper class to manage external tool execution with fallbacks."""

    @staticmethod
    def execute(cmd: Sequence[str]) -> None:
        """Execute a system command and exit on failure."""
        logger.info(f"Executing: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=False)  # noqa: S603
            if result.returncode != 0:
                logger.error(f"Command failed with exit code {result.returncode}: {' '.join(cmd)}")
                sys.exit(result.returncode)
        except FileNotFoundError:
            logger.error(f"Executable not found: {cmd[0]}")
            sys.exit(1)

    @classmethod
    def run_with_uv(cls, tool: str, args: list[str]) -> None:
        """Attempt to run a tool via 'uv run', falling back to direct execution."""
        if shutil.which("uv"):
            try:
                logger.debug(f"Attempting to run {tool} via uv...")
                cls.execute(["uv", "run", tool, *args])
                return
            except Exception as e:
                logger.warning(f"uv execution failed for {tool}: {e}. Trying direct execution...")

        if shutil.which(tool):
            cls.execute([tool, *args])
        else:
            logger.error(f"Tool '{tool}' is not installed or not in PATH.")
            sys.exit(1)
