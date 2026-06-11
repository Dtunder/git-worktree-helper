# git-worktree-helper

A Python CLI helper to manage, list, and clean up active git worktrees. This utility wraps standard git worktree commands, offering enhanced features like markdown table formatting and automatic branch creation.

## Features

- **List Worktrees**: Outputs a clean, pretty markdown table showing the path, HEAD commit, and branch of your worktrees.
- **Add Worktree**: Wraps `git worktree add`. Automatically creates a new branch based on the basename of the target directory if no branch is explicitly specified.
- **Remove Worktree**: Removes an existing worktree via `git worktree remove`.
- **Prune Worktrees**: Cleans up stale worktree definitions using `git worktree prune`.

## Config Setup Documentation

Before running or testing the script, you'll need an environment with Python 3.7+ installed.

1. Clone the repository and navigate into the project directory.
2. Ensure you have standard Git installed and accessible in your system's PATH.

### Testing Setup
If you plan to run the test suite, you need to install the required testing dependencies. We use `pytest` and `pytest-cov`.

```bash
# Install pytest and pytest-cov
pip install pytest pytest-cov

# Run tests and evaluate coverage
python -m pytest --cov=main
```

## CLI Instructions

You can run the script using the primary entry point `main.py`:

```bash
python main.py <command> [options]
```

### Commands

#### `list`
Lists all git worktrees for the current repository in a markdown table format.
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
Use `-f` or `--force` to force removal (useful if the worktree has uncommitted changes):
```bash
python main.py remove /path/to/worktree --force
```

#### `prune`
Prunes stale git worktrees. Stale worktrees are ones that are recorded in the repository but whose directories have been deleted or moved manually.
```bash
python main.py prune
```

## API Reference Documentation

The script also contains several utility functions in `main.py` that can be imported and used in other Python modules if needed.

### `setup_logging()`
Configures the root logger. Sets the logging level to `DEBUG` and uses a custom `JSONFormatter` to output logs as structured JSON to standard error.

### `run_cmd(cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess`
Executes a shell command via `subprocess.run()`. It handles logging, input validation, and gracefully exits the script with the subprocess's return code if the command fails (unless `capture_output` is set to `False`).

### `list_worktrees(args: argparse.Namespace) -> None`
Executes `git worktree list --porcelain`, parses the output, and prints a formatted markdown table to `stdout`.

### `add_worktree(args: argparse.Namespace) -> None`
Executes `git worktree add`. Automatically deduces a branch name using the basename of the target path if no branch name is provided via the arguments.

### `remove_worktree(args: argparse.Namespace) -> None`
Executes `git worktree remove` against the provided target path. Includes the `--force` flag if specified in the arguments.

### `prune_worktrees(args: argparse.Namespace) -> None`
Executes `git worktree prune` to clean up stale worktree definitions.
