import argparse
import subprocess
import os
import sys

def run_cmd(cmd, capture_output=True):
    result = subprocess.run(cmd, capture_output=capture_output, text=True)
    if result.returncode != 0 and capture_output:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return result

def list_worktrees(args):
    result = run_cmd(['git', 'worktree', 'list', '--porcelain'])
    lines = result.stdout.splitlines()
    
    worktrees = []
    current_wt = {}
    for line in lines:
        if not line.strip():
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
            current_wt['branch'] = value.replace('refs/heads/', '')
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

def add_worktree(args):
    path = args.path
    cmd = ['git', 'worktree', 'add']
    if args.branch:
        cmd.extend(['-b', args.branch])
    else:
        # Automatic branch creation based on basename
        basename = os.path.basename(os.path.abspath(path))
        cmd.extend(['-b', basename])
    
    cmd.append(path)
    
    # We might want to stream output to the user instead of capturing
    result = subprocess.run(cmd, text=True)
    sys.exit(result.returncode)

def remove_worktree(args):
    cmd = ['git', 'worktree', 'remove']
    if args.force:
        cmd.append('--force')
    cmd.append(args.path)
    result = subprocess.run(cmd, text=True)
    sys.exit(result.returncode)

def prune_worktrees(args):
    cmd = ['git', 'worktree', 'prune']
    result = subprocess.run(cmd, text=True)
    if result.returncode == 0:
        print("Pruned stale worktrees successfully.")
    sys.exit(result.returncode)

def main():
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
