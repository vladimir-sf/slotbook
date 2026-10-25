#!/usr/bin/env bash
# Lead-owned API v1 gate. Requires npm ci in contracts/ and frontend/ (Node 22).
# Usage: bash scripts/check-contract.sh [--self-test]
# Generation and type fixtures live only in a private temporary directory.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec node "$script_dir/check-contract.mjs" "$@"
