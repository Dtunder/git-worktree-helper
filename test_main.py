import pytest
import sys
import os
import argparse
from unittest.mock import patch, MagicMock

import main

# Helper to create a mock args object
class MockArgs:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

@patch('subprocess.run')
def test_run_cmd_success(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    result = main.run_cmd(['git', 'status'])
    mock_run.assert_called_once_with(['git', 'status'], capture_output=True, text=True)
    assert result == mock_result

@patch('sys.stderr')
@patch('sys.exit')
@patch('subprocess.run')
def test_run_cmd_failure(mock_run, mock_exit, mock_stderr):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "error message"
    mock_run.return_value = mock_result

    main.run_cmd(['git', 'status'])
    mock_run.assert_called_once_with(['git', 'status'], capture_output=True, text=True)
    mock_exit.assert_called_once_with(1)

@patch('subprocess.run')
def test_list_worktrees(mock_run, capsys):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = """worktree /path/to/repo
HEAD 1234567890
branch refs/heads/main

worktree /path/to/feature
HEAD abcdef1234
branch refs/heads/feature-branch

worktree /path/to/detached
HEAD 9876543210
detached
"""
    mock_run.return_value = mock_result

    args = MockArgs()
    main.list_worktrees(args)

    mock_run.assert_called_once_with(['git', 'worktree', 'list', '--porcelain'], capture_output=True, text=True)
    
    captured = capsys.readouterr()
    output = captured.out
    
    assert "| Worktree | HEAD | Branch |" in output
    assert "| /path/to/repo | 1234567 | main |" in output
    assert "| /path/to/feature | abcdef1 | feature-branch |" in output
    assert "| /path/to/detached | 9876543 | (detached) |" in output

@patch('sys.exit')
@patch('subprocess.run')
def test_add_worktree_with_branch(mock_run, mock_exit):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    args = MockArgs(path='/path/to/new-wt', branch='my-branch')
    main.add_worktree(args)

    mock_run.assert_called_once_with(['git', 'worktree', 'add', '-b', 'my-branch', '/path/to/new-wt'], capture_output=False, text=True)
    mock_exit.assert_called_once_with(0)

@patch('sys.exit')
@patch('subprocess.run')
def test_add_worktree_no_branch(mock_run, mock_exit):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    args = MockArgs(path='/path/to/new-wt', branch=None)
    main.add_worktree(args)

    mock_run.assert_called_once_with(['git', 'worktree', 'add', '-b', 'new-wt', '/path/to/new-wt'], capture_output=False, text=True)
    mock_exit.assert_called_once_with(0)

@patch('sys.exit')
@patch('subprocess.run')
def test_remove_worktree(mock_run, mock_exit):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    args = MockArgs(path='/path/to/wt', force=False)
    main.remove_worktree(args)

    mock_run.assert_called_once_with(['git', 'worktree', 'remove', '/path/to/wt'], capture_output=False, text=True)
    mock_exit.assert_called_once_with(0)

@patch('sys.exit')
@patch('subprocess.run')
def test_remove_worktree_force(mock_run, mock_exit):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    args = MockArgs(path='/path/to/wt', force=True)
    main.remove_worktree(args)

    mock_run.assert_called_once_with(['git', 'worktree', 'remove', '--force', '/path/to/wt'], capture_output=False, text=True)
    mock_exit.assert_called_once_with(0)

@patch('sys.exit')
@patch('subprocess.run')
def test_prune_worktrees(mock_run, mock_exit, capsys):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    args = MockArgs()
    main.prune_worktrees(args)

    mock_run.assert_called_once_with(['git', 'worktree', 'prune'], capture_output=False, text=True)
    mock_exit.assert_called_once_with(0)
    
    captured = capsys.readouterr()
    assert "Pruned stale worktrees successfully." in captured.out

@patch('sys.stderr')
def test_run_cmd_type_error(mock_stderr):
    with pytest.raises(SystemExit) as e:
        main.run_cmd("not a list")
    assert e.value.code == 1

@patch('subprocess.run')
@patch('sys.stderr')
def test_run_cmd_file_not_found(mock_stderr, mock_run):
    mock_run.side_effect = FileNotFoundError()
    with pytest.raises(SystemExit) as e:
        main.run_cmd(["non_existent_command"])
    assert e.value.code == 1

@patch('subprocess.run')
@patch('sys.stderr')
def test_run_cmd_general_exception(mock_stderr, mock_run):
    mock_run.side_effect = Exception("General error")
    with pytest.raises(SystemExit) as e:
        main.run_cmd(["git", "status"])
    assert e.value.code == 1

@patch('subprocess.run')
def test_list_worktrees_empty(mock_run, capsys):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_run.return_value = mock_result

    args = MockArgs()
    main.list_worktrees(args)
    captured = capsys.readouterr()
    assert "No worktrees found" in captured.out

@patch('sys.stderr')
def test_add_worktree_invalid_path(mock_stderr):
    args = MockArgs(path=None, branch="branch")
    with pytest.raises(SystemExit) as e:
        main.add_worktree(args)
    assert e.value.code == 1

@patch('sys.stderr')
def test_add_worktree_invalid_branch(mock_stderr):
    args = MockArgs(path="path", branch=123)
    with pytest.raises(SystemExit) as e:
        main.add_worktree(args)
    assert e.value.code == 1

@patch('sys.stderr')
def test_remove_worktree_invalid_path(mock_stderr):
    args = MockArgs(path=None, force=False)
    with pytest.raises(SystemExit) as e:
        main.remove_worktree(args)
    assert e.value.code == 1

@patch('main.list_worktrees')
@patch('argparse.ArgumentParser.parse_args')
def test_main_list(mock_parse_args, mock_list_worktrees):
    mock_args = MagicMock()
    mock_args.command = 'list'
    mock_args.func = mock_list_worktrees
    mock_parse_args.return_value = mock_args

    main.main()
    mock_list_worktrees.assert_called_once_with(mock_args)
