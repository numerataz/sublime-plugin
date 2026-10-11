import importlib
import importlib.util
import os
import sys
import types
from unittest import mock

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _install_stubs():
    sublime_plugin = types.ModuleType("sublime_plugin")
    for name in ("EventListener", "TextCommand", "WindowCommand", "ApplicationCommand"):
        setattr(sublime_plugin, name, type(name, (), {}))
    sys.modules["sublime_plugin"] = sublime_plugin
    for name in ("sublime", "websocket", "requests"):
        sys.modules[name] = mock.MagicMock(name=name)


def _load_package():
    # Load the repo root as a package so NinetyFive.py's relative imports resolve
    spec = importlib.util.spec_from_file_location(
        "ninetyfive", os.path.join(ROOT, "__init__.py"), submodule_search_locations=[ROOT]
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules["ninetyfive"] = package


_install_stubs()
_load_package()


@pytest.fixture
def plugin():
    sys.modules.pop("ninetyfive.NinetyFive", None)
    return importlib.import_module("ninetyfive.NinetyFive")
