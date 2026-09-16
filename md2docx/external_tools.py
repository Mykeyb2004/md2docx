"""Resolve external tools for both terminal and macOS desktop launches."""
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple


def resolve_external_command(command: str, node_runtime: bool = False) -> Tuple[Optional[str], Dict[str, str]]:
    """Build a child environment without executing shell profiles or changing PATH globally."""
    env = os.environ.copy()
    search_path = env.get('PATH', os.defpath)
    if sys.platform == 'darwin':
        home = Path.home()
        extra_paths = [str(home / '.local' / 'bin'), '/opt/homebrew/bin', '/usr/local/bin']
        if node_runtime:
            nvm_dir = Path(env.get('NVM_DIR') or home / '.nvm').expanduser()
            versions = sorted(
                (nvm_dir / 'versions' / 'node').glob('v*/bin'),
                key=lambda path: tuple(int(part) for part in re.findall(r'\d+', path.parent.name)),
                reverse=True,
            )
            extra_paths = [env.get('NVM_BIN', ''), *extra_paths, str(home / '.volta' / 'bin')]
            extra_paths.extend(str(path) for path in versions)
        search_path = os.pathsep.join(path for path in [search_path, *extra_paths] if path)
    resolved = shutil.which(os.path.expanduser(command), path=search_path)
    if resolved:
        # mmdc uses /usr/bin/env node; select the runtime beside that executable.
        search_path = os.pathsep.join([str(Path(resolved).absolute().parent), search_path])
    env['PATH'] = search_path
    return resolved, env
