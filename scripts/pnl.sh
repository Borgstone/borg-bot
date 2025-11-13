#!/usr/bin/env bash
set -euo pipefail

# Map service -> db file
declare -A DBS=(
  [borg-btc-1m]=btcusdt_1m.db
  [borg-btc-1h]=btcusdt_1h.db
  [borg-eth-1m]=ethusdt_1m.db
  [borg-eth-1h]=ethusdt_1h.db
)

latest_number_from_logs() {
  local svc="$1" field="$2" since="${3:-48h}"
  docker logs --since="$since" "$svc" 2>/dev/null \
    | awk -v f="\"$field\": " '
        $0 ~ f {
          split($0, a, f)
          if (length(a) > 1) { g=a[1+1]; sub(/[ ,}].*/, "", g); val=g }
        }
        END { if (val!="") print val }
      '
}

starting_cash_from_logs() {
  local svc="$1" since="${2:-365d}"
  docker logs --since="$since" "$svc" 2>/dev/null \
    | awk '
        /"event": "init\.cash"/ {
          if (match($0, /"starting_cash":[ ]*([0-9.]+)/, m)) sc=m[1]
        }
        END { if (sc!="") print sc }
      '
}

echo "timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf "%-12s | %-12s %-13s %-13s %-13s %-10s %s\n" "service" "price" "cash" "base" "equity" "PnL" "ROI%"

for svc in "${!DBS[@]}"; do
  db="${DBS[$svc]}"

  # 1) Price (logs)
  price="$(latest_number_from_logs "$svc" price 48h)"
  if [ -z "${price:-}" ]; then price="$(latest_number_from_logs "$svc" price 365d)"; fi
  price=${price:-0}

  # 2) starting cash (logs; fallback 1000)
  start_cash="$(starting_cash_from_logs "$svc" 365d)"
  if [ -z "${start_cash:-}" ]; then start_cash=1000; fi

  cash="$start_cash"
  base="0"

  # 3) Rebuild ledger from trades (buy/sell) — ignore cash_after/base_after
  if docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
       "apk add --no-cache sqlite >/dev/null 2>&1; [ -f /state/$db ] && sqlite3 -readonly -csv /state/$db \
        \"SELECT side, qty, price, fee FROM trades ORDER BY ts ASC;\" 2>/dev/null" \
        | awk -F, -v c="$cash" '
            BEGIN{ cash=c+0; base=0; have=0 }
            NF>=4 {
              side=$1; qty=$2+0; price=$3+0; fee=$4+0; have=1
              if (side=="buy")  { cash -= qty*price + fee; base += qty }
              if (side=="sell") { cash += qty*price - fee; base -= qty }
            }
            END{
              if (have==1) { printf "%.12f %.12f\n", cash, base }
            }
          ' >/tmp/.pnl_ledger 2>/dev/null; then
    if [ -s /tmp/.pnl_ledger ]; then read -r cash base < /tmp/.pnl_ledger; fi
  fi

  # 4) Equity / PnL
  equity=$(awk -v c="$cash" -v b="$base" -v p="$price" 'BEGIN{printf "%.2f", c + b*p}')
  pnl=$(awk -v e="$equity" -v s="$start_cash" 'BEGIN{printf "%.2f", e - s}')
  roi=$(awk -v p="$pnl" -v s="$start_cash" 'BEGIN{ if (s==0) printf "0.00"; else printf "%.2f", (p/s)*100 }')

  # Pretty price
  pdisp=$(awk -v p="$price" 'BEGIN{ if (p>=1000) printf "%.1f", p; else printf "%.2f", p }')

  printf "%-12s | price=%-8s cash=%-10.2f base=%-13.8f equity=%-8s PnL=%-8s %s%%\n" \
    "$svc" "$pdisp" "$cash" "$base" "$equity" "$pnl" "$roi"
done
