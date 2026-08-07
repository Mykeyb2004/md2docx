# GUI Configuration Workflow Design

## Goal

Make opening, editing, saving, and reusing YAML configuration files follow one predictable document workflow. The last successfully used file is restored on startup, unsaved editor values never affect conversion, and failed I/O never destroys the current usable state.

## State Model

`ConfigDocument` is the single source of truth:

- `current_path`: the YAML file associated with the document, or `None` for built-in defaults.
- `saved_config`: the last successfully loaded or saved effective configuration.
- `draft_config`: editable values shown by the configuration editor.
- `dirty`: whether the draft differs from the saved snapshot.

The document also keeps a private content fingerprint for detecting external file changes. Conversion reads a clone of `saved_config` only.

## User Workflow

The main window shows the current configuration plus two commands: `打开配置...` and `编辑配置...`. Opening a valid YAML file switches the document and records it as `last_config_path`. A failed open leaves both the document and preference unchanged.

The editor title identifies the current file. Its commands are `恢复内置默认`, `另存为`, `保存`, and `关闭`. Save overwrites the current file; when no file is associated, it delegates to Save As. Save As switches the document to the new file after a successful write. Restoring defaults changes only the draft.

Closing with a dirty draft asks the user to save, discard, or cancel. Saving after an external disk modification asks the user to reload, overwrite, or cancel. Reload discards the draft and adopts the disk version.

## Persistence And Errors

Preferences use `last_config_path`, while accepting the legacy `config_file` key during migration. Startup loads and validates the last file before replacing the built-in document. Missing, unreadable, or invalid YAML produces a warning and leaves built-in defaults active.

YAML saves use a temporary file in the destination directory followed by `os.replace`. State snapshots and preferences update only after the write succeeds. Successful operations update the status bar; errors and conflict decisions use dialogs.

## Removed Behavior

- Temporary applied configuration and its clear action.
- Save-as-startup-default semantics and special editable `default.yaml` target.
- YAML import inside the editor.
- Main-window `auto_fix_tables` override. The field remains editable in YAML and is read only from `saved_config` during conversion.

## Verification

Tests cover document state transitions, atomic save failure, startup restoration, transactional open, Save As path switching, dirty close choices, external modification choices, conversion isolation, preference migration, and removal of obsolete controls.
