"""Regression tests for worktree-aware detect_project().

Drop into the upstream `dschartman/trace` test suite (e.g. tests/test_projects.py
or a standalone module). Covers the data-loss bug where a `trc` write from
inside a git worktree truncated the parent checkout's .trace/issues.jsonl.
"""
import subprocess
from pathlib import Path

import pytest

from trace_core.projects import detect_project, _resolve_git_dir


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )


def test_resolve_git_dir_handles_pointer_file(tmp_path):
    # A worktree's .git is a file: "gitdir: <path>". Build that shape by hand.
    canonical = tmp_path / ".git"
    canonical.mkdir()
    wt_gitdir = canonical / "worktrees" / "wt"
    wt_gitdir.mkdir(parents=True)
    (wt_gitdir / "commondir").write_text("../..\n")
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {wt_gitdir}\n")

    cgd, root = _resolve_git_dir(wt / ".git")
    assert cgd == canonical
    assert root == tmp_path


def test_detect_project_identity_matches_across_worktree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@t.co")
    _git(repo, "config", "user.name", "t")
    _git(repo, "remote", "add", "origin", "https://github.com/example/repo.git")
    (repo / "f.txt").write_text("x")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-m", "init")
    _git(repo, "worktree", "add", "wt")

    main = detect_project(str(repo))
    wt = detect_project(str(repo / "wt"))

    assert main is not None and wt is not None
    # The worktree must resolve to the SAME project identity + root as the main
    # checkout — otherwise export_to_jsonl writes a per-worktree subset and
    # truncates the parent's issues.jsonl.
    assert wt == main
    assert wt["path"] == str(repo)
    assert wt["id"] == "github.com/example/repo"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
