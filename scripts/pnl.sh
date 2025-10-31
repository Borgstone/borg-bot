#!/usr/bin/env bash
set -euo pipefail

# Map service -> db file
declare -A DBS=(
  [borg-btc-1m]=btcusdt_1m.db
  [borg-btc-1h]=btcusdt_1h.db
  [borg-eth-1m]=ethusdt_1m.db
  [borg-eth-1h]=ethusdt_1h.db
)

# Helper: get the latest numeric field value from logs (e.g., price)
latest_number_from_logs() {
  local svc="$1" field="$2" since="${3:-60m}"
  docker logs --since="$since" "$svc" 2>/dev/null \
    | awk -v f="\"$field\": " '
        $0 ~ f {
          split($0, a, f)
          if (length(a) > 1) {
            # grab the token after the field
            g=a[2]
            # trim at comma, space or }
            sub(/[ ,}].*/, "", g)
            val=g
          }
        }
        END { if (val!="") print val }
      '
}

# Helper: get starting_cash from the init.cash event in logs
starting_cash_from_logs() {
  local svc="$1" since="${2:-365d}"  # wide window so we always find it
  docker logs --since="$since" "$svc" 2>/dev/null \
    | awk '
        /"event": "init\.cash"/ {
          if (match($0, /"starting_cash":[ ]*([0-9.]+)/, m)) sc=m[1]
        }
        END { if (sc!="") print sc }
      '
}

for svc in borg-btc-1m borg-btc-1h borg-eth-1m borg-eth-1h; do
  db="${DBS[$svc]}"

  # 1) Price (try recent logs, then full)
  price="$(latest_number_from_logs "$svc" price 60m)"
  if [ -z "${price:-}" ]; then
    price="$(latest_number_from_logs "$svc" price 365d)"
  fi

  # 2) starting_cash from logs (fallback 1000)
  start_cash="$(starting_cash_from_logs "$svc" 365d)"
  if [ -z "${start_cash:-}" ]; then start_cash=1000; fi

  # 3) last trade state (cash_after, base_after) from DB
  cash=""
  base=""

  # If DB exists and has trades, pull last row
  if docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
       "apk add --no-cache sqlite >/dev/null 2>&1; [ -f /state/$db ] && sqlite3 -readonly /state/$db \
        \"SELECT cash_after, base_after FROM trades ORDER BY ts DESC LIMIT 1;\" 2>/dev/null" \
        >/tmp/.pnl_last 2>/dev/null; then
    read -r cash base < /tmp/.pnl_last || true
  fi

  # If no trades yet or query returned nothing, assume initial state
  cash=${cash:-$start_cash}
  base=${base:-0}

  # 4) Compute equity / PnL
  # If price missing (shouldn’t), treat as 0 to avoid awk errors
  price=${price:-0}

  equity=$(awk -v c="$cash" -v b="$base" -v p="$price" 'BEGIN{printf "%.2f", c + b*p}')
  pnl=$(awk -v e="$equity" -v s="$start_cash" 'BEGIN{printf "%.2f", e - s}')
  roi=$(awk -v p="$pnl" -v s="$start_cash" 'BEGIN{
      if (s==0) { printf "0.00" } else { printf "%.2f", (p/s)*100 }
    }')

  printf "%-12s | price=%-12s cash=%-10s base=%-12s equity=%-10s PnL=%-10s (%s%%)\n" \
    "$svc" "$price" "$cash" "$base" "$equity" "$pnl" "$roi"
done
