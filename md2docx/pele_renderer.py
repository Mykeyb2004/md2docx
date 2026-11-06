"""In-process Mermaid diagram renderer using Obsidian Pele, QuickJS, and resvg-py.

This module provides high-performance, self-contained Mermaid diagram rendering
without requiring external Node.js or @mermaid-js/mermaid-cli installations.
"""

from __future__ import annotations

import glob
import io
import json
import os
import pkgutil
import re
import sys
import threading
from typing import Any, Dict, List, Optional, Tuple
from PIL import ImageFont

try:
    import quickjs  # type: ignore[import-untyped]
except ImportError:
    quickjs = None  # type: ignore[assignment]

try:
    import resvg_py  # type: ignore[import-untyped]
except ImportError:
    resvg_py = None  # type: ignore[assignment]

PELE_RENDERER_VERSION = "1.13.1"

# CJK and common font discovery candidates
_FONT_CANDIDATES: List[str] = [
    # macOS AssetsV2 PingFang (dynamic lookup added at runtime)
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    # Windows
    "C:\\Windows\\Fonts\\msyh.ttc",
    "C:\\Windows\\Fonts\\msyhl.ttc",
    "C:\\Windows\\Fonts\\simhei.ttf",
    "C:\\Windows\\Fonts\\simsun.ttc",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
]

_CACHED_FONT_PATH: Optional[str] = None
_FONT_DISCOVERY_LOCK = threading.Lock()


def _discover_best_font_path() -> Optional[str]:
    """Find the best available CJK TrueType font path on the current system."""
    global _CACHED_FONT_PATH
    if _CACHED_FONT_PATH is not None:
        return _CACHED_FONT_PATH

    with _FONT_DISCOVERY_LOCK:
        if _CACHED_FONT_PATH is not None:
            return _CACHED_FONT_PATH

        # On macOS, check AssetsV2 for PingFang
        if sys.platform == "darwin":
            assets = glob.glob("/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc")
            if assets and os.path.exists(assets[0]):
                _CACHED_FONT_PATH = assets[0]
                return _CACHED_FONT_PATH

        for candidate in _FONT_CANDIDATES:
            if os.path.exists(candidate):
                _CACHED_FONT_PATH = candidate
                return _CACHED_FONT_PATH

        _CACHED_FONT_PATH = ""
        return None


class PeleRenderError(ValueError):
    """Exception raised when Pele fails to parse or render Mermaid source."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        snippet: Optional[str] = None,
        mermaid_type: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.line = line
        self.column = column
        self.snippet = snippet
        self.mermaid_type = mermaid_type


def is_pele_available() -> bool:
    """Check whether Pele in-process rendering dependencies are available."""
    if quickjs is None or resvg_py is None:
        return False
    try:
        data = pkgutil.get_data("md2docx", "vendor/pele/pele.global.js")
        return bool(data and len(data) > 0)
    except Exception:
        return False


def _parse_color_to_rgb(color_str: str) -> Tuple[int, int, int]:
    """Convert a hex, rgb, or named color string to an RGB tuple."""
    c = color_str.strip().lower()
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        elif len(h) == 4:
            h = "".join(ch * 2 for ch in h[:3])
        elif len(h) >= 6:
            h = h[:6]
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    if c == "white":
        return (255, 255, 255)
    if c == "black":
        return (0, 0, 0)
    if c == "transparent":
        return (255, 255, 255)
    rgb_match = re.match(r"rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)", c)
    if rgb_match:
        return (
            int(round(float(rgb_match.group(1)))),
            int(round(float(rgb_match.group(2)))),
            int(round(float(rgb_match.group(3)))),
        )
    return (240, 240, 240)


def _mix_srgb(c1: str, pct_str: str, c2: str) -> str:
    """Evaluate CSS color-mix(in srgb, c1 pct%, c2) to a hex string."""
    try:
        pct = float(pct_str) / 100.0
    except ValueError:
        pct = 0.5
    pct = max(0.0, min(1.0, pct))
    r1, g1, b1 = _parse_color_to_rgb(c1)
    r2, g2, b2 = _parse_color_to_rgb(c2)
    r = int(round(r1 * pct + r2 * (1.0 - pct)))
    g = int(round(g1 * pct + g2 * (1.0 - pct)))
    b = int(round(b1 * pct + b2 * (1.0 - pct)))
    return f"#{r:02x}{g:02x}{b:02x}"


class _ThreadLocalPeleContext:
    """Thread-local container managing QuickJS instance and text measurer."""

    def __init__(self) -> None:
        if quickjs is None:
            raise RuntimeError("QuickJS is not available.")

        bundle_data = pkgutil.get_data("md2docx", "vendor/pele/pele.global.js")
        if not bundle_data:
            raise RuntimeError("Vendored pele.global.js bundle not found in md2docx package.")

        self.ctx = quickjs.Context()
        self.ctx.eval(bundle_data.decode("utf-8"))

        self._font_cache: Dict[Tuple[int, bool], Any] = {}
        self._measure_cache: Dict[Tuple[str, int, int], float] = {}
        self._font_path = _discover_best_font_path()

        # Register measurement callback for Pele
        self.ctx.add_callable("__py_measure_width", self._measure_width)
        self.ctx.eval(
            """
            var __customMeasurer = {
                width: function(text, size, style) {
                    return __py_measure_width(text, size, style || 0);
                }
            };
            function __peleRender(source, optsJson) {
                var opts = optsJson ? JSON.parse(optsJson) : {};
                opts.measurer = __customMeasurer;
                try {
                    var res = pele.render(source, opts);
                    return JSON.stringify({ ok: true, result: res });
                } catch (e) {
                    return JSON.stringify({
                        ok: false,
                        name: e.name || 'Error',
                        code: e.code || 'syntax',
                        message: e.message || String(e),
                        line: e.line || 0,
                        column: e.column || 0,
                        snippet: e.snippet || '',
                        mermaidType: e.mermaidType || null
                    });
                }
            }
            """
        )

    def _get_font(self, size: int, bold: bool) -> Any:
        key = (size, bold)
        if key in self._font_cache:
            return self._font_cache[key]
        font: Any = None
        if self._font_path:
            try:
                font = ImageFont.truetype(self._font_path, size)
            except Exception:
                font = None
        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
        self._font_cache[key] = font
        return font

    def _measure_width(self, text: str, size: float, style: int) -> float:
        if not text:
            return 0.0
        sz = max(1, int(round(size)))
        is_bold = bool(style & 1)
        cache_key = (text, sz, style)
        cached = self._measure_cache.get(cache_key)
        if cached is not None:
            return cached

        font = self._get_font(sz, is_bold)
        if font and hasattr(font, "getlength"):
            try:
                width = float(font.getlength(text))
                self._measure_cache[cache_key] = width
                return width
            except Exception:
                pass

        # Fallback approximation: CJK / wide characters ~1.0 * sz, others ~0.6 * sz
        w = 0.0
        for ch in text:
            w += sz if ord(ch) > 127 else sz * 0.6
        if is_bold:
            w *= 1.05
        self._measure_cache[cache_key] = w
        return w


class PeleRenderer:
    """In-process Mermaid renderer using Obsidian Pele and resvg-py."""

    # Built-in theme palette mappings
    THEME_PRESETS: Dict[str, Dict[str, str]] = {
        "default": {
            "--pele-bg": "#ffffff",
            "--pele-fg": "#333333",
            "--pele-muted": "#666666",
            "--pele-line": "#333333",
            "--pele-surface": "#ececff",
            "--pele-surface-alt": "#ffffde",
            "--pele-border": "#ccccff",
            "--pele-accent": "#5b7bd5",
        },
        "base": {
            "--pele-bg": "#ffffff",
            "--pele-fg": "#1f1f1f",
            "--pele-muted": "#6e6e6e",
            "--pele-line": "#1f1f1f",
            "--pele-surface": "#f3f3f3",
            "--pele-surface-alt": "#e6e6e6",
            "--pele-border": "#8a8a8a",
            "--pele-accent": "#5b7bd5",
        },
        "dark": {
            "--pele-bg": "#1f2022",
            "--pele-fg": "#f0f0f0",
            "--pele-muted": "#a0a0a0",
            "--pele-line": "#a0a0a0",
            "--pele-surface": "#2d3139",
            "--pele-surface-alt": "#252830",
            "--pele-border": "#505560",
            "--pele-accent": "#61afef",
        },
        "forest": {
            "--pele-bg": "#ffffff",
            "--pele-fg": "#2e3440",
            "--pele-muted": "#4c566a",
            "--pele-line": "#2e3440",
            "--pele-surface": "#e5e9f0",
            "--pele-surface-alt": "#d8dee9",
            "--pele-border": "#88c0d0",
            "--pele-accent": "#81a1c1",
        },
        "neutral": {
            "--pele-bg": "#ffffff",
            "--pele-fg": "#222222",
            "--pele-muted": "#666666",
            "--pele-line": "#444444",
            "--pele-surface": "#f4f4f4",
            "--pele-surface-alt": "#eeeeee",
            "--pele-border": "#cccccc",
            "--pele-accent": "#666666",
        },
    }

    def __init__(
        self,
        font_family: Optional[str] = None,
        font_size: int = 16,
    ) -> None:
        if not is_pele_available():
            raise RuntimeError("Pele renderer requires quickjs and resvg-py (Python >= 3.10).")

        self.font_family = font_family or "PingFang SC, Microsoft YaHei, Heiti SC, sans-serif"
        self.font_size = font_size
        self._local = threading.local()

    def _get_thread_context(self) -> _ThreadLocalPeleContext:
        ctx = getattr(self._local, "context", None)
        if ctx is None:
            ctx = _ThreadLocalPeleContext()
            self._local.context = ctx
        return ctx

    def _build_css_variable_map(
        self,
        raw_svg: str,
        theme: str,
        background_color: str,
        theme_variables: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Construct a complete dictionary mapping CSS variables to concrete values."""
        var_map: Dict[str, str] = dict(self.THEME_PRESETS.get(theme, self.THEME_PRESETS["base"]))

        # Base defaults
        var_map.setdefault("--pele-radius", "4px")
        var_map.setdefault("--pele-critical", "#e45756")
        var_map.setdefault("--pele-error", "#e45756")
        var_map.setdefault("--pele-fg-on-dark", "#ffffff")
        var_map.setdefault("--pele-fg-on-light", "#1f1f1f")
        var_map.setdefault("--pele-font", self.font_family)
        var_map.setdefault("--pele-font-mono", "monospace")

        # Background color
        bg = background_color.strip().lower()
        if bg and bg != "transparent":
            var_map["--pele-bg"] = background_color
        else:
            var_map["--pele-bg"] = "#ffffff"

        # Apply theme_variables overrides
        if theme_variables:
            if "primaryColor" in theme_variables:
                var_map["--pele-surface"] = str(theme_variables["primaryColor"])
            if "primaryTextColor" in theme_variables:
                var_map["--pele-fg"] = str(theme_variables["primaryTextColor"])
            if "primaryBorderColor" in theme_variables:
                var_map["--pele-border"] = str(theme_variables["primaryBorderColor"])
            if "lineColor" in theme_variables:
                var_map["--pele-line"] = str(theme_variables["lineColor"])
            if "secondaryColor" in theme_variables:
                var_map["--pele-accent"] = str(theme_variables["secondaryColor"])
            if "clusterBkg" in theme_variables:
                var_map["--pele-surface-alt"] = str(theme_variables["clusterBkg"])

        # Extract any inline series variables injected by Pele on root style (e.g. ;--pele-series-1:#4c78a8)
        for m in re.finditer(r"--(pele-series-\d+)\s*:\s*([^;\"}]+)", raw_svg):
            var_map["--" + m.group(1)] = m.group(2).strip()

        # Build internal shorthand map
        var_map["--_bg"] = var_map["--pele-bg"]
        var_map["--_fg"] = var_map["--pele-fg"]
        var_map["--_m"] = var_map["--pele-muted"]
        var_map["--_l"] = var_map["--pele-line"]
        var_map["--_s"] = var_map["--pele-surface"]
        var_map["--_a"] = var_map["--pele-surface-alt"]
        var_map["--_b"] = var_map["--pele-border"]
        var_map["--_c"] = var_map["--pele-accent"]
        var_map["--_r"] = var_map["--pele-radius"]
        var_map["--_tw"] = "bold"
        var_map["--_hw"] = "bold"
        var_map["--_w"] = "bold"
        var_map["--_fm"] = var_map["--pele-font-mono"]

        return var_map

    def _postprocess_svg(
        self,
        raw_svg: str,
        theme: str,
        background_color: str,
        theme_variables: Optional[Dict[str, Any]],
    ) -> str:
        """Resolve all CSS variables, convert CSS rx to attributes, and evaluate color-mix."""
        var_map = self._build_css_variable_map(raw_svg, theme, background_color, theme_variables)
        svg = raw_svg

        # 1. Substitute var(--name, fallback) or var(--name)
        def replace_var(match: re.Match[str]) -> str:
            name = match.group(1)
            fallback = match.group(2)
            if name in var_map:
                return var_map[name]
            if fallback is not None:
                return fallback.strip()
            return ""

        var_pattern = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)(?:\s*,\s*([^)]+))?\s*\)")
        for _ in range(6):
            if not var_pattern.search(svg):
                break
            svg = var_pattern.sub(replace_var, svg)

        # 2. Evaluate color-mix(in srgb, color1 pct%, color2)
        mix_pattern = re.compile(r"color-mix\(\s*in\s+srgb\s*,\s*([^%]+?)\s+([0-9.]+)%\s*,\s*([^)]+)\)")
        for _ in range(3):
            if not mix_pattern.search(svg):
                break
            svg = mix_pattern.sub(lambda m: _mix_srgb(m.group(1), m.group(2), m.group(3)), svg)

        # 3. Apply clusterBorder and edgeLabelBackground if specified
        if theme_variables:
            cluster_border = theme_variables.get("clusterBorder")
            if cluster_border:
                # Update stroke on .pele-cluster rect
                svg = re.sub(
                    r'(<g class="pele-cluster"[^>]*>\s*<rect\b[^>]*?)(stroke="[^"]*")',
                    rf'\1stroke="{cluster_border}"',
                    svg,
                )
            edge_label_bg = theme_variables.get("edgeLabelBackground")
            if edge_label_bg:
                # Update fill on .pele-edge-label rect
                svg = re.sub(
                    r'(<g class="pele-edge-label"[^>]*>\s*<rect\b[^>]*?)(fill="[^"]*")',
                    rf'\1fill="{edge_label_bg}"',
                    svg,
                )

        # 4. Convert style="...rx:4px..." on <rect> to rx="4" XML attribute for resvg compatibility
        def fix_rect_rx(m: re.Match[str]) -> str:
            tag = m.group(0)
            rx_m = re.search(r"rx:\s*([0-9.]+)(?:px)?", tag)
            if rx_m and 'rx="' not in tag:
                rx_val = rx_m.group(1)
                # Remove rx from style attribute
                tag = re.sub(r"rx:\s*[0-9.]+(?:px)?;?", "", tag)
                tag = re.sub(r'style="\s*"', "", tag)
                if tag.endswith("/>"):
                    tag = tag[:-2] + f' rx="{rx_val}"/>'
                elif tag.endswith(">"):
                    tag = tag[:-1] + f' rx="{rx_val}">'
            return tag

        svg = re.sub(r"<rect\b[^>]*>", fix_rect_rx, svg)

        # 5. Strip all CSS custom properties (--name: value;) from style attributes
        # resvg's CSS parser does not support CSS custom property declarations in inline style="..."
        # and silently drops the entire style attribute (including critical root font and font-family).
        def clean_style_vars(m: re.Match[str]) -> str:
            s = m.group(1)
            s = re.sub(r"--[a-zA-Z0-9_-]+\s*:[^;]+;?", "", s)
            s = s.strip("; ")
            return f'style="{s}"' if s else ""

        svg = re.sub(r'style="([^"]*)"', clean_style_vars, svg)

        # 6. Ensure root <svg> has explicit font-family attribute as defense-in-depth for resvg font resolution
        if 'font-family=' not in svg[:300]:
            svg = re.sub(r"<svg\b", f'<svg font-family="{self.font_family}"', svg, count=1)

        return svg

    def render_svg(
        self,
        code: str,
        theme: str = "base",
        background_color: str = "white",
        theme_variables: Optional[Dict[str, Any]] = None,
        font_family: Optional[str] = None,
        font_size: Optional[int] = None,
    ) -> str:
        """Render Mermaid diagram source to a standalone, fully-resolved SVG string."""
        clean_code = code.strip()
        if not clean_code:
            raise ValueError("Mermaid diagram code cannot be empty.")

        thread_ctx = self._get_thread_context()
        ff = font_family or self.font_family
        fs = font_size or self.font_size

        opts: Dict[str, Any] = {
            "responsive": False,
            "fontFamily": ff,
            "fontSize": fs,
        }
        if theme_variables:
            opts["config"] = {"themeVariables": theme_variables}

        thread_ctx.ctx.set("__current_src", clean_code)
        thread_ctx.ctx.set("__current_opts", json.dumps(opts))
        raw_res = thread_ctx.ctx.eval("__peleRender(__current_src, __current_opts)")
        data = json.loads(raw_res)

        if not data.get("ok"):
            raise PeleRenderError(
                message=data.get("message", "Unknown Pele rendering error"),
                code=data.get("code"),
                line=data.get("line"),
                column=data.get("column"),
                snippet=data.get("snippet"),
                mermaid_type=data.get("mermaidType"),
            )

        raw_svg = data["result"]["svg"]
        return self._postprocess_svg(
            raw_svg=raw_svg,
            theme=theme,
            background_color=background_color,
            theme_variables=theme_variables,
        )

    def render_png(
        self,
        code: str,
        theme: str = "base",
        background_color: str = "white",
        theme_variables: Optional[Dict[str, Any]] = None,
        font_family: Optional[str] = None,
        font_size: Optional[int] = None,
        scale: Optional[float] = None,
    ) -> bytes:
        """Render Mermaid diagram source to PNG bytes.

        Args:
            code: Mermaid diagram source code.
            theme: Theme preset name ("default", "base", "dark", "forest", "neutral").
            background_color: Background color ("white", "#RRGGBB", or "transparent").
            theme_variables: Optional theme variable overrides.
            font_family: Font family string.
            font_size: Font size in pixels (default: 16).
            scale: Pixel zoom factor. Defaults to 1.0.

        Returns:
            PNG image bytes.
        """
        svg_str = self.render_svg(
            code=code,
            theme=theme,
            background_color=background_color,
            theme_variables=theme_variables,
            font_family=font_family,
            font_size=font_size,
        )

        effective_scale = float(scale) if scale is not None else 1.0
        if effective_scale <= 0.0:
            effective_scale = 1.0

        bg_arg: Optional[str] = None
        bg_norm = background_color.strip().lower()
        if bg_norm and bg_norm != "transparent":
            bg_arg = background_color.strip()

        # Render in-memory to PNG via resvg-py
        png_bytes: bytes = resvg_py.svg_to_bytes(
            svg_string=svg_str,
            zoom=effective_scale,
            background=bg_arg,
            skip_system_fonts=False,
        )
        return png_bytes
