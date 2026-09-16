"""Desktop PATH and fallback reporting for Word equations."""
import os
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import matplotlib.pyplot as plt
import pytest
from PIL import Image

from md2docx import Converter
from md2docx.cli import main
from md2docx.gui import Md2docxGUI
import md2docx.gui as gui_module
from md2docx.math_converter import MathConverter
from md2docx.omml_converter import OmmlConverter


def test_finder_discovers_pandoc_for_all_formula_locations(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('POSIX executable shebang regression')
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setenv('PATH', '/usr/bin:/bin:/usr/sbin:/sbin')
    command = tmp_path / '.local/bin/pandoc'
    command.parent.mkdir(parents=True)
    command.write_text(
        f'#!{sys.executable}\n'
        'import sys\nfrom zipfile import ZipFile\n'
        'formula = sys.stdin.read()\n'
        'math = "<m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>"\n'
        'if formula.startswith("$$"): math = "<m:oMathPara>" + math + "</m:oMathPara>"\n'
        'with ZipFile(sys.argv[sys.argv.index("-o") + 1], "w") as z:\n'
        ' z.writestr("word/document.xml", \'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><w:body><w:p>\' + math + "</w:p></w:body></w:document>")\n'
    )
    command.chmod(0o755)
    markdown = '# 标题 $x^2$\n\n正文 $x^2$。\n\n- 列表 $x^2$\n\n| 列 |\n| --- |\n| $x^2$ |\n\n$$\nx^2\n$$\n\n```latex\nx^2\n```'

    converter = Converter()
    document = converter.to_document(markdown)

    assert len(document._element.xpath('.//m:oMath')) == 6
    assert len(document.inline_shapes) == 0
    assert converter.formula_report.native == 6
    assert not converter.formula_report.fallbacks
    assert not converter.formula_report.failures


@pytest.fixture
def unavailable_pandoc(monkeypatch):
    def fail(self, latex, inline=False):
        raise ValueError('Pandoc not found')
    monkeypatch.setattr(OmmlConverter, 'latex_to_omml', fail)


@pytest.mark.parametrize('image_fails', [False, True])
def test_formula_fallbacks_and_failures_are_visible(monkeypatch, unavailable_pandoc, image_fails):
    def render(self, latex, inline=False):
        if image_fails:
            raise ValueError('Invalid formula')
        stream = BytesIO()
        Image.new('RGB', (40, 20), 'white').save(stream, format='PNG')
        return stream.getvalue()
    monkeypatch.setattr(MathConverter, 'latex_to_image', render)
    converter = Converter()
    document = converter.to_document('行内 $x^2$\n\n$$\ny^2\n$$')
    report = converter.formula_report

    assert report.total == 2 and report.native == 0
    if image_fails:
        assert len(report.failures) == 2 and not report.fallbacks
        assert [issue.index for issue in report.failures] == [1, 2]
        assert 'Invalid formula' in report.failures[0].error
        assert 'x^2' in '\n'.join(p.text for p in document.paragraphs)
        assert 'y^2' in '\n'.join(p.text for p in document.paragraphs)
    else:
        assert len(report.fallbacks) == 2 and not report.failures
        assert 'Pandoc not found' in report.fallbacks[0].error
        assert len(document.inline_shapes) == 2

    converter.to_document('No equations.')
    assert converter.formula_report.total == 0


def test_invalid_formula_closes_matplotlib_figure(tmp_path):
    converter = MathConverter(cache_dir=tmp_path)
    existing = plt.get_fignums()
    try:
        with pytest.raises(ValueError):
            converter.latex_to_image(r'\invalid{command', inline=True)
        assert plt.get_fignums() == existing
    finally:
        for number in set(plt.get_fignums()) - set(existing):
            plt.close(number)


def test_cli_warns_when_formula_loses_native_editability(tmp_path, monkeypatch, capsys, unavailable_pandoc):
    source = tmp_path / 'formula.md'
    source.write_text('公式 $x^2$')
    monkeypatch.setattr(sys, 'argv', ['md2docx', str(source)])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 2
    assert source.with_suffix('.docx').exists()
    output = capsys.readouterr()
    assert 'Pandoc not found' in output.err
    assert 'Conversion successful!' not in output.out


def test_gui_warns_when_formula_falls_back_to_image(tmp_path, monkeypatch, unavailable_pandoc):
    source = tmp_path / 'formula.md'
    source.write_text('公式 $x^2$')
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

    gui._do_conversion(str(source), str(tmp_path / 'formula.docx'))

    warning.assert_called_once()
    info.assert_not_called()
    error.assert_not_called()
    assert '公式' in warning.call_args.args[1]
    assert 'Pandoc not found' in warning.call_args.args[1]
    assert gui.add_to_history.call_args.args[2].startswith('Warning:')
