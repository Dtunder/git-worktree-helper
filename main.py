import argparse
import subprocess
import os
import sys
from typing import List, Dict

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
        print("Error: Command must be a list of strings.", file=sys.stderr)
        sys.exit(1)
        
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True)
        if result.returncode != 0 and capture_output:
            print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)
        return result
    except FileNotFoundError:
        print(f"Error: Command '{cmd[0]}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running command: {e}", file=sys.stderr)
        sys.exit(1)

def list_worktrees(args: argparse.Namespace) -> None:
    """
    Lists git worktrees in a formatted markdown table.
    
    Args:
        args: Parsed command-line arguments.
    """
    result = run_cmd(['git', 'worktree', 'list', '--porcelain'])
    if not result or not hasattr(result, 'stdout') or not result.stdout:
        print("No worktrees found or failed to list worktrees.")
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
    if not path or not isinstance(path, str):
        print("Error: Path must be a non-empty string.", file=sys.stderr)
        sys.exit(1)

    cmd = ['git', 'worktree', 'add']
    if args.branch:
        if not isinstance(args.branch, str):
            print("Error: Branch must be a string.", file=sys.stderr)
            sys.exit(1)
        cmd.extend(['-b', args.branch])
    else:
        # Automatic branch creation based on basename
        basename = os.path.basename(os.path.abspath(path))
        if not basename:
            print("Error: Could not determine basename from path.", file=sys.stderr)
            sys.exit(1)
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
    if not path or not isinstance(path, str):
        print("Error: Path must be a non-empty string.", file=sys.stderr)
        sys.exit(1)

    cmd = ['git', 'worktree', 'remove']
    if args.force:
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
    cmd = ['git', 'worktree', 'prune']
    result = run_cmd(cmd, capture_output=False)
    if result.returncode == 0:
        print("Pruned stale worktrees successfully.")
    sys.exit(result.returncode)

def main() -> None:
    """
    Main entry point for parsing arguments and dispatching commands.
    """
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
