"""
POC: Test matplotlib LaTeX rendering capabilities.
This file will be deleted after verification.
"""
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
from io import BytesIO
from pathlib import Path

def test_latex_rendering():
    """Test basic LaTeX rendering with matplotlib."""
    
    # Test formulas (basic + advanced)
    test_formulas = [
        # Basic
        (r'E=mc^2', 'basic_einstein.png'),
        (r'x^2 + y^2 = r^2', 'basic_circle.png'),
        (r'\frac{a}{b}', 'basic_fraction.png'),
        (r'\sqrt{x}', 'basic_sqrt.png'),
        
        # Advanced
        (r'\sum_{i=1}^{n} x_i', 'advanced_sum.png'),
        (r'\int_0^1 x^2 dx', 'advanced_integral.png'),
        (r'\frac{-b \pm \sqrt{b^2-4ac}}{2a}', 'advanced_quadratic.png'),
        (r'\begin{pmatrix} a & b \\ c & d \end{pmatrix}', 'advanced_matrix.png'),
    ]
    
    output_dir = Path(__file__).parent / 'poc_output'
    output_dir.mkdir(exist_ok=True)
    
    print("Testing matplotlib LaTeX rendering...\n")
    
    for latex, filename in test_formulas:
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(6, 1))
            ax.axis('off')
            
            # Render LaTeX
            ax.text(0.5, 0.5, f'${latex}$', 
                   fontsize=20, ha='center', va='center')
            
            # Save with high DPI
            output_path = output_dir / filename
            fig.savefig(output_path, dpi=300, bbox_inches='tight', 
                       pad_inches=0.1, transparent=False, facecolor='white')
            plt.close(fig)
            
            # Check file size
            size_kb = output_path.stat().st_size / 1024
            
            print(f"✓ {latex:40s} → {filename:25s} ({size_kb:.1f} KB)")
            
        except Exception as e:
            print(f"✗ {latex:40s} → ERROR: {e}")
    
    print(f"\nOutput directory: {output_dir}")
    print("Please review the generated images for quality.")

def test_inline_vs_block():
    """Test inline vs block formula rendering."""
    
    output_dir = Path(__file__).parent / 'poc_output'
    output_dir.mkdir(exist_ok=True)
    
    latex = r'\frac{a}{b}'
    
    print("\nTesting inline vs block rendering...\n")
    
    # Inline (smaller)
    fig, ax = plt.subplots(figsize=(1, 0.3))
    ax.axis('off')
    ax.text(0.5, 0.5, f'${latex}$', fontsize=12, ha='center', va='center')
    fig.savefig(output_dir / 'inline_formula.png', dpi=300, 
               bbox_inches='tight', pad_inches=0.05, transparent=True)
    plt.close(fig)
    print("✓ Inline formula saved")
    
    # Block (larger)
    fig, ax = plt.subplots(figsize=(2, 0.5))
    ax.axis('off')
    ax.text(0.5, 0.5, f'${latex}$', fontsize=16, ha='center', va='center')
    fig.savefig(output_dir / 'block_formula.png', dpi=300, 
               bbox_inches='tight', pad_inches=0.1, transparent=True)
    plt.close(fig)
    print("✓ Block formula saved")

if __name__ == '__main__':
    print("=" * 70)
    print("LaTeX Rendering POC - matplotlib")
    print("=" * 70)
    
    test_latex_rendering()
    test_inline_vs_block()
    
    print("\n" + "=" * 70)
    print("POC Complete!")
    print("=" * 70)
