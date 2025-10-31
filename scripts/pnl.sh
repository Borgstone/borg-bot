#!/usr/bin/env bash
set -euo pipefail

# Map service -> db file
declare -A DBS=(
  [borg-btc-1m]=btcusdt_1m.db
  [borg-btc-1h]=btcusdt_1h.db
  [borg-eth-1m]=ethusdt_1m.db
  [borg-eth-1h]=ethusdt_1h.db
)

for svc in borg-btc-1m borg-btc-1h borg-eth-1m borg-eth-1h; do
  db="${DBS[$svc]}"
  # latest price from logs (fallback to full log if last 15m sparse)
  price="$(docker logs --since=15m "$svc" 2>/dev/null \
            | awk -F'"price": ' '/"price":[ ]*[0-9]/{p=$2} END{print p}' \
            | awk -F'[ ,}]' '{print $1}')"
  if [ -z "${price:-}" ]; then
    price="$(docker logs "$svc" 2>/dev/null \
              | awk -F'"price": ' '/"price":[ ]*[0-9]/{p=$2} END{print p}' \
              | awk -F'[ ,}]' '{print $1}')"
  fi

  # read starting cash (if present) else default 1000
  start_cash="$(docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
    "apk add --no-cache sqlite >/dev/null; sqlite3 -readonly /state/$db \"SELECT value FROM kv WHERE key='starting_cash' LIMIT 1;\"" \
    || true)"
  if [ -z "${start_cash:-}" ]; then start_cash=1000; fi

  # last trade state (cash/base/avg_price)
  read -r cash base avg ts <<< "$(
    docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
      "apk add --no-cache sqlite >/dev/null; sqlite3 -readonly /state/$db \
       \"SELECT cash_after, base_after, COALESCE(avg_price,0), ts FROM trades ORDER BY ts DESC LIMIT 1;\""
  )" || true

  cash=${cash:-$start_cash}
  base=${base:-0}
  price=${price:-0}

  equity=$(awk -v c="$cash" -v b="$base" -v p="$price" 'BEGIN{printf "%.2f", c + b*p}')
  pnl=$(awk -v e="$equity" -v s="$start_cash" 'BEGIN{printf "%.2f", e - s}')
  roi=$(awk -v p="$pnl" -v s="$start_cash" 'BEGIN{printf "%.2f", (p/s)*100}')

  printf "%-12s | price=%-12s cash=%-10s base=%-12s equity=%-10s PnL=%-10s (%s%%)\n" \
    "$svc" "$price" "$cash" "$base" "$equity" "$pnl" "$roi"
done
