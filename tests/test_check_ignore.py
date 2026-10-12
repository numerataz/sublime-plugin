import os
import shutil
import subprocess
from unittest import mock

import pytest

from ninetyfive.check_ignore import IgnoreChecker

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


@pytest.fixture
def repo(tmp_path):
    root = str(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    write(os.path.join(root, ".gitignore"), "*.log\nbuild/\n")
    write(os.path.join(root, "sub", ".gitignore"), "*.tmp\n!keep.log\n")
    return root


@pytest.fixture
def checker():
    c = IgnoreChecker()
    yield c
    c.close()


def test_plain_file_is_not_ignored(repo, checker):
    assert checker.is_ignored(repo, os.path.join(repo, "a.py")) is False


def test_ignored_by_root_gitignore(repo, checker):
    assert checker.is_ignored(repo, os.path.join(repo, "x.log")) is True
    assert checker.is_ignored(repo, os.path.join(repo, "build", "z.c")) is True


def test_nested_gitignore_and_exception_rule(repo, checker):
    assert checker.is_ignored(repo, os.path.join(repo, "sub", "y.tmp")) is True
    # "!keep.log" re-includes the file, so it is not ignored
    assert checker.is_ignored(repo, os.path.join(repo, "sub", "keep.log")) is False


def test_one_git_process_is_reused(repo):
    popen = mock.Mock(wraps=subprocess.Popen)
    checker = IgnoreChecker(popen=popen)
    try:
        for name in ("a.py", "x.log", "b.py", "y.log"):
            checker.is_ignored(repo, os.path.join(repo, name))
        assert popen.call_count == 1
    finally:
        checker.close()


def test_invalidate_rereads_the_rules(repo, checker):
    target = os.path.join(repo, "a.py")
    assert checker.is_ignored(repo, target) is False
    write(os.path.join(repo, ".gitignore"), "*.py\n")
    # Git read its rules when it started, so the old answer is still given ...
    assert checker.is_ignored(repo, target) is False
    # ... until the process is restarted
    checker.invalidate()
    assert checker.is_ignored(repo, target) is True


def test_process_is_restarted_after_max_age(repo):
    popen = mock.Mock(wraps=subprocess.Popen)
    checker = IgnoreChecker(max_age=0.0, popen=popen)
    try:
        checker.is_ignored(repo, os.path.join(repo, "a.py"))
        checker.is_ignored(repo, os.path.join(repo, "a.py"))
        assert popen.call_count == 2
    finally:
        checker.close()


def test_path_outside_the_folder_gives_no_answer(repo, tmp_path_factory, checker):
    other = str(tmp_path_factory.mktemp("other"))
    assert checker.is_ignored(repo, os.path.join(other, "a.py")) is None


def test_missing_path_gives_no_answer(repo, checker):
    assert checker.is_ignored(repo, None) is None
    assert checker.is_ignored(None, "a.py") is None


def test_not_a_repository_gives_no_answer_and_does_not_respawn(tmp_path):
    popen = mock.Mock(wraps=subprocess.Popen)
    checker = IgnoreChecker(popen=popen)
    try:
        for _ in range(5):
            assert checker.is_ignored(str(tmp_path), os.path.join(str(tmp_path), "a.py")) is None
        assert popen.call_count == 1
    finally:
        checker.close()


def test_git_not_installed_gives_no_answer(repo):
    popen = mock.Mock(side_effect=FileNotFoundError)
    checker = IgnoreChecker(popen=popen)
    assert checker.is_ignored(repo, os.path.join(repo, "a.py")) is None
