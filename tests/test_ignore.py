import subprocess
from unittest import mock

import pytest


def make_view(file_name="/repo/main.py"):
    view = mock.MagicMock()
    view.settings().get.return_value = False
    view.window().active_view.return_value = view
    view.window().folders.return_value = ["/repo"]
    view.file_name.return_value = file_name
    view.substr.return_value = "text"
    view.sel.return_value = [mock.MagicMock(**{"begin.return_value": 4})]
    return view


def run_on_modified(plugin, view, check_output):
    plugin.sublime.active_window().folders.return_value = ["/repo"]
    plugin.websocket_instance = mock.MagicMock()
    # Skip __init__, which starts a websocket connection thread
    listener = object.__new__(plugin.NinetyFiveListener)
    with mock.patch.object(plugin.subprocess, "check_output", check_output):
        listener.on_modified(view)
    return plugin.websocket_instance.send_message


def error(code):
    return subprocess.CalledProcessError(code, ["git", "check-ignore"])


@pytest.mark.parametrize(
    "file_name, check_output",
    [
        (None, mock.MagicMock(return_value="")),
        ("/repo/main.py", mock.MagicMock(side_effect=error(128))),
        ("/repo/main.py", mock.MagicMock(side_effect=FileNotFoundError("git"))),
        ("/repo/main.py", mock.MagicMock(return_value="/repo/main.py\n")),
    ],
    ids=["no-file-name", "exit-128", "git-missing", "ignored"],
)
def test_not_sent(plugin, file_name, check_output):
    send = run_on_modified(plugin, make_view(file_name), check_output)
    send.assert_not_called()


def test_sent_when_not_ignored(plugin):
    send = run_on_modified(plugin, make_view(), mock.MagicMock(side_effect=error(1)))
    assert '"type": "file-content"' in send.call_args_list[0].args[0]
