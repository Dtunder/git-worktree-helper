import argparse
import subprocess
import os
import sys
import logging
import json
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class JSONFormatter(logging.Formatter):
    """
    Custom logging formatter to output logs as JSON strings.

    This formatter is useful for structured logging, allowing log aggregation
    systems to easily parse and index the log entries.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats a logging record into a JSON string.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The JSON-encoded string representation of the log record.
        """
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logging() -> None:
    """
    Configures the root logger for the application.

    Sets the logging level to DEBUG and attaches a StreamHandler that writes
    to sys.stderr. The handler uses the JSONFormatter for structured logging.
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def run_cmd(
    cmd: List[str],
    capture_output: bool = True,
    retries: int = 0,
    timeout: Optional[float] = None,
    retry_delay: float = 1.0,
) -> subprocess.CompletedProcess:
    """
    Executes a shell command via the subprocess module with retry and timeout support.

    This function wraps `subprocess.run` with error handling, logging, and type
    checking. It captures standard output and standard error by default, and
    exits the program if the command fails after all retries (unless capture_output is False).

    Args:
        cmd (List[str]): A list of strings representing the command.
        capture_output (bool, optional): Whether to capture stdout and stderr.
        retries (int, optional): Number of times to retry on failure.
        timeout (Optional[float], optional): Timeout for the command in seconds.
        retry_delay (float, optional): Delay between retries in seconds.

    Returns:
        subprocess.CompletedProcess: A CompletedProcess instance.

    Raises:
        SystemExit: If `cmd` is not a list, if the command is not found,
            or if the command fails after all retries and capture_output is True.
    """
    if not isinstance(cmd, list):
        logger.error("Error: Command must be a list of strings.")
        sys.exit(1)

    attempts = 0
    while attempts <= retries:
        try:
            logger.debug(f"Running command (attempt {attempts + 1}/{retries + 1}): {' '.join(cmd)}")
            result = subprocess.run(
                cmd, capture_output=capture_output, text=True, timeout=timeout
            )
            if result.returncode != 0:
                err = result.stderr.strip() if hasattr(result, "stderr") and result.stderr else ""
                logger.warning(f"Command failed with code {result.returncode}. Stderr: {err}")
                if attempts < retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    attempts += 1
                    continue
                if capture_output:
                    logger.error(f"Command permanently failed after {retries + 1} attempts with stderr: {err}")
                    sys.exit(result.returncode)
            return result
        except FileNotFoundError:
            logger.error(f"Error: Command '{cmd[0]}' not found.")
            sys.exit(1)
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Command timed out after {timeout} seconds.")
            if attempts < retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                attempts += 1
                continue
            logger.error(f"Command permanently failed (timeout) after {retries + 1} attempts.")
            sys.exit(1)
        except Exception as e:
            logger.warning(f"Error running command: {e}")
            if attempts < retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                attempts += 1
                continue
            logger.error(f"Command permanently failed after {retries + 1} attempts due to error: {e}")
            sys.exit(1)
    
    # This shouldn't be reached, but fallback just in case
    logger.error("Unexpected execution path in run_cmd")
    sys.exit(1)


def list_worktrees(args: argparse.Namespace) -> None:
    """
    Lists git worktrees in a formatted markdown table.

    This function executes `git worktree list --porcelain` and parses
    the output to extract path, HEAD commit, and branch for each worktree.
    It then prints these details in a markdown-compatible table to stdout.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Returns:
        None
    """
    logger.info("Listing git worktrees")
    result = run_cmd(["git", "worktree", "list", "--porcelain"])
    if not result or not hasattr(result, "stdout") or not result.stdout:
        logger.info("No worktrees found or failed to list worktrees.")
        return

    worktrees: List[Dict[str, str]] = []
    current_wt: Dict[str, str] = {}

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            if current_wt:
                worktrees.append(current_wt)
                current_wt = {}
            continue

        parts = line.split(" ", 1)
        key = parts[0]
        value = parts[1] if len(parts) > 1 else ""

        if key == "worktree":
            current_wt["worktree"] = value
        elif key == "HEAD":
            current_wt["head"] = value[:7]
        elif key == "branch":
            current_wt["branch"] = (
                value.removeprefix("refs/heads/")
                if hasattr(value, "removeprefix")
                else value.replace("refs/heads/", "")
            )
        elif key == "detached":
            current_wt["branch"] = "(detached)"

    if current_wt:
        worktrees.append(current_wt)

    print("| Worktree | HEAD | Branch |")
    print("| -------- | ---- | ------ |")
    for wt in worktrees:
        path = wt.get("worktree", "")
        head = wt.get("head", "")
        branch = wt.get("branch", "")
        print(f"| {path} | {head} | {branch} |")


def add_worktree(args: argparse.Namespace) -> None:
    """
    Adds a new git worktree with automatic or specified branch creation.

    If a branch is specified via `args.branch`, it uses that branch. Otherwise,
    it automatically creates a new branch named after the basename of the
    target directory (`args.path`).

    Args:
        args (argparse.Namespace): Parsed command-line arguments containing:
            - path (str): The path where the new worktree should be created.
            - branch (str, optional): The name of the branch to use.

    Returns:
        None

    Raises:
        SystemExit: If the path is invalid, the branch is invalid,
            or if the git command fails.
    """
    path = args.path
    logger.info(f"Adding worktree at path: {path}")
    if not path or not isinstance(path, str):
        logger.error("Error: Path must be a non-empty string.")
        sys.exit(1)

    cmd = ["git", "worktree", "add"]
    if args.branch:
        if not isinstance(args.branch, str):
            logger.error("Error: Branch must be a string.")
            sys.exit(1)
        logger.debug(f"Using specified branch: {args.branch}")
        cmd.extend(["-b", args.branch])
    else:
        # Automatic branch creation based on basename
        basename = os.path.basename(os.path.abspath(path))
        if not basename:
            logger.error("Error: Could not determine basename from path.")
            sys.exit(1)
        logger.debug(f"Using automatically determined branch: {basename}")
        cmd.extend(["-b", basename])

    cmd.append(path)

    # Stream output to the user instead of capturing
    result = run_cmd(cmd, capture_output=False)
    sys.exit(result.returncode)


def remove_worktree(args: argparse.Namespace) -> None:
    """
    Removes an existing git worktree.

    Executes `git worktree remove` on the specified path. If the force flag
    is provided, it adds the `--force` option to the command.

    Args:
        args (argparse.Namespace): Parsed command-line arguments containing:
            - path (str): The path of the worktree to remove.
            - force (bool): Whether to force removal of the worktree.

    Returns:
        None

    Raises:
        SystemExit: If the path is invalid or the git command fails.
    """
    path = args.path
    logger.info(f"Removing worktree at path: {path}")
    if not path or not isinstance(path, str):
        logger.error("Error: Path must be a non-empty string.")
        sys.exit(1)

    cmd = ["git", "worktree", "remove"]
    if args.force:
        logger.debug("Force removal flag provided.")
        cmd.append("--force")
    cmd.append(path)
    result = run_cmd(cmd, capture_output=False)
    sys.exit(result.returncode)


def prune_worktrees(args: argparse.Namespace) -> None:
    """
    Prunes stale git worktrees.

    Executes `git worktree prune` to clean up any worktree definitions in
    `.git/worktrees` that no longer have corresponding directories on disk.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Returns:
        None

    Raises:
        SystemExit: If the git command fails.
    """
    logger.info("Pruning stale worktrees")
    cmd = ["git", "worktree", "prune"]
    result = run_cmd(cmd, capture_output=False)
    if result.returncode == 0:
        logger.info("Pruned stale worktrees successfully.")
    else:
        logger.error(f"Prune command exited with code {result.returncode}")
    sys.exit(result.returncode)


def main() -> None:
    """
    Main entry point for parsing arguments and dispatching commands.

    Sets up logging and defines the CLI parser using `argparse`. It creates
    subparsers for the `list`, `add`, `remove`, and `prune` commands, and
    dispatches execution to the corresponding function based on user input.

    Returns:
        None
    """
    setup_logging()
    parser = argparse.ArgumentParser(
        description="A wrapper for standard git worktree commands."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    list_parser = subparsers.add_parser(
        "list", help="List git worktrees in a pretty markdown table"
    )
    list_parser.set_defaults(func=list_worktrees)

    # Add command
    add_parser = subparsers.add_parser(
        "add", help="Add a new git worktree with automatic branch creation"
    )
    add_parser.add_argument("path", help="Path to the new worktree")
    add_parser.add_argument(
        "-b",
        "--branch",
        help="Branch to create. Defaults to basename of path.",
    )
    add_parser.set_defaults(func=add_worktree)

    # Remove command
    remove_parser = subparsers.add_parser(
        "remove", help="Remove a git worktree"
    )
    remove_parser.add_argument("path", help="Path of the worktree to remove")
    remove_parser.add_argument(
        "-f", "--force", action="store_true", help="Force removal"
    )
    remove_parser.set_defaults(func=remove_worktree)

    # Prune command
    prune_parser = subparsers.add_parser(
        "prune", help="Prune stale git worktrees"
    )
    prune_parser.set_defaults(func=prune_worktrees)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
