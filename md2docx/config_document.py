"""File-backed configuration state for the desktop GUI."""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from md2docx.config_utils import (
    clone_config,
    load_yaml_config,
    merge_config,
    save_yaml_config,
)


class MissingConfigPathError(RuntimeError):
    """Raised when saving a document that is not associated with a file."""


class ExternalConfigChangeError(RuntimeError):
    """Raised when the associated file changed after it was loaded or saved."""


def _file_digest(path: Path) -> Optional[str]:
    """Return a content fingerprint, or None when the file no longer exists."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _same_path(left: Path, right: Path) -> bool:
    """Compare paths after expanding them without requiring an existing file."""
    return left.expanduser().resolve(strict=False) == right.expanduser().resolve(strict=False)


@dataclass
class ConfigDocument:
    """Own the saved and editable snapshots of one GUI configuration file."""

    current_path: Optional[Path]
    saved_config: Dict[str, Any]
    draft_config: Dict[str, Any]
    dirty: bool = False
    _disk_digest: Optional[str] = field(default=None, repr=False, compare=False)

    @classmethod
    def from_defaults(cls, defaults: Dict[str, Any]) -> "ConfigDocument":
        """Create a clean document that is not yet associated with a file."""
        saved = clone_config(defaults)
        return cls(
            current_path=None,
            saved_config=saved,
            draft_config=clone_config(saved),
        )

    @classmethod
    def load(cls, path: Path, defaults: Dict[str, Any]) -> "ConfigDocument":
        """Load a file and merge it over packaged defaults."""
        resolved_path = Path(path).expanduser()
        saved = merge_config(defaults, load_yaml_config(resolved_path))
        return cls(
            current_path=resolved_path,
            saved_config=saved,
            draft_config=clone_config(saved),
            _disk_digest=_file_digest(resolved_path),
        )

    def update_draft(self, config: Dict[str, Any]) -> None:
        """Replace the editable snapshot without changing saved conversion data."""
        self.draft_config = clone_config(config)
        self.dirty = self.draft_config != self.saved_config

    def discard_draft(self) -> None:
        """Reset editable values to the last saved snapshot."""
        self.draft_config = clone_config(self.saved_config)
        self.dirty = False

    def reload(self, defaults: Dict[str, Any]) -> None:
        """Reload the associated file and discard any draft values."""
        if self.current_path is None:
            raise MissingConfigPathError("Configuration has no file path")

        loaded = type(self).load(self.current_path, defaults)
        self.saved_config = loaded.saved_config
        self.draft_config = loaded.draft_config
        self.dirty = False
        self._disk_digest = loaded._disk_digest

    def save(self, *, overwrite: bool = False) -> None:
        """Save the draft to the associated file after conflict detection."""
        if self.current_path is None:
            raise MissingConfigPathError("Configuration has no file path")

        if not overwrite and _file_digest(self.current_path) != self._disk_digest:
            raise ExternalConfigChangeError(str(self.current_path))

        save_yaml_config(self.current_path, self.draft_config)
        self.saved_config = clone_config(self.draft_config)
        self.dirty = False
        self._disk_digest = _file_digest(self.current_path)

    def save_as(self, path: Path, *, overwrite: bool = False) -> None:
        """Save the draft to a new file and associate the document with it."""
        target_path = Path(path).expanduser()
        if (
            not overwrite
            and self.current_path is not None
            and _same_path(target_path, self.current_path)
            and _file_digest(target_path) != self._disk_digest
        ):
            raise ExternalConfigChangeError(str(target_path))

        save_yaml_config(target_path, self.draft_config)
        self.current_path = target_path
        self.saved_config = clone_config(self.draft_config)
        self.dirty = False
        self._disk_digest = _file_digest(target_path)
