#!/usr/bin/env bash
set -euo pipefail
(
 cd contracts
 npm run build
)
(
 cd frontend
 npm run generate:api
 npm run build
)
(
 cd backend
 python -m pytest -q
)
echo "Scaffold checks passed. Booking/E2E checks must be added by agents."
