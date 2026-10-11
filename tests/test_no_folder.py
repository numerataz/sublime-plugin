from unittest import mock


def test_on_modified_without_folder(plugin):
    plugin.sublime.active_window.return_value.folders.return_value = []
    plugin.websocket_instance = mock.MagicMock()
    view = mock.MagicMock()
    view.settings.return_value.get.return_value = False
    view.window.return_value.active_view.return_value = view

    # Skip __init__, which starts a websocket connection thread
    listener = object.__new__(plugin.NinetyFiveListener)
    listener.on_modified(view)

    plugin.websocket_instance.send_message.assert_not_called()
