import json
import os
import re

from conftest import ROOT


def command_name(class_name):
    name = re.sub(r"Command$", "", class_name)
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def test_palette_commands_exist(plugin):
    defined = {command_name(n) for n in dir(plugin) if n.endswith("Command")}
    with open(os.path.join(ROOT, "Default.sublime-commands")) as f:
        entries = json.load(f)
    for entry in entries:
        if entry["command"] != "edit_settings":
            assert entry["command"] in defined
