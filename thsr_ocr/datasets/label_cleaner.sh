#!/bin/bash

set -euo pipefail

usage() {
  echo "Usage: $(basename "$0") [--apply] [--dry-run] [PATH]"
  echo "Default is dry-run. PATH defaults to current directory."
}

apply=false
path="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) apply=true; shift ;;
    -n|--dry-run) apply=false; shift ;;
    -h|--help) usage; exit 0 ;;
    *) path="$1"; shift ;;
  esac
done

[[ -d "$path" ]] || { echo "Not a directory: $path" >&2; exit 1; }

# Collect strictly matching files, sorted (null-safe)
mapfile -d '' files < <(
  find "$path" -maxdepth 1 -type f -regextype posix-extended \
    -regex '.*/[A-Za-z0-9]+_[0-9]{3}\.jpg' -print0 | sort -z
)

[[ ${#files[@]} -gt 0 ]] || { echo "No matching files in: $path"; exit 0; }

for f0 in "${files[@]}"; do
  f="${f0%$'\0'}";                 # trim NUL (mapfile quirk)
  dir=$(dirname -- "$f")
  base=$(basename -- "$f")

  # Extract prefix
  [[ "$base" =~ ^([A-Za-z0-9]+)_[0-9]{3}\.jpg$ ]] || continue
  prefix="${BASH_REMATCH[1]}"
  
  tgt="${dir}/${prefix}.jpg"

  if [[ "$f" == "$tgt" ]]; then
    echo "Skip (already named): $f"
  else
    if $apply; then
      echo "Renaming $f -> $tgt"
      mv -i -- "$f" "$tgt"
    else
      echo "[DRY-RUN] $f -> $tgt"
    fi
  fi
done
