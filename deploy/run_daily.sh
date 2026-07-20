#!/usr/bin/env bash
# daily NSE collection wrapper for cron/systemd. edit paths for your box.
set -euo pipefail

PROJECT_DIR="/opt/nse-market-collector"      # <-- change me
VENV_PY="${PROJECT_DIR}/.venv/bin/python"    # or system python3

cd "$PROJECT_DIR"
export NSE_POLITE_DELAY="${NSE_POLITE_DELAY:-2.5}"

# full daily job: all snapshots + that day's per_date + date_range
exec "$VENV_PY" -m nse_collector "$@"
