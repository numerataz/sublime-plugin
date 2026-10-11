import json


def test_reply_without_v_does_not_raise(plugin):
    plugin.active_request_id = "req-1"
    handler = plugin.WebSocketHandler("ws://test")
    handler._on_message(None, json.dumps({"r": "req-1"}))
    assert plugin.active_request_id is None


def test_reply_with_v_accumulates(plugin):
    plugin.active_request_id = "req-1"
    plugin.accumulated_completion = ""
    handler = plugin.WebSocketHandler("ws://test")
    handler._on_message(None, json.dumps({"r": "req-1", "v": "foo"}))
    assert plugin.accumulated_completion == "foo"
