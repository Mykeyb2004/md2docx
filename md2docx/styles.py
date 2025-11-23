"""
Style management module.
"""
from typing import Dict, Optional, Any
import yaml
from pathlib import Path


class StyleManager:
    """Manage Word document styles from YAML configuration."""
    
    # Default configuration fallback
    DEFAULT_CONFIG: Dict[str, Any] = {
        "document": {
            "page_size": "A4",
            "line_spacing": 1.5
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
            "style": "Light Grid Accent 1",
            "font_size": "11pt"
        },
        "list": {
            "bullet_char": "•",
            "number_format": "1.",
            "indent_size": "0.5in"
        }
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
    
    def _load_default_template(self) -> Dict[str, Any]:
        """Load default template configuration."""
        default_template_path = Path(__file__).parent / "templates" / "default.yaml"
        
        if default_template_path.exists():
            with open(default_template_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        
        # Fallback to hardcoded defaults
        return self.DEFAULT_CONFIG.copy()
    
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
            # It's a template name
            template_path = Path(__file__).parent / "templates" / f"{config_path}.yaml"
            if template_path.exists():
                config_path = str(template_path)
            else:
                raise FileNotFoundError(f"Template '{config_path}' not found")
        
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
