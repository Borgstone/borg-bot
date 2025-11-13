#!/usr/bin/env bash
# Robust PnL: resilient price extraction, DB fallback, ledger replay.
set -u

# Services to report (ordered)
SERVICES=(borg-btc-1m borg-btc-1h borg-eth-1m borg-eth-1h)

# Map service -> db file
declare -A DBS=(
  [borg-btc-1m]=btcusdt_1m.db
  [borg-btc-1h]=btcusdt_1h.db
  [borg-eth-1m]=ethusdt_1m.db
  [borg-eth-1h]=ethusdt_1h.db
)

# Run a command safely; never crash the script
run_safe() { bash -c "$1" 2>/dev/null || true; }

# Extract the latest numeric field from logs via regex. Last match wins.
latest_price_from_logs() {
  local svc="$1" since="$2"
  run_safe "docker logs --since='$since' '$svc'" \
    | awk '
        {
          if (match($0, /"price"[[:space:]]*:[[:space:]]*([0-9.]+)/, m)) v=m[1]
        }
        END { if (v != "") print v }
      '
}

# starting_cash from logs (init.cash), fallback 1000
starting_cash_from_logs() {
  local svc="$1" since="${2:-365d}"
  run_safe "docker logs --since='$since' '$svc'" \
    | awk '
        /"event":[[:space:]]*"init\.cash"/ {
          if (match($0, /"starting_cash"[[:space:]]*:[[:space:]]*([0-9.]+)/, m)) sc=m[1]
        }
        END { if (sc!="") print sc }
      '
}

echo "timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf "%-12s | %-12s %-12s %-12s %-12s %-10s %s\n" "service" "price" "cash" "base" "equity" "PnL" "ROI%"

for svc in "${SERVICES[@]}"; do
  # Ensure container exists
  if ! docker inspect "$svc" >/dev/null 2>&1; then
    printf "%-12s | price=%-8s cash=%-10s base=%-12s equity=%-8s PnL=%-8s %s\n" \
      "$svc" "N/A" "N/A" "N/A" "N/A" "N/A" "N/A"
    continue
  fi

  db="${DBS[$svc]:-}"

  # 1) Price: try recent logs, then longer; fallback to last trade price
  price="$(latest_price_from_logs "$svc" 15m)"
  if [ -z "${price:-}" ]; then price="$(latest_price_from_logs "$svc" 24h)"; fi
  if [ -z "${price:-}" ]; then price="$(latest_price_from_logs "$svc" 365d)"; fi

  if [ -z "${price:-}" ] && [ -n "$db" ]; then
    # last trade price fallback
    price="$(run_safe "docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
      \"apk add --no-cache sqlite >/dev/null; \
         [ -f /state/$db ] && sqlite3 -readonly /state/$db \
         'SELECT price FROM trades ORDER BY ts DESC LIMIT 1;'\"")"
  fi

  # As a final guard, zero if still empty (will show up obviously on report)
  price="${price:-0}"

  # 2) starting cash from logs (or 1000)
  start_cash="$(starting_cash_from_logs "$svc" 365d)"; start_cash="${start_cash:-1000}"

  # 3) Rebuild ledger from trades (buy/sell with fees)
  cash="$start_cash"
  base="0"
  if [ -n "$db" ]; then
    run_safe "docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
      \"apk add --no-cache sqlite >/dev/null; \
         [ -f /state/$db ] && sqlite3 -readonly -csv /state/$db \
         'SELECT side, qty, price, fee FROM trades ORDER BY ts ASC;'\"" \
      | awk -F, -v c="$cash" '
          BEGIN{ cash=c+0; base=0; have=0 }
          NF>=4 {
            side=$1; qty=$2+0; price=$3+0; fee=$4+0; have=1
            if (side=="buy")  { cash -= qty*price + fee; base += qty }
            if (side=="sell") { cash += qty*price - fee; base -= qty }
          }
          END{ if (have==1) printf "%.12f %.12f\n", cash, base }
        ' >/tmp/.pnl_ledger.$$ || true

    if [ -s /tmp/.pnl_ledger.$$ ]; then
      read -r cash base < /tmp/.pnl_ledger.$$ || true
    fi
    rm -f /tmp/.pnl_ledger.$$ || true
  fi

  # 4) Math
  equity=$(awk -v c="${cash:-0}" -v b="${base:-0}" -v p="${price:-0}" 'BEGIN{printf "%.2f", c + b*p}')
  pnl=$(awk -v e="$equity" -v s="$start_cash" 'BEGIN{printf "%.2f", e - s}')
  roi=$(awk -v p="$pnl" -v s="$start_cash" 'BEGIN{ if (s==0) printf "0.00"; else printf "%.2f", (p/s)*100 }')

  # Display formatting
  pdisp=$(awk -v p="$price" 'BEGIN{ if (p>=1000) printf "%.1f", p; else printf "%.2f", p }')

  printf "%-12s | price=%-8s cash=%-10.2f base=%-12.8f equity=%-8s PnL=%-8s %s%%\n" \
    "$svc" "$pdisp" "$cash" "$base" "$equity" "$pnl" "$roi"
done
