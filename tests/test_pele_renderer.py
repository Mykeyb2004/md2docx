"""Unit tests for the in-process Pele + QuickJS + resvg Mermaid renderer."""

from concurrent.futures import ThreadPoolExecutor
import io
import pytest
from PIL import Image

from md2docx.pele_renderer import (
    PELE_RENDERER_VERSION,
    PeleRenderError,
    PeleRenderer,
    is_pele_available,
)


class TestPeleRendererAvailability:
    """Tests for runtime availability and version metadata."""

    def test_pele_is_available(self) -> None:
        assert is_pele_available() is True
        assert isinstance(PELE_RENDERER_VERSION, str)
        assert len(PELE_RENDERER_VERSION) > 0


class TestPeleDiagramTypes:
    """Tests rendering across major Mermaid diagram types."""

    @pytest.mark.parametrize(
        "diagram_code",
        [
            "flowchart TD\n  A[开始] --> B{判断条件}\n  B -->|是| C[执行处理]\n  B -->|否| D[结束]",
            "graph LR\n  User[用户终端] --> GW[API网关] --> DB[(业务数据库)]",
            "sequenceDiagram\n  participant U as 申请人\n  participant S as 审批系统\n  U->>S: 提交救助申请\n  S-->>U: 返回受理编号",
            "mindmap\n  root((社会救助体系))\n    最低生活保障\n    特困人员供养\n    临时救助服务",
            "gantt\n  title 项目实施进度计划\n  dateFormat YYYY-MM-DD\n  section 一期建设\n  需求调研 :a1, 2026-01-01, 7d\n  系统开发 :after a1, 14d",
        ],
    )
    def test_renders_supported_diagram_types_to_png(self, diagram_code: str) -> None:
        renderer = PeleRenderer()
        png_bytes = renderer.render_png(diagram_code)

        assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        with Image.open(io.BytesIO(png_bytes)) as img:
            assert img.format == "PNG"
            assert img.width >= 80
            assert img.height >= 40


class TestPeleSvgPostProcessingAndThemes:
    """Tests CSS variable resolution, rounded rect attributes, color-mix, and themes."""

    def test_svg_resolves_all_css_vars_color_mix_and_rect_rx(self) -> None:
        renderer = PeleRenderer()
        # Nested subgraphs + edge crossover trigger pele-cluster-title with color-mix(...)
        code = (
            "flowchart TD\n"
            "  Start[外部入口] --> InnerA\n"
            "  subgraph Outer[外层业务域]\n"
            "    subgraph Inner[核心子系统]\n"
            "      InnerA[服务节点A<br/>第二行说明] -->|条件跳转| InnerB[服务节点B]\n"
            "    end\n"
            "  end\n"
            "  style InnerB fill:#FFE8CC,stroke:#D97706,rx:6px"
        )
        svg = renderer.render_svg(
            code,
            theme="base",
            background_color="white",
            theme_variables={
                "primaryColor": "#E8F1FF",
                "primaryTextColor": "#163A70",
                "primaryBorderColor": "#2F6BFF",
                "lineColor": "#2F6BFF",
                "clusterBkg": "#F7FBFF",
                "clusterBorder": "#9AB8E8",
                "edgeLabelBackground": "#FFFFFF",
            },
        )

        assert "var(--_" not in svg
        assert "var(--pele-" not in svg
        assert "color-mix(" not in svg
        assert 'rx="4"' in svg
        assert "#E8F1FF" in svg
        assert "#163A70" in svg
        assert "#2F6BFF" in svg
        assert "#F7FBFF" in svg
        assert "#9AB8E8" in svg

        png_bytes = renderer.render_png(
            code,
            theme="base",
            background_color="white",
            theme_variables={
                "primaryColor": "#E8F1FF",
                "primaryTextColor": "#163A70",
                "primaryBorderColor": "#2F6BFF",
                "lineColor": "#2F6BFF",
                "clusterBkg": "#F7FBFF",
                "clusterBorder": "#9AB8E8",
                "edgeLabelBackground": "#FFFFFF",
            },
        )
        with Image.open(io.BytesIO(png_bytes)) as img:
            assert img.width > 100
            assert img.height > 100

    @pytest.mark.parametrize("theme_name", ["default", "base", "dark", "forest", "neutral"])
    def test_theme_presets_render_valid_png(self, theme_name: str) -> None:
        renderer = PeleRenderer()
        png_bytes = renderer.render_png("flowchart LR\n  A[节点一] --> B[节点二]", theme=theme_name)
        with Image.open(io.BytesIO(png_bytes)) as img:
            assert img.width > 50
            assert img.height > 30

    def test_transparent_and_custom_background_colors(self) -> None:
        renderer = PeleRenderer()
        code = "flowchart LR\n  A[透明背景测试] -->|边标签| B[结果节点]"

        png_transparent = renderer.render_png(code, background_color="transparent")
        with Image.open(io.BytesIO(png_transparent)) as img:
            rgba = img.convert("RGBA")
            # Top-left padding pixel must be fully transparent
            assert rgba.getpixel((0, 0))[3] == 0

        png_cream = renderer.render_png(code, background_color="#FFF8E7")
        with Image.open(io.BytesIO(png_cream)) as img:
            rgba = img.convert("RGBA")
            assert rgba.getpixel((0, 0)) == (255, 248, 231, 255)


class TestPeleScaleAndThreading:
    """Tests scale factor (default 1.0) and multi-threaded rendering safety."""

    def test_default_scale_is_one_and_scale_two_doubles_dimensions(self) -> None:
        renderer = PeleRenderer()
        code = "flowchart LR\n  A[输入模块] --> B[处理模块]"

        png_default = renderer.render_png(code)
        png_none = renderer.render_png(code, scale=None)
        png_one = renderer.render_png(code, scale=1.0)
        png_two = renderer.render_png(code, scale=2.0)

        with Image.open(io.BytesIO(png_default)) as img_def, \
             Image.open(io.BytesIO(png_none)) as img_none, \
             Image.open(io.BytesIO(png_one)) as img_one, \
             Image.open(io.BytesIO(png_two)) as img_two:
            assert img_def.size == img_one.size
            assert img_none.size == img_one.size
            assert img_two.width == img_one.width * 2
            assert img_two.height == img_one.height * 2

    def test_multithreaded_rendering_is_thread_safe(self) -> None:
        renderer = PeleRenderer()
        diagrams = [
            f"flowchart LR\n  N{i}[并发节点_{i}_中文测试] --> M{i}[目标节点_{i}]"
            for i in range(16)
        ]

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(renderer.render_png, diagrams))

        assert len(results) == 16
        for data in results:
            assert data.startswith(b"\x89PNG\r\n\x1a\n")
            with Image.open(io.BytesIO(data)) as img:
                assert img.width > 80


class TestPeleErrorHandling:
    """Tests error reporting on invalid Mermaid syntax."""

    def test_invalid_syntax_raises_pele_render_error(self) -> None:
        renderer = PeleRenderer()
        with pytest.raises(PeleRenderError) as exc_info:
            renderer.render_png("flowchart TD\n  A[正常节点] -- > B[错误箭头]")

        err = exc_info.value
        assert isinstance(err, ValueError)
        assert "line" in str(err).lower() or "error" in str(err).lower()
        assert err.line is None or err.line >= 1

    def test_empty_code_raises_value_error(self) -> None:
        renderer = PeleRenderer()
        with pytest.raises(ValueError):
            renderer.render_png("   \n  ")
