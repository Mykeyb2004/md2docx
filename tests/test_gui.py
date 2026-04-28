"""
Tests for GUI runtime conversion options.
"""
from md2docx.gui import Md2docxGUI


class _FakeBooleanVar:
    """Minimal BooleanVar stand-in for non-Tk unit tests."""

    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value


def test_gui_builds_runtime_override_for_auto_fix_tables():
    """Main GUI toggle should feed the table auto-fix override into conversions."""
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.auto_fix_tables_var = _FakeBooleanVar(True)

    assert gui.build_runtime_config_override() == {
        "document": {"auto_fix_tables": True}
    }
