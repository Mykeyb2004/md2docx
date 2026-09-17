"""
Style management module.
"""
import copy
import sys
from typing import Dict, Optional, Any
import yaml
import pkgutil
from pathlib import Path


class StyleManager:
    """Manage Word document styles from YAML configuration."""
    
    # Default configuration fallback
    DEFAULT_CONFIG: Dict[str, Any] = {
        "document": {
            "page_size": "A4",
            "line_spacing": 1.5,
            "ignore_thematic_breaks": True,
            "auto_fix_tables": False,
            "section_index": False,
        },
        "heading1": {
            "font_name": "微软雅黑",
            "font_size": "18pt",
            "bold": True
        },
        "heading2": {
            "font_name": "微软雅黑",
            "font_size": "16pt",
            "bold": True
        },
        "heading3": {
            "font_name": "微软雅黑",
            "font_size": "14pt",
            "bold": True
        },
        "heading4": {
            "font_name": "微软雅黑",
            "font_size": "12pt",
            "bold": True
        },
        "paragraph": {
            "font_name": "宋体",
            "font_size": "12pt",
            "line_spacing": 1.5
        },
        "table": {
            "layout": "accent_grid",
            "style": "Light Grid Accent 1",
            "font_size": "11pt",
            "alignment": "left",
            "vertical_alignment": "center",
            "cell_margin_vertical": "3pt",
            "cell_margin_horizontal": "5.4pt",
            "header_alignment": "center",
            "header_vertical_alignment": "center",
            "column_width_strategy": "content-weighted",
        },
        "list": {
            "bullet_char": "•",
            "number_format": "1.",
            "indent_size": "0.5in",
            "ordered_list_as_text": False,
        },
        "mermaid": {
            "command": "mmdc",
            "format": "png",
            "theme": "default",
            "width": "5.5in",
            "alignment": "center",
            "space_before": "6pt",
            "space_after": "6pt",
            "background_color": "white",
            "soft_max_height_ratio": 0.68,
            "hard_max_height_ratio": 0.82,
            "page_max_height_ratio": 0.92,
            "page_break_threshold_ratio": 0.9,
            "min_readable_width": "3.2in",
            "oversized_strategy": "page",
            "force_page_break_before_oversized": False,
            "keep_with_previous": True,
            "keep_with_previous_max_chars": 80,
            "follow_previous_trigger_height_ratio": 0.24,
            "follow_previous_width_ratio": 0.55,
            "follow_previous_space_before": "0pt",
            "keep_together": True,
            "keep_with_next": False,
            "widow_control": False,
        },
        "chapter_scan": {
            "target_dir": "output",
            "glob": "*.md",
            "recursive": True,
        },
    }
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize style manager.
        
        Args:
            config_path: Path to YAML configuration file or template name
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
        if config_path:
            self.config = self.load_config(config_path)
        else:
            # Load default template
            self.config = self._load_default_template()

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "StyleManager":
        """Create a manager from an isolated in-memory configuration."""
        manager = cls.__new__(cls)
        manager.config_path = None
        manager.config = copy.deepcopy(config)
        return manager

    @staticmethod
    def _get_runtime_dir() -> Path:
        """Return the directory users are expected to place editable config files in."""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path.cwd()

    @classmethod
    def _get_external_template_path(cls, template_name: str) -> Path:
        """Return the editable template path beside the packaged app."""
        return cls._get_runtime_dir() / f"{template_name}.yaml"

    @classmethod
    def get_editable_template_path(cls, template_name: str = "default") -> Path:
        """Return the editable on-disk path for a template."""
        return cls._get_external_template_path(template_name)

    @staticmethod
    def _load_packaged_template(template_name: str) -> Dict[str, Any]:
        """Load a bundled template shipped with the package."""
        raw_data = pkgutil.get_data("md2docx", f"templates/{template_name}.yaml")
        if raw_data is None:
            raise FileNotFoundError(f"Template '{template_name}' not found")

        config = yaml.safe_load(raw_data.decode("utf-8")) or {}
        if not isinstance(config, dict):
            raise ValueError(f"Invalid configuration format in packaged template: {template_name}")
        return config

    @classmethod
    def load_packaged_template(cls, template_name: str = "default") -> Dict[str, Any]:
        """Load a bundled template configuration."""
        return cls._load_packaged_template(template_name)
    
    def _load_default_template(self) -> Dict[str, Any]:
        """Load default template configuration."""
        external_template_path = self._get_external_template_path("default")

        if external_template_path.exists():
            with open(external_template_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}

        try:
            return self._load_packaged_template("default")
        except (FileNotFoundError, ValueError):
            pass

        # Fallback to hardcoded defaults
        return copy.deepcopy(self.DEFAULT_CONFIG)
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file or template name
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If configuration file not found
            yaml.YAMLError: If YAML parsing fails
        """
        # Check if it's a template name (without path separators)
        if '/' not in config_path and '\\' not in config_path and not config_path.endswith('.yaml'):
            template_path = self._get_external_template_path(config_path)
            if template_path.exists():
                config_path = str(template_path)
            else:
                return self._load_packaged_template(config_path)
        
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        if not isinstance(config, dict):
            raise ValueError(f"Invalid configuration format in {config_path}")
        
        return config
    
    def get_heading_style(self, level: int) -> Dict[str, Any]:
        """
        Get heading style configuration for specified level.
        
        Args:
            level: Heading level (1-4)
            
        Returns:
            Style configuration dictionary
        """
        if level < 1 or level > 4:
            raise ValueError(f"Invalid heading level: {level}. Must be 1-4.")
        
        key = f"heading{level}"
        return self.config.get(key, self.DEFAULT_CONFIG.get(key, {}))
    
    def get_paragraph_style(self) -> Dict[str, Any]:
        """
        Get paragraph style configuration.
        
        Returns:
            Style configuration dictionary
        """
        return self.config.get("paragraph", self.DEFAULT_CONFIG.get("paragraph", {}))
    
    def get_table_style(self) -> Dict[str, Any]:
        """
        Get table style configuration.
        
        Returns:
            Style configuration dictionary
        """
        return self.config.get("table", self.DEFAULT_CONFIG.get("table", {}))
    
    def get_list_style(self) -> Dict[str, Any]:
        """
        Get list style configuration.
        
        Returns:
            Style configuration dictionary
        """
        return self.config.get("list", self.DEFAULT_CONFIG.get("list", {}))
    
    def get_document_style(self) -> Dict[str, Any]:
        """
        Get document-level style configuration.
        
        Returns:
            Style configuration dictionary
        """
        return self.config.get("document", self.DEFAULT_CONFIG.get("document", {}))
    
    def get_inline_style(self, style_type: str = None) -> Dict[str, Any]:
        """
        Get inline text formatting style configuration.
        
        Args:
            style_type: Type of inline style ('bold', 'italic', 'code'), or None for all
            
        Returns:
            Style configuration dictionary
        """
        inline_config = self.config.get("inline", {})
        
        if style_type:
            return inline_config.get(style_type, {})
        
        return inline_config
    
    def get_code_block_style(self) -> Dict[str, Any]:
        """
        Get code block style configuration.
        
        Returns:
            Style configuration dictionary
        """
        return self.config.get("code_block", self.DEFAULT_CONFIG.get("code_block", {}))

    def get_mermaid_style(self) -> Dict[str, Any]:
        """
        Get Mermaid diagram style configuration.

        Returns:
            Style configuration dictionary
        """
        return self.config.get("mermaid", self.DEFAULT_CONFIG.get("mermaid", {}))

    def get_style(self, style_name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get an arbitrary style section by name.

        Args:
            style_name: Style section key
            default: Optional fallback when neither config nor defaults contain it

        Returns:
            Style configuration dictionary
        """
        if style_name in self.config:
            return self.config[style_name]
        if style_name in self.DEFAULT_CONFIG:
            return self.DEFAULT_CONFIG[style_name]
        return default or {}
