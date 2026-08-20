# Word Template Persistence Design

## Goal

Remember the last Word `.docx` template selected in the desktop GUI so it is
restored the next time the application starts.

## Scope

The feature applies only to the desktop GUI. The existing CLI and Python API
remain stateless. The existing YAML configuration preference and conversion
history behavior remain unchanged.

## Persistence

The GUI stores the selected template path in the existing
`~/.md2docx/preferences.json` file under `last_word_template_path`.

- Selecting a template records its expanded path immediately after the dialog
  returns a non-empty value.
- Clearing the template removes `last_word_template_path` while preserving
  other preference keys, including `last_config_path`.
- Preference writes merge with the existing JSON object so adding this setting
  cannot erase configuration preferences.
- Existing installations that contain only `last_config_path` or the legacy
  `config_file` key continue to load normally.

## Startup Behavior

During startup, the GUI loads the remembered template path into the read-only
template field. The path is retained even when the file no longer exists, so
the user can see which template was last used and decide whether to replace or
clear it.

If the remembered path is missing or is not a `.docx` file, the GUI shows one
warning after the main window is ready. Conversion keeps its existing
validation and refuses to start until the user selects a valid `.docx` file or
clears the field.

Unreadable or malformed preferences do not prevent startup; the GUI falls back
to its current defaults, consistent with the existing configuration preference
handling.

## Data Flow

1. `Md2docxGUI.__init__` loads the existing preferences and remembers the
   template path plus any startup warning.
2. `setup_conversion_section` initializes `word_template_var` with the loaded
   path.
3. `browse_word_template` updates the variable and persists the selected path.
4. `clear_word_template` clears the variable and removes the persisted key.
5. `convert_file` snapshots and validates the current path before starting the
   background thread, preserving the existing worker API.

## Error Handling

Preference save failures do not invalidate a selected template or block a
conversion. They use the existing warning/status path where a user-visible
warning is available. A stale path is reported once at startup and again by
the existing conversion validation if the user attempts to convert without
replacing it.

## Testing

Add focused GUI tests for:

- selecting a template persists it without removing `last_config_path`;
- a new GUI instance loads the persisted template path;
- a missing or invalid remembered path produces the startup warning payload;
- clearing a template removes only its preference key;
- legacy preference keys remain compatible;
- existing template validation and background conversion snapshot behavior stay
  unchanged.

No GUI display server is required; tests use the existing Tk stand-ins and
temporary preference files.

## Out of Scope

- Remembering multiple templates or template history.
- Persisting CLI/API choices.
- Copying or relocating template files.
- Automatically deleting stale paths.
