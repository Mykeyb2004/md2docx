"""Regression tests for Finder environments and incomplete diagram conversion."""
import os
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from docx import Document
from PIL import Image

from md2docx import Converter
from md2docx.cli import main
from md2docx.gui import Md2docxGUI
import md2docx.gui as gui_module
from md2docx.mermaid_converter import MermaidConverter


@pytest.fixture
def png_bytes():
    stream = BytesIO()
    Image.new('RGB', (80, 40), 'white').save(stream, format='PNG')
    return stream.getvalue()


@pytest.fixture
def finder_runtime(tmp_path, monkeypatch, png_bytes):
    """Install executable shims that exercise the real env-node subprocess chain."""
    if os.name == 'nt':
        pytest.skip('POSIX executable shebang regression')
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setenv('PATH', '/usr/bin:/bin:/usr/sbin:/sbin')
    monkeypatch.delenv('NVM_BIN', raising=False)
    monkeypatch.delenv('NVM_DIR', raising=False)
    runtime = tmp_path / '.nvm/versions/node/v22.7.0/bin'
    runtime.mkdir(parents=True)
    command = runtime / 'mmdc'
    command.write_text('#!/usr/bin/env node\n')
    node = runtime / 'node'
    node.write_text(
        f'#!{sys.executable}\n'
        'import sys\nfrom pathlib import Path\n'
        f'Path(sys.argv[sys.argv.index("-o") + 1]).write_bytes({png_bytes!r})\n'
    )
    command.chmod(0o755)
    node.chmod(0o755)
    return command


@pytest.mark.parametrize('absolute_command', [False, True])
def test_finder_conversion_finds_mmdc_and_its_node(finder_runtime, tmp_path, absolute_command):
    original_path = os.environ['PATH']
    converter = Converter(config_override={
        'mermaid': {'command': str(finder_runtime) if absolute_command else 'mmdc'},
    })
    output = tmp_path / 'diagram.docx'
    converter.convert_string('```mermaid\ngraph TD\nA-->B\n```', str(output))

    assert len(Document(output).inline_shapes) == 1
    assert os.environ['PATH'] == original_path


def test_missing_explicit_command_does_not_use_another_mmdc(finder_runtime, tmp_path):
    converter = MermaidConverter(cache_dir=tmp_path / 'cache', command=str(tmp_path / 'missing/mmdc'))
    assert not converter.is_available()


@pytest.fixture
def mixed_diagrams(monkeypatch, png_bytes):
    def render(self, code):
        if 'Broken' in code:
            try:
                raise ValueError('Lexical error on line 2.\nA -- > Broken\n------^')
            except ValueError as exc:
                raise ValueError('Failed to render Mermaid diagram') from exc
        return png_bytes

    monkeypatch.setattr(MermaidConverter, 'mermaid_to_image', render)
    return '```mermaid\ngraph TD\nA-->B\n```\n\n```mermaid\ngraph TD\nA -- > Broken\n```'


def test_conversion_reports_failures_and_resets_for_next_document(tmp_path, mixed_diagrams):
    converter = Converter()
    output = tmp_path / 'mixed.docx'
    converter.convert_string(mixed_diagrams, str(output))
    report = converter.mermaid_report

    assert len(Document(output).inline_shapes) == 1
    assert report.total == 2
    assert report.succeeded == 1
    assert report.failures[0].index == 2
    assert 'Lexical error' in report.failures[0].error
    assert 'A -- > Broken' in report.failures[0].error

    converter.convert_string('No diagrams.', str(tmp_path / 'next.docx'))
    assert converter.mermaid_report.total == 0
    assert not converter.mermaid_report.failures


@pytest.mark.parametrize('directory_input', [False, True])
def test_cli_marks_incomplete_conversion_and_keeps_output(tmp_path, monkeypatch, capsys, mixed_diagrams, directory_input):
    source = tmp_path / 'input'
    source.mkdir()
    markdown = source / 'mixed.md'
    markdown.write_text(mixed_diagrams)
    if directory_input:
        (source / 'clean.md').write_text('Clean document.')
    output = tmp_path / 'output'
    monkeypatch.setattr(sys, 'argv', ['md2docx', str(source if directory_input else markdown), '--output-dir', str(output)])

    with pytest.raises(SystemExit) as raised:
        main()

    assert raised.value.code == 2
    assert (output / 'mixed.docx').exists()
    if directory_input:
        assert (output / 'clean.docx').exists()
    captured = capsys.readouterr()
    assert 'Mermaid' in captured.err and '2' in captured.err
    assert 'Lexical error' in captured.err
    assert 'Conversion successful!' not in captured.out


def test_gui_warns_instead_of_success_for_missing_diagrams(tmp_path, monkeypatch, mixed_diagrams):
    source = tmp_path / 'mixed.md'
    source.write_text(mixed_diagrams)
    gui = Md2docxGUI.__new__(Md2docxGUI)
    gui.root = SimpleNamespace(after=lambda delay, callback: callback(), update_idletasks=lambda: None)
    gui.progress = Mock()
    gui.status_var = Mock()
    gui.build_effective_conversion_config = lambda: {}
    gui.dialog_parent = lambda: gui.root
    gui.add_to_history = Mock()
    gui.refresh_history_list = Mock()
    warning, info, error = Mock(), Mock(), Mock()
    monkeypatch.setattr(gui_module.messagebox, 'showwarning', warning)
    monkeypatch.setattr(gui_module.messagebox, 'showinfo', info)
    monkeypatch.setattr(gui_module.messagebox, 'showerror', error)

    gui._do_conversion(str(source), str(tmp_path / 'mixed.docx'))

    warning.assert_called_once()
    info.assert_not_called()
    error.assert_not_called()
    message = warning.call_args.args[1]
    assert '1/2' in message and 'Lexical error' in message
    assert gui.add_to_history.call_args.args[2].startswith('Warning:')
    assert '警告' in gui.status_var.set.call_args.args[0]
