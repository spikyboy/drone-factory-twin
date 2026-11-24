#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Launch the Swarmy Factory Twin in a local Omniverse Kit runtime (Linux).
# Set KIT_PATH to your ./kit binary (Kit SDK) or omni.create.sh (USD Composer).
# ---------------------------------------------------------------------------
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_PATH="${KIT_PATH:-$HOME/.local/share/ov/pkg/kit/kit}"
APP="$HERE/apps/swarmy.twin.kit"
echo "Launching twin with $KIT_PATH"
"$KIT_PATH" "$APP" --ext-folder "$HERE/source/extensions"
