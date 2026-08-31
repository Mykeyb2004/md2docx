# Word Template History and Toggle Design

## Goal

Improve the desktop GUI's optional Word-template workflow by remembering recent
templates in a selectable drop-down and allowing the current conversion to
ignore the selected template without losing that selection.

## Scope

The feature applies only to the desktop GUI. The CLI, Python API, converter,
configuration workflow, and conversion-history format remain unchanged.

## User Interface

Replace the read-only Word-template entry with a read-only `ttk.Combobox` that
shows up to ten recently selected `.docx` template paths.

The template row contains these controls in order:

1. A `使用 Word 模板` checkbutton, enabled by default for every application
   launch.
2. The template-history combobox, displaying the current template and recent
   paths.
3. The existing `选择...` button for browsing to a new template.
4. The existing `清除` button for clearing the current selection.

Turning off `使用 Word 模板` keeps the current template visible and retains the
history, but the current and subsequent conversions in that application session
do not receive a Word template until the user turns the checkbutton on again.
The enabled state is not persisted, so each application launch starts enabled.

Selecting a template with the file dialog adds it to the front of the history,
removes a duplicate of the same expanded path, selects it, and persists the
updated state. Selecting an older item from the combobox applies the same
most-recently-used ordering. The list is capped at ten entries.

`清除` clears only the current template selection and removes
`last_word_template_path`. It does not erase `word_template_history`, so a
template can be selected again from the combobox.

## Persistence and Compatibility

The existing `~/.md2docx/preferences.json` remains the only persistence file.
It stores:

- `last_word_template_path`: the current selected template, retained for
  backward compatibility;
- `word_template_history`: an array of at most ten template path strings,
  ordered most recently selected first.

Preference writes merge with all existing keys. Existing installations with
only `last_word_template_path` seed the history with that path when loaded.
Missing, malformed, non-string, blank, and duplicate history items are ignored.
The in-memory list is normalized and bounded even if a manually edited
preference file contains invalid or excessive entries.

Paths are expanded before storage and comparison. The GUI does not copy,
relocate, or automatically delete template files.

## Data Flow

1. `Md2docxGUI.__init__` loads the current template, normalized history, and a
   warning for an unusable current path.
2. `setup_conversion_section` creates an enabled Boolean variable and builds the
   combobox from the loaded history.
3. Browsing or choosing from the combobox records the selected template through
   one shared most-recently-used update path.
4. Clearing removes only the current selection while retaining the history.
5. `selected_word_template` returns an empty string when template use is
   disabled; otherwise it returns the selected combobox value.
6. `convert_file` keeps its existing validation and background-thread contract.
   Because disabled template use produces an empty string, no template is
   validated or passed to the worker for that conversion.

## Error Handling

The existing startup warning applies only to the current selected template.
Missing files and paths with a non-`.docx` suffix remain visible in history; they
are rejected by the existing conversion validation only after being selected
while template use is enabled.

Malformed or unreadable preferences fall back to an empty history and no current
selection. A preference write failure does not undo the user's in-memory
selection and does not block conversion; it uses the existing user-visible
warning behavior.

## Testing

Focused GUI tests will verify:

- a legacy `last_word_template_path` seeds the history;
- malformed, blank, duplicate, and excessive history values are normalized;
- browsing adds a template to the front without dropping unrelated preferences;
- selecting a historical item makes it current and moves it to the front;
- clearing removes the current path but preserves history;
- the combobox initializes with the normalized values and current selection;
- disabling template use preserves the selection but skips template validation
  and excludes the template from background-thread arguments;
- template use starts enabled for every GUI construction;
- the existing enabled-template validation and worker handoff continue to work.

All tests use the existing Tk stand-ins and temporary preference files, so they
do not require a display server.

## Out of Scope

- Persisting the template-use checkbutton state.
- Adding template history to the CLI or Python API.
- Recording the selected template in conversion-history entries.
- Providing a separate history-management dialog.
- Automatically deleting stale template paths.
