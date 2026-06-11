# git-worktree-helper

A Python CLI helper to manage, list, and clean up active git worktrees. This utility wraps standard git worktree commands, offering enhanced features like markdown table formatting and automatic branch creation.

## Features

- **List Worktrees**: Outputs a clean, pretty markdown table showing the path, HEAD commit, and branch of your worktrees.
- **Add Worktree**: Wraps `git worktree add`. Automatically creates a new branch based on the basename of the target directory if no branch is explicitly specified.
- **Remove Worktree**: Removes an existing worktree via `git worktree remove`.
- **Prune Worktrees**: Cleans up stale worktree definitions using `git worktree prune`.

## Usage

You can run the script via Python:

```bash
python main.py <command> [options]
```

### Commands

#### `list`
Lists all git worktrees in a markdown table format.
```bash
python main.py list
```

#### `add`
Adds a new git worktree. By default, it will create a new branch named after the directory you specify.
```bash
python main.py add /path/to/my-feature
# Creates a worktree at /path/to/my-feature on a new branch named 'my-feature'
```
To specify a specific branch, use the `-b` option:
```bash
python main.py add /path/to/worktree -b specific-branch
```

#### `remove`
Removes a specified worktree.
```bash
python main.py remove /path/to/worktree
```
Use `-f` or `--force` to force removal:
```bash
python main.py remove /path/to/worktree --force
```

#### `prune`
Prunes stale git worktrees.
```bash
python main.py prune
```
