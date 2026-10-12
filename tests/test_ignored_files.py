from unittest import mock

import pytest


def _modify(plugin, is_ignored):
    plugin.sublime.active_window.return_value.folders.return_value = ["/repo"]
    plugin.websocket_instance = mock.MagicMock()
    plugin.ignore_checker = mock.MagicMock()
    plugin.ignore_checker.is_ignored.return_value = is_ignored
    plugin.active_view_id = None
    plugin.active_content = None
    view = mock.MagicMock()
    view.settings.return_value.get.return_value = False
    view.window.return_value.active_view.return_value = view
    view.window.return_value.folders.return_value = ["/repo"]
    view.file_name.return_value = "/repo/a.py"
    view.size.return_value = 4
    view.substr.return_value = "text"
    view.id.return_value = 1

    # Skip __init__, which starts a websocket connection thread
    listener = object.__new__(plugin.NinetyFiveListener)
    listener.on_modified(view)
    return plugin.websocket_instance.send_message


def test_ignored_file_is_not_sent(plugin):
    send = _modify(plugin, True)
    send.assert_not_called()
    plugin.ignore_checker.is_ignored.assert_called_once_with("/repo", "/repo/a.py")


@pytest.mark.parametrize("answer", [False, None])
def test_file_is_sent_when_not_ignored_or_when_git_cannot_say(plugin, answer):
    send = _modify(plugin, answer)
    assert send.called


def test_saving_a_gitignore_makes_git_reread_the_rules(plugin):
    plugin.ignore_checker = mock.MagicMock()
    listener = object.__new__(plugin.NinetyFiveListener)
    view = mock.MagicMock()

    view.file_name.return_value = "/repo/src/.gitignore"
    listener.on_post_save(view)
    plugin.ignore_checker.invalidate.assert_called_once_with()

    plugin.ignore_checker.reset_mock()
    view.file_name.return_value = "/repo/a.py"
    listener.on_post_save(view)
    plugin.ignore_checker.invalidate.assert_not_called()

    view.file_name.return_value = None
    listener.on_post_save(view)
    plugin.ignore_checker.invalidate.assert_not_called()
