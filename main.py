import argparse
import subprocess
import os
import sys
import logging
import json
from typing import List, Dict

logger = logging.getLogger(__name__)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logging():
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

def run_cmd(cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """
    Executes a shell command via subprocess.
    
    Args:
        cmd: A list of strings representing the command and its arguments.
        capture_output: Whether to capture standard output and standard error.
        
    Returns:
        A CompletedProcess instance containing the command results.
    """
    if not isinstance(cmd, list):
        logger.error("Error: Command must be a list of strings.")
        sys.exit(1)
        
    try:
        logger.debug(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=capture_output, text=True)
        if result.returncode != 0 and capture_output:
            logger.error(f"Command failed with stderr: {result.stderr.strip() if result.stderr else ''}")
            sys.exit(result.returncode)
        return result
    except FileNotFoundError:
        logger.error(f"Error: Command '{cmd[0]}' not found.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running command: {e}")
        sys.exit(1)

def list_worktrees(args: argparse.Namespace) -> None:
    """
    Lists git worktrees in a formatted markdown table.
    
    Args:
        args: Parsed command-line arguments.
    """
    logger.info("Listing git worktrees")
    result = run_cmd(['git', 'worktree', 'list', '--porcelain'])
    if not result or not hasattr(result, 'stdout') or not result.stdout:
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
        
        parts = line.split(' ', 1)
        key = parts[0]
        value = parts[1] if len(parts) > 1 else ''
        
        if key == 'worktree':
            current_wt['worktree'] = value
        elif key == 'HEAD':
            current_wt['head'] = value[:7]
        elif key == 'branch':
            current_wt['branch'] = value.removeprefix('refs/heads/') if hasattr(value, 'removeprefix') else value.replace('refs/heads/', '')
        elif key == 'detached':
            current_wt['branch'] = '(detached)'
    
    if current_wt:
        worktrees.append(current_wt)
        
    print("| Worktree | HEAD | Branch |")
    print("| -------- | ---- | ------ |")
    for wt in worktrees:
        path = wt.get('worktree', '')
        head = wt.get('head', '')
        branch = wt.get('branch', '')
        print(f"| {path} | {head} | {branch} |")

def add_worktree(args: argparse.Namespace) -> None:
    """
    Adds a new git worktree with automatic or specified branch creation.
    
    Args:
        args: Parsed command-line arguments.
    """
    path = args.path
    logger.info(f"Adding worktree at path: {path}")
    if not path or not isinstance(path, str):
        logger.error("Error: Path must be a non-empty string.")
        sys.exit(1)

    cmd = ['git', 'worktree', 'add']
    if args.branch:
        if not isinstance(args.branch, str):
            logger.error("Error: Branch must be a string.")
            sys.exit(1)
        logger.debug(f"Using specified branch: {args.branch}")
        cmd.extend(['-b', args.branch])
    else:
        # Automatic branch creation based on basename
        basename = os.path.basename(os.path.abspath(path))
        if not basename:
            logger.error("Error: Could not determine basename from path.")
            sys.exit(1)
        logger.debug(f"Using automatically determined branch: {basename}")
        cmd.extend(['-b', basename])
    
    cmd.append(path)
    
    # Stream output to the user instead of capturing
    result = run_cmd(cmd, capture_output=False)
    sys.exit(result.returncode)

def remove_worktree(args: argparse.Namespace) -> None:
    """
    Removes an existing git worktree.
    
    Args:
        args: Parsed command-line arguments.
    """
    path = args.path
    logger.info(f"Removing worktree at path: {path}")
    if not path or not isinstance(path, str):
        logger.error("Error: Path must be a non-empty string.")
        sys.exit(1)

    cmd = ['git', 'worktree', 'remove']
    if args.force:
        logger.debug("Force removal flag provided.")
        cmd.append('--force')
    cmd.append(path)
    result = run_cmd(cmd, capture_output=False)
    sys.exit(result.returncode)

def prune_worktrees(args: argparse.Namespace) -> None:
    """
    Prunes stale git worktrees.
    
    Args:
        args: Parsed command-line arguments.
    """
    logger.info("Pruning stale worktrees")
    cmd = ['git', 'worktree', 'prune']
    result = run_cmd(cmd, capture_output=False)
    if result.returncode == 0:
        logger.info("Pruned stale worktrees successfully.")
    else:
        logger.error(f"Prune command exited with code {result.returncode}")
    sys.exit(result.returncode)

def main() -> None:
    """
    Main entry point for parsing arguments and dispatching commands.
    """
    setup_logging()
    parser = argparse.ArgumentParser(description="A wrapper for standard git worktree commands.")
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # List command
    list_parser = subparsers.add_parser('list', help="List git worktrees in a pretty markdown table")
    list_parser.set_defaults(func=list_worktrees)
    
    # Add command
    add_parser = subparsers.add_parser('add', help="Add a new git worktree with automatic branch creation")
    add_parser.add_argument('path', help="Path to the new worktree")
    add_parser.add_argument('-b', '--branch', help="Branch to create/checkout. Defaults to the basename of the path.")
    add_parser.set_defaults(func=add_worktree)
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help="Remove a git worktree")
    remove_parser.add_argument('path', help="Path of the worktree to remove")
    remove_parser.add_argument('-f', '--force', action='store_true', help="Force removal")
    remove_parser.set_defaults(func=remove_worktree)
    
    # Prune command
    prune_parser = subparsers.add_parser('prune', help="Prune stale git worktrees")
    prune_parser.set_defaults(func=prune_worktrees)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
