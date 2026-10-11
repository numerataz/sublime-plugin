from unittest import mock

import pytest


class FakeSettings(dict):
    def get(self, key, default=None):
        return super().get(key, default)

    def set(self, key, value):
        self[key] = value


@pytest.fixture
def settings(plugin):
    settings = FakeSettings()
    plugin.sublime.load_settings.return_value = settings
    plugin.sublime.save_settings.reset_mock()
    plugin.sublime.windows.return_value = []
    return settings


def make_view(name="Python", scope="source.python"):
    view = mock.MagicMock()
    view.syntax.return_value.name = name
    view.syntax.return_value.scope = scope
    return view


def test_disabled_globally(plugin, settings):
    settings["enabled"] = False
    assert not plugin.is_enabled_for(make_view())


def test_disabled_by_syntax_name(plugin, settings):
    settings["disabled_syntaxes"] = ["Markdown"]
    assert not plugin.is_enabled_for(make_view("Markdown", "text.html.markdown"))


def test_disabled_by_scope(plugin, settings):
    settings["disabled_syntaxes"] = ["text.plain"]
    assert not plugin.is_enabled_for(make_view("Plain Text", "text.plain"))


def test_enabled_otherwise(plugin, settings):
    settings["disabled_syntaxes"] = ["Markdown", "text.plain"]
    assert plugin.is_enabled_for(make_view())


def test_toggle_flips_and_saves(plugin, settings):
    plugin.ToggleNinetyFiveCommand().run()
    assert settings["enabled"] is False
    plugin.sublime.save_settings.assert_called_with("NinetyFive.sublime-settings")

    plugin.ToggleNinetyFiveCommand().run()
    assert settings["enabled"] is True
