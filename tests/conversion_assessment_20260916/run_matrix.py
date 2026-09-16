"""Run archived source trees against identical inputs and installed dependencies."""
import json
import os
from pathlib import Path
import subprocess
import sys

folder = Path(__file__).resolve().parent
root = folder.parents[1]
cases = [(ref, mode) for ref in ['cd04fc8', 'd14566d', '446fd59', '80fd050', '1eeb7e7', '022ef8b', 'current']
         for mode in (['plain'] if ref in ['cd04fc8', 'd14566d', '446fd59'] else ['plain', 'template'])]
rows = []
for ref, mode in cases:
    source = root if ref == 'current' else folder / 'versions' / ref
    command = [sys.executable, str(folder / 'probe.py'), str(source), ref, mode]
    run = subprocess.run(command, text=True, capture_output=True)
    (folder / f'{ref}-{mode}.log').write_text(run.stdout + '\n' + run.stderr)
    result_path = folder / f'{ref}-{mode}' / 'result.json'
    if result_path.exists():
        result = json.loads(result_path.read_text())
        rows.append(result)
        print(ref, mode, {name: {'pass': value['pass'], 'drawings': value.get('drawings'), 'equations': value.get('equations'), 'error': value.get('error'), 'pictures': value.get('pictures')} for name, value in result['cases'].items()}, flush=True)
    else:
        print(ref, mode, 'PROBE FAILED', run.returncode, run.stderr[-1000:], flush=True)
(folder / 'matrix.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
