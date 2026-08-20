# Word Template Header and Footer Design

## Goal

Allow a conversion to use a selected Word `.docx` template while preserving all
of the template's header and footer content and formatting, including text,
images, tables, fields, page numbers, and first/even-page variants.

## Scope

The first release supports a `.docx` template with one Word section. The
template provides the page header and footer and its page geometry. Markdown is
rendered as a fresh document body.

The feature is available through the Python API, CLI, and desktop GUI. Existing
conversions without a Word template retain their current behavior.

## User Interface

The main conversion panel adds a `Word Template:` row below `Output File:`.
It contains a read-only path field, a `Choose...` button that filters for
`.docx`, and a `Clear` button.

The selected path belongs to the current conversion only. It is passed into the
background conversion thread as a string snapshot, so the worker never reads
Tk state. Selecting a new Markdown input does not clear the template choice.

The UI validates a non-empty template path before starting conversion. A missing
path produces an error dialog and no output is written. The selector does not
accept `.dotx`; python-docx cannot load that package type.

## API and CLI

`Converter` gains an optional `word_template` constructor argument. The value
is a path to an existing `.docx` file. It is separate from `template`, which
continues to mean a packaged YAML style template.

The CLI gains `--word-template FILE`. It may be combined with either existing
YAML style selection option because the inputs serve separate purposes:

- YAML configuration controls Markdown body rendering.
- The Word template controls the document package, section settings, and
  header/footer definitions.

## Conversion Behavior

When no Word template is selected, `Converter.to_document()` continues to call
`Document()` and applies all configured document geometry exactly as it does
today.

When a template is selected, the converter:

1. Verifies the file exists and has a `.docx` suffix.
2. Opens it with `Document(template_path)`.
3. Rejects a template that has more than one section.
4. Removes all body blocks before the final section properties element.
5. Does not apply YAML page-size or margin settings.
6. Renders Markdown into the now-empty body and saves normally.

Removing only body blocks leaves the section properties and all relationships
intact. This preserves primary, first-page, and even-page headers and footers,
their images and other relationships, header/footer distance, page size,
margins, and first/even-page settings.

Template body styles and numbering definitions are intentionally retained. A
template must contain the built-in `Heading 1` through `Heading 4`, `List
Bullet`, and `List Number` styles, along with usable bullet and decimal
numbering definitions. This is the current renderer contract and is documented
as a template authoring requirement for this release.

## Error Handling

The converter raises `FileNotFoundError` for a missing template and `ValueError`
for a non-`.docx` path or an unsupported multi-section template. CLI error
handling and the GUI conversion error dialog display these errors through their
existing pathways.

## Verification

Automated tests create a `.docx` template with formatted primary, first-page,
and even-page headers and footers, including a PNG in the primary header. After
conversion they compare every `word/header*.xml`, `word/footer*.xml`, their
relationship files, and the referenced media bytes before and after conversion.
They also assert that template body placeholder text is absent, Markdown body
text is present, and template section geometry wins over YAML values.

Additional tests cover missing, non-DOCX, and multi-section templates, CLI
option propagation, GUI selection and clearing, GUI validation, and preservation
of the no-template conversion path.

## Out of Scope

- `.dotx`, macro-enabled, encrypted, or protected templates.
- Templates with multiple sections.
- Copying only selected headers or footers from a template.
- Editing template header or footer content in md2docx.
- Persisting the selected Word template in application preferences or history.
