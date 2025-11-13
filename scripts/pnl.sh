#!/usr/bin/env bash
# Robust PnL: uses logs first; if missing/rotated, fetches price via ccxt (inside our image)
set -u  # no -e, so a single failure doesn't abort the report

declare -A DBS=(
  [borg-btc-1m]=btcusdt_1m.db
  [borg-btc-1h]=btcusdt_1h.db
  [borg-eth-1m]=ethusdt_1m.db
  [borg-eth-1h]=ethusdt_1h.db
)

declare -A SYMBOLS=(
  [borg-btc-1m]="BTC/USDT"
  [borg-btc-1h]="BTC/USDT"
  [borg-eth-1m]="ETH/USDT"
  [borg-eth-1h]="ETH/USDT"
)

latest_number_from_logs() {
  local svc="$1" field="$2" since="${3:-60m}"
  docker logs --since="$since" "$svc" 2>/dev/null \
  | awk -v f="\"$field\": " '
      $0 ~ f {
        split($0, a, f)
        if (length(a) > 1) { g=a[2]; sub(/[ ,}].*/, "", g); val=g }
      }
      END { if (val!="") print val }
    ' || true
}

price_from_ccxt() {
  local symbol="$1"
  docker run --rm --network host borg-bot:local python - "$symbol" 2>/dev/null <<'PY' || true
import sys, json
sym = sys.argv[1]
try:
    import ccxt
    ex = ccxt.kucoin()
    t = ex.fetch_ticker(sym)
    print(t.get("last") or t.get("close") or 0)
except Exception:
    print(0)
PY
}

starting_cash_from_logs() {
  local svc="$1" since="${2:-365d}"
  docker logs --since="$since" "$svc" 2>/dev/null \
  | awk '
      /"event": "init\.cash"/ { if (match($0, /"starting_cash":[ ]*([0-9.]+)/, m)) sc=m[1] }
      END { if (sc!="") print sc }
    ' || true
}

echo "service      | price         cash           base           equity         PnL         ROI%"

for svc in borg-btc-1m borg-btc-1h borg-eth-1m borg-eth-1h; do
  db="${DBS[$svc]}"
  sym="${SYMBOLS[$svc]}"

  # 1) Price: recent logs → ccxt → older logs → 0
  price="$(latest_number_from_logs "$svc" price 60m)"
  [[ -z "${price:-}" ]] && price="$(price_from_ccxt "$sym")"
  [[ -z "${price:-}" || "$price" = "0" ]] && price="$(latest_number_from_logs "$svc" price 365d)"
  [[ -z "${price:-}" ]] && price="0"

  # 2) starting_cash from logs (fallback 1000)
  start_cash="$(starting_cash_from_logs "$svc" 365d)"
  [[ -z "${start_cash:-}" ]] && start_cash="1000"

  # 3) last trade state (cash_after, base_after) from DB (fallback start_cash,0)
  row="$(docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
        "apk add --no-cache sqlite >/dev/null 2>&1; \
         [ -f /state/$db ] && sqlite3 -readonly -cmd '.mode list' /state/$db \
         'SELECT cash_after, base_after FROM trades ORDER BY ts DESC LIMIT 1;' \
         || true" 2>/dev/null || true)"
  cash="$start_cash"
  base="0"
  if [[ -n "$row" && "$row" == *"|"* ]]; then
    cash="${row%%|*}"
    base="${row##*|}"
  fi

  equity=$(awk -v c="$cash" -v b="$base" -v p="$price" 'BEGIN{ printf "%.2f", (c+0)+(b+0)*(p+0) }')
  pnl=$(awk -v e="$equity" -v s="$start_cash" 'BEGIN{ printf "%.2f", (e+0)-(s+0) }')
  roi=$(awk -v p="$pnl" -v s="$start_cash" 'BEGIN{ if ((s+0)==0) printf "0.00"; else printf "%.2f", ((p+0)/(s+0))*100 }')

  printf "%-12s | %-12s %-14s %-14s %-14s %-12s %s%%\n" \
    "$svc" "price=$price" "cash=$cash" "base=$base" "equity=$equity" "PnL=$pnl" "$roi"
done
