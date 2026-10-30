import json


def _send(handler, frame):
    handler._on_message(None, json.dumps(frame))


def _view(plugin):
    view = plugin.sublime.active_window.return_value.active_view.return_value
    view.run_command.reset_mock()
    return view


def test_reply_without_v_does_not_raise(plugin):
    plugin.active_request_id = "req-1"
    handler = plugin.WebSocketHandler("ws://test")
    handler._on_message(None, json.dumps({"r": "req-1"}))
    # A frame without "v" or "end" is not end-of-stream
    assert plugin.active_request_id == "req-1"


def test_reply_with_v_accumulates(plugin):
    plugin.active_request_id = "req-1"
    plugin.accumulated_completion = ""
    handler = plugin.WebSocketHandler("ws://test")
    handler._on_message(None, json.dumps({"r": "req-1", "v": "foo"}))
    assert plugin.accumulated_completion == "foo"


def test_flush_without_v_mid_stream_delivers_full_suggestion(plugin):
    plugin.active_request_id = "req-1"
    plugin.accumulated_completion = ""
    plugin.suggestion = ""
    view = _view(plugin)
    handler = plugin.WebSocketHandler("ws://test")

    _send(handler, {"r": "req-1", "v": "foo", "flush": False})
    _send(handler, {"r": "req-1", "flush": True})
    assert plugin.active_request_id == "req-1"
    assert plugin.accumulated_completion == "foo"
    view.run_command.assert_not_called()

    _send(handler, {"r": "req-1", "v": "bar", "flush": True})
    _send(handler, {"r": "req-1", "end": True, "flush": True})

    assert plugin.suggestion == "foobar"
    assert plugin.active_request_id is None
    assert plugin.accumulated_completion == ""
    view.run_command.assert_called_once_with("trigger_ninety_five_completion")


def test_end_frame_with_text_delivers_suggestion(plugin):
    plugin.active_request_id = "req-1"
    plugin.accumulated_completion = ""
    plugin.suggestion = ""
    view = _view(plugin)
    handler = plugin.WebSocketHandler("ws://test")

    _send(handler, {"r": "req-1", "v": "foo", "flush": True})
    _send(handler, {"r": "req-1", "v": "bar", "end": True, "flush": True})

    assert plugin.suggestion == "foobar"
    assert plugin.active_request_id is None
    view.run_command.assert_called_once_with("trigger_ninety_five_completion")


def test_end_frame_with_no_text_shows_nothing(plugin):
    plugin.active_request_id = "req-1"
    plugin.accumulated_completion = ""
    plugin.suggestion = ""
    view = _view(plugin)
    handler = plugin.WebSocketHandler("ws://test")

    _send(handler, {"r": "req-1", "error": "boom", "end": True, "flush": True})

    assert plugin.active_request_id is None
    assert plugin.suggestion == ""
    view.run_command.assert_not_called()


def test_stale_request_id_is_ignored(plugin):
    plugin.active_request_id = "req-2"
    plugin.accumulated_completion = "foo"
    plugin.suggestion = ""
    view = _view(plugin)
    handler = plugin.WebSocketHandler("ws://test")

    _send(handler, {"r": "req-1", "v": "stale", "flush": True})
    _send(handler, {"r": "req-1", "end": True, "flush": True})

    assert plugin.active_request_id == "req-2"
    assert plugin.accumulated_completion == "foo"
    assert plugin.suggestion == ""
    view.run_command.assert_not_called()
