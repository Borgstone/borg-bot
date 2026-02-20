#!/usr/bin/env bash
set -euo pipefail

CSV_PATH="${CSV_PATH:-/home/borg/pnl.csv}"

services=(borg-btc-1m borg-btc-1h borg-eth-1m borg-eth-1h)
declare -A dbs=(
  [borg-btc-1m]=btcusdt_1m.db
  [borg-btc-1h]=btcusdt_1h.db
  [borg-eth-1m]=ethusdt_1m.db
  [borg-eth-1h]=ethusdt_1h.db
)

# --- helpers ---

# latest numeric field (e.g. "price") from logs; try recent window then wide
latest_num_from_logs() {
  local svc="$1" field="$2" since="${3:-15m}"
  docker logs --since="$since" "$svc" 2>/dev/null \
    | awk -v f="\"$field\": " '
        $0 ~ f {
          split($0, a, f)
          if (length(a) > 1) {
            g=a[2]
            sub(/[ ,}].*/, "", g)
            val=g
          }
        }
        END { if (val!="") print val }
      '
}

# starting cash from the earliest init.cash we can still see in logs; fallback 1000
starting_cash_from_logs() {
  local svc="$1"
  docker logs --since="365d" "$svc" 2>/dev/null | awk '
    /"event": "init\.cash"/ {
      if (match($0, /"starting_cash":[ ]*([0-9.]+)/, m)) sc=m[1]
    }
    END { if (sc!="") print sc }
  ' || true
}


# last cash/base from DB (one sqlite call)
db_last_cash_base() {
  local db="$1"
  if [ -f "/opt/borg/state/$db" ]; then
    sqlite3 "/opt/borg/state/$db" \
      'SELECT cash_after, base_after FROM trades ORDER BY ts DESC LIMIT 1;' 2>/dev/null
  fi
}


# --- write header if needed ---
if [ ! -f "$CSV_PATH" ] || ! head -n1 "$CSV_PATH" | grep -q '^timestamp,service,price,cash,base,equity,pnl,roi$'; then
  echo "timestamp,service,price,cash,base,equity,pnl,roi" > "$CSV_PATH"
fi

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

for svc in "${services[@]}"; do
  db="${dbs[$svc]}"

  # 1) price
  price="$(latest_num_from_logs "$svc" price 20m)"
  if [ -z "${price:-}" ]; then
    price="$(latest_num_from_logs "$svc" price 365d)"
  fi
  price="${price:-0}"

  starting_cash_from_logs() {
  local svc="$1"
  docker logs --since="365d" "$svc" 2>/dev/null | awk '
    /"event": "init\.cash"/ {
      if (match($0, /"starting_cash":[ ]*([0-9.]+)/, m)) sc=m[1]
    }
    END { if (sc!="") print sc }
  ' || true
}


  # 3) cash/base from DB
  read -r cash base <<<"$(db_last_cash_base "$db" || true)"
  # If DB had no trades yet, use initial state
  cash="${cash:-$sc}"
  base="${base:-0}"

  # 4) equity, pnl, roi
  equity=$(awk -v c="$cash" -v b="$base" -v p="$price" 'BEGIN{printf "%.2f", c + b*p}')
  pnl=$(awk -v e="$equity" -v s="$sc" 'BEGIN{printf "%.2f", e - s}')
  roi=$(awk -v p="$pnl" -v s="$sc" 'BEGIN{ if (s==0) printf "0.00"; else printf "%.2f", (p/s)*100 }')

  # normalize formats: price two decimals, base 8 decimals, cash two decimals
  price_fmt=$(awk -v x="$price" 'BEGIN{printf "%.2f", x}')
  cash_fmt=$(awk -v x="$cash"  'BEGIN{printf "%.2f", x}')
  base_fmt=$(awk -v x="$base"  'BEGIN{printf "%.8f", x}')

  echo "$ts,$svc,$price_fmt,$cash_fmt,$base_fmt,$equity,$pnl,$roi" >> "$CSV_PATH"
done
