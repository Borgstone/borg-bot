#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/logs /app/state
exec python -m borgbot.app.paper_runner
