#!/usr/bin/env bash
# Regenerate the USD twin + validate + preview (no GPU required).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m pip install -r "$HERE/requirements.txt" --quiet
python3 "$HERE/tools/generate_factory.py"
python3 "$HERE/scripts/validate.py"
python3 "$HERE/scripts/preview_floorplan.py"
python3 "$HERE/scripts/preview_iso.py"
echo "Twin regenerated at $HERE/usd/DroneFactory.usd"
