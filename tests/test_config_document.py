"""Tests for file-backed GUI configuration document state."""
from pathlib import Path

import pytest

import md2docx.config_document as config_document_module
from md2docx.config_document import (
    ConfigDocument,
    ExternalConfigChangeError,
    MissingConfigPathError,
)
from md2docx.config_utils import load_yaml_config


def test_from_defaults_owns_independent_saved_and_draft_snapshots():
    """Built-in defaults should start clean and must not retain caller references."""
    defaults = {"table": {"layout": "accent_grid"}}

    document = ConfigDocument.from_defaults(defaults)
    defaults["table"]["layout"] = "plain_grid"
    document.draft_config["table"]["layout"] = "three_line"

    assert document.current_path is None
    assert document.saved_config["table"]["layout"] == "accent_grid"
    assert document.dirty is False


def test_load_merges_file_over_defaults_and_starts_clean(tmp_path: Path):
    """A loaded document should expose one complete effective saved snapshot."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: three_line\n", encoding="utf-8")

    document = ConfigDocument.load(
        path,
        {
            "document": {"page_size": "A4"},
            "table": {"layout": "accent_grid", "alignment": "center"},
        },
    )

    assert document.current_path == path
    assert document.saved_config == {
        "document": {"page_size": "A4"},
        "table": {"layout": "three_line", "alignment": "center"},
    }
    assert document.draft_config == document.saved_config
    assert document.draft_config is not document.saved_config
    assert document.dirty is False


def test_update_and_discard_draft_are_isolated():
    """Unsaved edits must never mutate the conversion snapshot."""
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})

    document.update_draft({"table": {"layout": "three_line"}})

    assert document.dirty is True
    assert document.saved_config["table"]["layout"] == "accent_grid"

    document.discard_draft()

    assert document.draft_config == document.saved_config
    assert document.draft_config is not document.saved_config
    assert document.dirty is False


def test_save_without_path_preserves_dirty_draft():
    """A built-in document must use Save As instead of inventing a target."""
    document = ConfigDocument.from_defaults({"document": {"page_size": "A4"}})
    document.update_draft({"document": {"page_size": "Letter"}})

    with pytest.raises(MissingConfigPathError):
        document.save()

    assert document.current_path is None
    assert document.saved_config["document"]["page_size"] == "A4"
    assert document.draft_config["document"]["page_size"] == "Letter"
    assert document.dirty is True


def test_save_as_switches_path_only_after_success(tmp_path: Path):
    """Save As should associate and snapshot the new file after it is written."""
    path = tmp_path / "new.yaml"
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})
    document.update_draft({"table": {"layout": "three_line"}})

    document.save_as(path)

    assert document.current_path == path
    assert document.saved_config == document.draft_config
    assert document.dirty is False
    assert load_yaml_config(path)["table"]["layout"] == "three_line"


def test_save_as_failure_preserves_path_and_dirty_state(tmp_path: Path, monkeypatch):
    """A failed Save As must not point the document at an unwritten target."""
    path = tmp_path / "new.yaml"
    document = ConfigDocument.from_defaults({"table": {"layout": "accent_grid"}})
    document.update_draft({"table": {"layout": "three_line"}})
    monkeypatch.setattr(
        config_document_module,
        "save_yaml_config",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    with pytest.raises(OSError, match="disk full"):
        document.save_as(path)

    assert document.current_path is None
    assert document.saved_config["table"]["layout"] == "accent_grid"
    assert document.draft_config["table"]["layout"] == "three_line"
    assert document.dirty is True


def test_save_as_current_path_detects_external_file_changes(tmp_path: Path):
    """Save As must not bypass conflict detection when it selects the current file."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    document.update_draft({"table": {"layout": "three_line"}})
    path.write_text("table:\n  layout: plain_grid\n", encoding="utf-8")

    with pytest.raises(ExternalConfigChangeError):
        document.save_as(path)

    assert load_yaml_config(path)["table"]["layout"] == "plain_grid"
    assert document.draft_config["table"]["layout"] == "three_line"
    assert document.dirty is True


def test_save_failure_preserves_path_and_dirty_state(tmp_path: Path, monkeypatch):
    """A failed direct save must leave the current document fully retryable."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    document.update_draft({"table": {"layout": "three_line"}})
    monkeypatch.setattr(
        config_document_module,
        "save_yaml_config",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    with pytest.raises(OSError, match="disk full"):
        document.save()

    assert document.current_path == path
    assert document.saved_config["table"]["layout"] == "accent_grid"
    assert document.draft_config["table"]["layout"] == "three_line"
    assert document.dirty is True


def test_save_detects_external_file_changes_and_keeps_draft(tmp_path: Path):
    """A normal save must not silently overwrite another program's changes."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    document.update_draft({"table": {"layout": "three_line"}})
    path.write_text("table:\n  layout: plain_grid\n", encoding="utf-8")

    with pytest.raises(ExternalConfigChangeError):
        document.save()

    assert load_yaml_config(path)["table"]["layout"] == "plain_grid"
    assert document.saved_config["table"]["layout"] == "accent_grid"
    assert document.draft_config["table"]["layout"] == "three_line"
    assert document.dirty is True


def test_save_can_explicitly_overwrite_external_changes(tmp_path: Path):
    """Explicit overwrite should commit the draft and refresh the disk fingerprint."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    document = ConfigDocument.load(path, {})
    document.update_draft({"table": {"layout": "three_line"}})
    path.write_text("table:\n  layout: plain_grid\n", encoding="utf-8")

    document.save(overwrite=True)

    assert load_yaml_config(path)["table"]["layout"] == "three_line"
    assert document.saved_config == document.draft_config
    assert document.dirty is False


def test_reload_adopts_disk_version_and_discards_draft(tmp_path: Path):
    """Reload should resolve a conflict by replacing both in-memory snapshots."""
    path = tmp_path / "selected.yaml"
    path.write_text("table:\n  layout: accent_grid\n", encoding="utf-8")
    defaults = {"document": {"page_size": "A4"}}
    document = ConfigDocument.load(path, defaults)
    document.update_draft({"table": {"layout": "three_line"}})
    path.write_text("table:\n  layout: plain_grid\n", encoding="utf-8")

    document.reload(defaults)

    assert document.saved_config == {
        "document": {"page_size": "A4"},
        "table": {"layout": "plain_grid"},
    }
    assert document.draft_config == document.saved_config
    assert document.dirty is False
