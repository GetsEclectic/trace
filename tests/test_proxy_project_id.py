"""Cloud-sandbox egress-proxy project-id stability.

Anthropics cloud sandbox rewrites every git remote to
local_proxy@127.0.0.1:<port>/git/<owner>/<repo>, where <port> is ephemeral
(new each sandbox). Without normalization the port leaks into the project_id,
so issues created in one sandbox become unresolvable in the next and every
trc write aborts with "Cannot find project path".
"""
import tempfile
from pathlib import Path

from trace_core.projects import _extract_project_id_from_git_remote


def _git_dir_with_url(tmp: Path, url: str) -> Path:
    gd = tmp / ".git"
    gd.mkdir(parents=True)
    (gd / "config").write_text(
        "[remote \"origin\"]\n\turl = %s\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n" % url
    )
    return gd


def test_proxy_port_stripped_and_stable():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = _extract_project_id_from_git_remote(
            _git_dir_with_url(tmp / "a", "http://local_proxy@127.0.0.1:37849/git/GetsEclectic/claude-cloud-bootstrap")
        )
        b = _extract_project_id_from_git_remote(
            _git_dir_with_url(tmp / "b", "http://local_proxy@127.0.0.1:38291/git/GetsEclectic/claude-cloud-bootstrap")
        )
    assert a == "GetsEclectic/claude-cloud-bootstrap"
    assert a == b  # stable across ephemeral ports


def test_ordinary_remotes_unchanged():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        https = _extract_project_id_from_git_remote(_git_dir_with_url(tmp / "h", "https://github.com/user/repo.git"))
        ssh = _extract_project_id_from_git_remote(_git_dir_with_url(tmp / "s", "git@github.com:user/repo.git"))
    assert https == "github.com/user/repo"
    assert ssh == "github.com/user/repo"
