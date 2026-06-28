"""Test configuration for collector tests.

Ensures all project packages are importable when running tests
outside the installed editable package.
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent  # apps/collector/
_liquidity_root = _project_root.parent.parent          # liquidity-os/

# Packages root — shared/, meteora/, database/ live here
_packages_root = _liquidity_root / "packages"
# decision_log is a flat package inside packages/
_decision_log = _liquidity_root / "packages" / "decision_log"

for p in [_packages_root, _decision_log, _project_root]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
