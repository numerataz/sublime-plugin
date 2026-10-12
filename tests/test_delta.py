import json
import random
from unittest import mock


def apply_delta(old, delta):
    start, end, text = delta
    raw = old.encode("utf-8")
    return (raw[:start] + text.encode("utf-8") + raw[end:]).decode("utf-8")


def test_no_change(plugin):
    assert plugin.compute_delta("hello", "hello") == (5, 5, "")


def test_multibyte_offsets_are_utf8_bytes(plugin):
    # "é" is 2 bytes, so the insertion point after it is byte 3
    assert plugin.compute_delta("aéb", "aéxb") == (3, 3, "x")
    assert plugin.compute_delta("a😀b", "ab") == (1, 5, "")


def test_random_round_trip(plugin):
    rng = random.Random(0)
    alphabet = "ab é😀\n"
    for _ in range(2000):
        old = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 10)))
        new = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 10)))
        assert apply_delta(old, plugin.compute_delta(old, new)) == new


def make_view(view_id, text):
    view = mock.MagicMock()
    view.id.return_value = view_id
    view.settings().get.return_value = False
    view.window().active_view.return_value = view
    view.window().folders.return_value = ["/repo"]
    view.file_name.return_value = "/repo/file.py"
    view.substr.side_effect = lambda region: view.text
    view.text = text
    return view


def sent_file_messages(ws):
    messages = [json.loads(c.args[0]) for c in ws.send_message.call_args_list]
    return [m for m in messages if m["type"] in ("file-content", "file-delta")]


def test_on_modified_sends_content_then_delta(plugin):
    plugin.websocket_instance = ws = mock.MagicMock()
    listener = plugin.NinetyFiveListener.__new__(plugin.NinetyFiveListener)
    a, b = make_view(1, "foo"), make_view(2, "bar")

    with mock.patch.object(plugin.subprocess, "check_output", return_value=""):
        listener.on_modified(a)
        a.text = "fooo"
        listener.on_modified(a)
        listener.on_modified(b)

    first, second, third = sent_file_messages(ws)
    assert first["type"] == "file-content" and first["text"] == "foo"
    assert second == {"type": "file-delta", "start": 3, "end": 3, "text": "o"}
    assert third["type"] == "file-content" and third["text"] == "bar"
