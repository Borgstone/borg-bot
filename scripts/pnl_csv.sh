#!/usr/bin/env bash
set -euo pipefail

# Where to write the CSV (override with CSV_PATH env if you want)
CSV_PATH="${CSV_PATH:-/home/borg/pnl.csv}"

# Map service -> db file
declare -A DBS=(
  [borg-btc-1m]=btcusdt_1m.db
  [borg-btc-1h]=btcusdt_1h.db
  [borg-eth-1m]=ethusdt_1m.db
  [borg-eth-1h]=ethusdt_1h.db
)

timestamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Latest price from logs (window param), fallback to DB last trade price
latest_price() {
  local svc="$1" db="$2" win="${3:-180m}"
  # try recent logs (most recent "price": <num>)
  local p
  p="$(docker logs --since="$win" "$svc" 2>/dev/null \
        | grep -o '"price":[ ]*[0-9.]\+' \
        | tail -n1 | awk -F: '{gsub(/ /,"",$2); print $2}' || true)"
  if [ -z "${p:-}" ]; then
    # fallback: last trade price in DB
    p="$(docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
          "apk add --no-cache sqlite >/dev/null 2>&1; \
           [ -f /state/$db ] && sqlite3 -readonly /state/$db \
           'SELECT price FROM trades ORDER BY ts DESC LIMIT 1;'" 2>/dev/null || true)"
  fi
  echo "${p:-0}"
}

# Starting cash from init.cash logs (fallback 1000)
starting_cash() {
  local svc="$1" win="${2:-365d}"
  local sc
  sc="$(docker logs --since="$win" "$svc" 2>/dev/null \
        | awk '/"event": "init\.cash"/ { if (match($0, /"starting_cash":[ ]*([0-9.]+)/, m)) v=m[1] } END{ if (v!="") print v }' || true)"
  echo "${sc:-1000}"
}

# Last state (cash_after, base_after) from DB (fallback: start_cash, 0)
last_state() {
  local db="$1" start_cash="$2"
  local tmp cash base
  tmp="$(mktemp)"; trap 'rm -f "$tmp"' RETURN
  docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
    "apk add --no-cache sqlite >/dev/null 2>&1; \
     [ -f /state/$db ] && sqlite3 -readonly /state/$db \
     'SELECT cash_after, base_after FROM trades ORDER BY ts DESC LIMIT 1;'" \
     >"$tmp" 2>/dev/null || true
  read -r cash base < "$tmp" || true
  echo "${cash:-$start_cash} ${base:-0}"
}

# Ensure CSV has header
mkdir -p "$(dirname "$CSV_PATH")"
if [ ! -f "$CSV_PATH" ]; then
  echo "timestamp,service,price,cash,base,equity,pnl,roi" > "$CSV_PATH"
fi

ts="$(timestamp)"

for svc in borg-btc-1m borg-btc-1h borg-eth-1m borg-eth-1h; do
  db="${DBS[$svc]}"
  # Choose log window: tighter for 1m, looser for 1h
  case "$svc" in
    *-1m) win="180m" ;;  # 3h
    *-1h) win="24h"  ;;  # 24h
    *)    win="6h"   ;;
  esac

  price="$(latest_price "$svc" "$db" "$win")"
  sc="$(starting_cash "$svc" "365d")"
  read -r cash base <<<"$(last_state "$db" "$sc")"

  # Compute equity/pnl/roi safely
  equity=$(awk -v c="$cash" -v b="$base" -v p="$price" 'BEGIN{ printf "%.2f", (c + b*p) }')
  pnl=$(awk -v e="$equity" -v s="$sc" 'BEGIN{ printf "%.2f", (e - s) }')
  roi=$(awk -v p="$pnl" -v s="$sc" 'BEGIN{ if (s==0) printf "0.00"; else printf "%.2f", (p/s)*100 }')

  # Normalize numbers for CSV
  p_fmt=$(awk -v x="$price" 'BEGIN{ printf "%.2f", x }')
  c_fmt=$(awk -v x="$cash"  'BEGIN{ printf "%.2f", x }')
  b_fmt=$(awk -v x="$base"  'BEGIN{ printf "%.8f", x }')

  echo "$ts,$svc,$p_fmt,$c_fmt,$b_fmt,$equity,$pnl,$roi" >> "$CSV_PATH"
done
