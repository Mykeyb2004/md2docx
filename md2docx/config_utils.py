"""
Helpers for loading, merging, and saving YAML configuration data.
"""
import copy
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


ConfigPath = Tuple[str, ...]


def clone_config(config: Any) -> Any:
    """Return a deep copy of config data."""
    return copy.deepcopy(config)


def merge_config(base: Any, override: Any) -> Any:
    """Recursively merge override data on top of a base config."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = {key: clone_config(value) for key, value in base.items()}
        for key, value in override.items():
            if key in merged:
                merged[key] = merge_config(merged[key], value)
            else:
                merged[key] = clone_config(value)
        return merged

    if override is None:
        return None

    return clone_config(override)


def build_config_schema(default_config: Any, loaded_config: Any) -> Any:
    """Build a schema tree using default types and preserving imported extras."""
    if isinstance(default_config, dict) or isinstance(loaded_config, dict):
        default_dict = default_config if isinstance(default_config, dict) else {}
        loaded_dict = loaded_config if isinstance(loaded_config, dict) else {}

        schema = {
            key: build_config_schema(value, loaded_dict.get(key))
            for key, value in default_dict.items()
        }

        for key, value in loaded_dict.items():
            if key not in schema:
                schema[key] = clone_config(value)

        return schema

    if default_config is not None:
        return clone_config(default_config)

    return clone_config(loaded_config)


def load_yaml_config(path: Path) -> Dict[str, Any]:
    """Load YAML config from disk and ensure it is a mapping."""
    with open(path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    if not isinstance(config, dict):
        raise ValueError(f"Invalid configuration format in {path}")

    return config


def dump_yaml_config(config: Dict[str, Any]) -> str:
    """Serialize config to YAML text."""
    return yaml.safe_dump(
        config,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def _fsync_directory(path: Path) -> None:
    """Best-effort sync of a directory entry after an atomic replacement."""
    try:
        descriptor = os.open(str(path), os.O_RDONLY)
    except OSError:
        return

    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def save_yaml_config(path: Path, config: Dict[str, Any]) -> None:
    """Save config atomically so a failed write preserves the previous file."""
    path = Path(path).expanduser()
    destination = path.resolve(strict=False) if path.is_symlink() else path
    destination.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = (
        stat.S_IMODE(destination.stat().st_mode)
        if destination.exists()
        else None
    )
    temporary_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(dump_yaml_config(config))
            handle.flush()
            os.fsync(handle.fileno())

        if existing_mode is not None:
            os.chmod(temporary_path, existing_mode)

        os.replace(temporary_path, destination)
        _fsync_directory(destination.parent)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def set_value_at_path(config: Dict[str, Any], path: ConfigPath, value: Any) -> None:
    """Set a nested config value using a tuple path."""
    current = config
    for key in path[:-1]:
        current = current.setdefault(key, {})
    current[path[-1]] = value


def format_config_value(value: Any) -> str:
    """Format a config value for text input widgets."""
    if value is None:
        return ""
    return str(value)


def coerce_config_value(raw_value: Any, schema_value: Any) -> Any:
    """Convert widget input back to the expected config type."""
    if isinstance(schema_value, bool):
        return bool(raw_value)

    text = str(raw_value).strip()

    if schema_value is None:
        return None if text == "" else str(raw_value)

    if isinstance(schema_value, int) and not isinstance(schema_value, bool):
        if text == "":
            raise ValueError("Value cannot be empty")
        return int(text)

    if isinstance(schema_value, float):
        if text == "":
            raise ValueError("Value cannot be empty")
        return float(text)

    return str(raw_value)
