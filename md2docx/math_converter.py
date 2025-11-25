"""
Math formula converter using matplotlib.

Converts LaTeX mathematical expressions to PNG images for embedding in Word documents.
"""
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
from pathlib import Path
import hashlib
from typing import Optional


class MathConverter:
    """Convert LaTeX formulas to PNG images."""
    
    def __init__(self, cache_dir: Optional[Path] = None, dpi: int = 300):
        """
        Initialize the math converter.
        
        Args:
            cache_dir: Directory to store cached formula images
            dpi: Resolution for rendered images (default: 300)
        """
        self.dpi = dpi
        if cache_dir is None:
            cache_dir = Path.home() / '.md2docx' / 'math_cache'
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def latex_to_image(self, latex: str, inline: bool = False) -> bytes:
        """
        Convert LaTeX formula to PNG image bytes.
        
        Args:
            latex: LaTeX formula string (without $ delimiters)
            inline: True for inline formulas (smaller), False for block formulas
            
        Returns:
            PNG image bytes
            
        Raises:
            ValueError: If LaTeX rendering fails
        """
        # Check cache first
        cache_key = self._get_cache_key(latex, inline)
        cached = self._get_cached_image(cache_key)
        if cached:
            return cached
        
        try:
            # Render with matplotlib
            img_bytes = self._render_formula(latex, inline)
            
            # Cache the result
            self._cache_image(cache_key, img_bytes)
            
            return img_bytes
            
        except Exception as e:
            raise ValueError(f"Failed to render LaTeX formula: {latex}") from e
    
    def _render_formula(self, latex: str, inline: bool) -> bytes:
        """Render LaTeX formula using matplotlib."""
        import io
        
        # Configure figure size and font size based on inline/block
        if inline:
            figsize = (0.1, 0.1)
            fontsize = 12
            pad = 0.05
        else:
            figsize = (0.1, 0.1)
            fontsize = 16
            pad = 0.1
        
        # Create figure
        fig, ax = plt.subplots(figsize=figsize)
        ax.axis('off')
        
        # Add LaTeX text
        ax.text(0.5, 0.5, f'${latex}$',
               fontsize=fontsize,
               ha='center',
               va='center')
        
        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf,
                   format='png',
                   dpi=self.dpi,
                   bbox_inches='tight',
                   pad_inches=pad,
                   transparent=True)
        plt.close(fig)
        
        buf.seek(0)
        return buf.read()
    
    def _get_cache_key(self, latex: str, inline: bool) -> str:
        """Generate cache key from LaTeX string and parameters."""
        data = f"{latex}:{inline}:{self.dpi}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _get_cached_image(self, key: str) -> Optional[bytes]:
        """Get cached image if exists."""
        cache_file = self.cache_dir / f"{key}.png"
        if cache_file.exists():
            return cache_file.read_bytes()
        return None
    
    def _cache_image(self, key: str, img_bytes: bytes):
        """Cache rendered image."""
        cache_file = self.cache_dir / f"{key}.png"
        cache_file.write_bytes(img_bytes)
    
    def clear_cache(self):
        """Clear all cached formula images."""
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.png"):
                cache_file.unlink()
