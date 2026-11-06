"""
Mermaid diagram converter using Mermaid CLI.
"""
import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from md2docx.external_tools import resolve_external_command
from md2docx.pele_renderer import (
    PELE_RENDERER_VERSION,
    PeleRenderError,
    PeleRenderer,
    is_pele_available,
)


@dataclass(frozen=True)
class MermaidFailure:
    """A diagram that was preserved as source instead of an image."""

    index: int
    error: str


@dataclass
class MermaidReport:
    """Diagram outcomes for one document, in source order."""

    total: int = 0
    failures: List[MermaidFailure] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return self.total - len(self.failures)

    def record_failure(self, exc: Exception) -> None:
        """Keep the underlying CLI error without its lengthy JavaScript stack."""
        while exc.__cause__ is not None:
            exc = exc.__cause__
        detail = str(exc).strip() or type(exc).__name__
        detail = '\n'.join(detail.splitlines()[:4])[:600]
        self.failures.append(MermaidFailure(self.total, detail))


class MermaidConverter:
    """Convert Mermaid diagrams to images via built-in Pele engine or external Mermaid CLI."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        engine: str = "pele",
        command: str = "mmdc",
        output_format: str = "png",
        theme: Optional[str] = None,
        theme_variables: Optional[Dict[str, Any]] = None,
        background_color: str = "white",
        scale: Optional[float] = 1.0,
    ) -> None:
        """
        Initialize the Mermaid converter.

        Args:
            cache_dir: Directory to store cached diagram images
            engine: Rendering engine ("pele" for built-in, "mmdc" for Mermaid CLI)
            command: Mermaid CLI executable name or path (for mmdc engine)
            output_format: Output image format, default is PNG
            theme: Optional Mermaid theme
            theme_variables: Optional Mermaid theme variables passed via config file
            background_color: Mermaid background color
            scale: Optional Mermaid render scale, defaults to 1.0
        """
        self.engine = (engine or "pele").strip().lower()
        self.command = command
        self.output_format = output_format.lower()
        self.theme = theme
        self.theme_variables = dict(theme_variables) if theme_variables else None
        self.background_color = background_color
        self.scale = 1.0 if scale is None else float(scale)

        self._pele_renderer: Optional[PeleRenderer] = None
        if self.engine == "pele" and is_pele_available():
            self._pele_renderer = PeleRenderer()

        if cache_dir is None:
            default_cache = Path.home() / ".md2docx" / "mermaid_cache"
            try:
                default_cache.mkdir(parents=True, exist_ok=True)
                self.cache_dir = default_cache
            except OSError:
                self.cache_dir = Path(tempfile.gettempdir()) / "md2docx_mermaid_cache"
                try:
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                except OSError:
                    pass
        else:
            self.cache_dir = Path(cache_dir)
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    def is_available(self) -> bool:
        """Return whether the selected Mermaid engine is available."""
        if self.engine == "pele":
            return is_pele_available()
        command, _ = self._command_environment()
        return command is not None

    def _command_environment(self) -> Tuple[Optional[str], Dict[str, str]]:
        """Resolve local installs without relying on Finder loading shell profiles."""
        return resolve_external_command(self.command, node_runtime=True)

    def mermaid_to_image(self, code: str) -> bytes:
        """
        Convert Mermaid code to image bytes.

        Args:
            code: Mermaid diagram source

        Returns:
            Rendered image bytes

        Raises:
            RuntimeError: If the selected engine is not available
            ValueError: If rendering fails
        """
        diagram = code.strip()
        if not diagram:
            raise ValueError("Mermaid diagram is empty")

        if not self.is_available():
            if self.engine == "pele":
                raise RuntimeError(
                    "Built-in Pele Mermaid renderer is not available. "
                    "Ensure quickjs-ng and resvg-py are installed."
                )
            raise RuntimeError(
                f"Mermaid CLI command '{self.command}' not found. "
                "Install @mermaid-js/mermaid-cli and ensure 'mmdc' is in PATH."
            )

        cache_key = self._get_cache_key(diagram)
        cached = self._get_cached_image(cache_key)
        if cached is not None:
            return cached

        try:
            img_bytes = self._render_diagram(diagram)
            self._cache_image(cache_key, img_bytes)
            return img_bytes
        except Exception as exc:
            raise ValueError("Failed to render Mermaid diagram") from exc

    def _render_diagram(self, code: str) -> bytes:
        """Render Mermaid code to an image via the selected engine."""
        if self.engine == "pele":
            if self._pele_renderer is None:
                self._pele_renderer = PeleRenderer()

            if self.output_format == "svg":
                svg_str = self._pele_renderer.render_svg(
                    code=code,
                    theme=self.theme or "base",
                    background_color=self.background_color,
                    theme_variables=self.theme_variables,
                )
                return svg_str.encode("utf-8")
            else:
                return self._pele_renderer.render_png(
                    code=code,
                    theme=self.theme or "base",
                    background_color=self.background_color,
                    theme_variables=self.theme_variables,
                    scale=self.scale,
                )

        executable, env = self._command_environment()
        if executable is None:
            raise RuntimeError(f"Mermaid CLI command '{self.command}' not found")
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "diagram.mmd"
            output_path = tmp_path / f"diagram.{self.output_format}"

            input_path.write_text(code, encoding="utf-8")

            command = [
                executable,
                "-i",
                str(input_path),
                "-o",
                str(output_path),
                "-b",
                self.background_color,
            ]

            mermaid_config = self._build_mermaid_config()
            if mermaid_config:
                config_path = tmp_path / "mermaid-config.json"
                config_path.write_text(
                    json.dumps(mermaid_config, ensure_ascii=False, sort_keys=True),
                    encoding="utf-8",
                )
                command.extend(["-c", str(config_path)])
            elif self.theme:
                command.extend(["-t", self.theme])

            if self.scale:
                command.extend(["-s", str(self.scale)])

            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            if result.returncode != 0 or not output_path.exists():
                error_output = (result.stderr or result.stdout or "").strip()
                raise ValueError(error_output or "Mermaid CLI did not produce output")

            return output_path.read_bytes()

    def _build_mermaid_config(self) -> Dict[str, Any]:
        """Build an optional Mermaid config file payload."""
        config: Dict[str, Any] = {}

        if self.theme_variables:
            # Mermaid applies themeVariables reliably only on the base theme.
            config["theme"] = "base"
            config["themeVariables"] = self.theme_variables

        return config

    def _get_cache_key(self, code: str) -> str:
        """Generate a cache key from Mermaid source, engine, and render options."""
        theme_variables_key = (
            json.dumps(self.theme_variables, ensure_ascii=False, sort_keys=True)
            if self.theme_variables
            else ""
        )
        if self.engine == "pele":
            engine_marker = f"pele:{PELE_RENDERER_VERSION}"
        else:
            engine_marker = f"mmdc:{self.command}"

        data = (
            f"{code}:{engine_marker}:{self.output_format}:"
            f"{self.theme}:{theme_variables_key}:{self.background_color}:{self.scale}"
        )
        return hashlib.md5(data.encode("utf-8")).hexdigest()

    def _get_cached_image(self, key: str) -> Optional[bytes]:
        """Get a cached diagram image if present."""
        try:
            cache_file = self.cache_dir / f"{key}.{self.output_format}"
            if cache_file.exists():
                return cache_file.read_bytes()
        except OSError:
            pass
        return None

    def _cache_image(self, key: str, img_bytes: bytes) -> None:
        """Persist a rendered diagram image in the cache."""
        try:
            cache_file = self.cache_dir / f"{key}.{self.output_format}"
            cache_file.write_bytes(img_bytes)
        except OSError:
            pass

    def clear_cache(self) -> None:
        """Clear all cached Mermaid diagrams."""
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob(f"*.{self.output_format}"):
                cache_file.unlink()
