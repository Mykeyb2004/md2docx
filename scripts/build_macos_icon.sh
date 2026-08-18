#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_PNG="${REPO_ROOT}/assets/macos/AppIcon.png"
OUTPUT_ICNS="${REPO_ROOT}/assets/macos/AppIcon.icns"

die() {
  printf 'build_macos_icon: %s\n' "$1" >&2
  exit 1
}

command -v sips >/dev/null 2>&1 || die "sips is required on macOS"
command -v iconutil >/dev/null 2>&1 || die "iconutil is required on macOS"
[[ -f "$SOURCE_PNG" ]] || die "missing source PNG: $SOURCE_PNG"

read -r width height < <(
  sips -g pixelWidth -g pixelHeight "$SOURCE_PNG" |
    awk '/pixelWidth:/{width=$2} /pixelHeight:/{height=$2} END {print width, height}'
)
[[ "$width" == "1024" && "$height" == "1024" ]] ||
  die "source PNG must be 1024x1024 (got ${width}x${height})"

TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/md2docx-icon.XXXXXX")"
cleanup() {
  rm -rf "$TEMP_ROOT"
}
trap cleanup EXIT

ICONSET="${TEMP_ROOT}/AppIcon.iconset"
mkdir -p "$ICONSET"

for spec in \
  "16x16:16" "16x16@2x:32" \
  "32x32:32" "32x32@2x:64" \
  "128x128:128" "128x128@2x:256" \
  "256x256:256" "256x256@2x:512" \
  "512x512:512" "512x512@2x:1024"; do
  name="${spec%%:*}"
  size="${spec##*:}"
  sips -z "$size" "$size" "$SOURCE_PNG" \
    --out "${ICONSET}/icon_${name}.png" >/dev/null
done

CANDIDATE="${TEMP_ROOT}/AppIcon.icns"
iconutil --convert icns --output "$CANDIDATE" "$ICONSET"
[[ -s "$CANDIDATE" ]] || die "iconutil did not create a non-empty .icns"
mv "$CANDIDATE" "$OUTPUT_ICNS"
printf 'Generated %s\n' "$OUTPUT_ICNS"
