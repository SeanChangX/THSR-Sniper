#!/usr/bin/env bash
# Interactive captcha labeling script
# - Traverses image files in current directory
# - Shows each image
# - Prompts for label; renames to "<label>__labeled__.<ext>"
# - Skips already labeled files
# - Logs mapping to labels.csv

set -Eeuo pipefail
shopt -s nullglob

MARK="__labeled__"
LOGFILE="labels.csv"
exts=(jpg jpeg png gif bmp webp tif tiff)

lower() { printf '%s' "${1,,}"; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

show_image() {
  local f="$1"
  if has_cmd imgcat; then imgcat "$f" || true
  elif has_cmd viu; then viu "$f" || true
  elif has_cmd display; then display "$f" &
  elif has_cmd xdg-open; then xdg-open "$f" >/dev/null 2>&1 || true
  elif has_cmd open; then open "$f" >/dev/null 2>&1 || true
  else
    echo "[Info] No image viewer found. Please open manually: $f"
  fi
}

sanitize_label() {
  local s="$1"
  s="${s// /_}"
  s="${s//\//-}"
  s="${s#.}"
  s="${s%.}"
  printf '%s' "$s"
}

unique_name() {
  local base="$1" ext="$2" candidate
  candidate="${base}${MARK}.${ext}"
  local i=1
  while [[ -e "$candidate" ]]; do
    candidate="${base}${MARK}_${i}.${ext}"
    ((i++))
  done
  printf '%s' "$candidate"
}

# Initialize log file
if [[ ! -e "$LOGFILE" ]]; then
  echo "original_filename,new_filename" > "$LOGFILE"
fi

# Collect image files
files=()
for e in "${exts[@]}"; do
  for f in *."$e" *."${e^^}"; do
    [[ -e "$f" ]] || continue
    files+=("$f")
  done
done

if ((${#files[@]}==0)); then
  echo "No image files found. Supported extensions: ${exts[*]}"
  exit 0
fi

echo "Found ${#files[@]} images. Start labeling."
echo "Instructions: type label then Enter; press Enter to skip; type q to quit."

for f in "${files[@]}"; do
  if [[ "$f" == *"$MARK"* ]]; then
    echo "Skip (already labeled): $f"
    continue
  fi

  echo "----------------------------------------"
  echo "File: $f"
  show_image "$f"

  read -rp "Enter label (q=quit, empty=skip): " label_raw || true

  if [[ "$label_raw" == "q" || "$label_raw" == "Q" ]]; then
    echo "User quit."
    exit 0
  fi

  if [[ -z "${label_raw}" ]]; then
    echo "Skipped: $f"
    continue
  fi

  label="$(sanitize_label "$label_raw")"
  if [[ -z "$label" ]]; then
    echo "Invalid label, skipped: $f"
    continue
  fi

  ext="$(lower "${f##*.}")"
  target="$(unique_name "$label" "$ext")"

  mv -- "$f" "$target"
  echo "\"$f\",\"$target\"" >> "$LOGFILE"
  echo "Renamed to: $target"
done

echo "Done. Mapping saved to $LOGFILE"
