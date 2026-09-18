#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python -m pytest -c test/pytest.ini test \
  --cov=d4sign \
  --cov=main \
  --cov-branch \
  --cov-report=term-missing \
  --cov-fail-under=100 \
  "$@"
