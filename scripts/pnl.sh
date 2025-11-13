#!/usr/bin/env bash
# PnL report with robust price lookup (logs -> exec ccxt -> older logs -> ephemeral ccxt)
set -u  # keep running even if one svc has issues

declare -A DBS=(
  [borg-btc-1m]=btcusdt_1m.db
  [borg-btc-1h]=btcusdt_1h.db
  [borg-eth-1m]=ethusdt_1m.db
  [borg-eth-1h]=ethusdt_1h.db
)

# Fallback symbol mapping if we can't read from container env
declare -A DEFAULT_SYMBOLS=(
  [borg-btc-1m]="BTC/USDT"
  [borg-btc-1h]="BTC/USDT"
  [borg-eth-1m]="ETH/USDT"
  [borg-eth-1h]="ETH/USDT"
)

ts() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }

symbol_from_container() {
  local svc="$1"
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$svc" 2>/dev/null \
    | awk -F= '$1=="SYMBOL"{print $2}' | head -n1
}

latest_number_from_logs() {
  local svc="$1" field="$2" since="${3:-60m}"
  docker logs --since="$since" "$svc" 2>/dev/null \
  | awk -v f="\"$field\": " '
      $0 ~ f { split($0,a,f); if (length(a)>1) { g=a[2]; sub(/[ ,}].*/, "", g); val=g } }
      END { if (val!="") print val }
    ' || true
}

price_from_exec() {
  local svc="$1" sym="$2"
  docker exec "$svc" python - "$sym" 2>/dev/null <<'PY' || true
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

price_from_ephemeral() {
  local sym="$1"
  docker run --rm --network host borg-bot:local python - "$sym" 2>/dev/null <<'PY' || true
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
  | awk '/"event": "init\.cash"/ { if (match($0, /"starting_cash":[ ]*([0-9.]+)/, m)) sc=m[1] } END { if (sc!="") print sc }' \
  || true
}

echo "timestamp: $(ts)"
echo "service      | price         cash           base           equity         PnL         ROI%"

for svc in borg-btc-1m borg-btc-1h borg-eth-1m borg-eth-1h; do
  db="${DBS[$svc]}"
  sym="$(symbol_from_container "$svc")"
  [[ -z "${sym:-}" ]] && sym="${DEFAULT_SYMBOLS[$svc]}"

  # 1) price: recent logs
  price="$(latest_number_from_logs "$svc" price 60m)"

  # 2) price: exec inside running container
  if [[ -z "${price:-}" ]]; then
    price="$(price_from_exec "$svc" "$sym")"
  fi

  # 3) price: older logs (if exec failed or returned 0)
  if [[ -z "${price:-}" || "$price" = "0" ]]; then
    price="$(latest_number_from_logs "$svc" price 365d)"
  fi

  # 4) price: ephemeral container (last resort)
  if [[ -z "${price:-}" || "$price" = "0" ]]; then
    price="$(price_from_ephemeral "$sym")"
  fi
  [[ -z "${price:-}" ]] && price="0"

  # starting cash from logs (fallback 1000)
  start_cash="$(starting_cash_from_logs "$svc" 365d)"; [[ -z "${start_cash:-}" ]] && start_cash="1000"

  # last trade state from DB
  row="$(docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
        "apk add --no-cache sqlite >/dev/null 2>&1; \
         [ -f /state/$db ] && sqlite3 -readonly -cmd '.mode list' /state/$db \
         'SELECT cash_after, base_after FROM trades ORDER BY ts DESC LIMIT 1;' || true" \
        2>/dev/null || true)"
  cash="$start_cash"; base="0"
  if [[ -n "$row" && "$row" == *"|"* ]]; then cash="${row%%|*}"; base="${row##*|}"; fi

  equity=$(awk -v c="$cash" -v b="$base" -v p="$price" 'BEGIN{ printf "%.2f", (c+0)+(b+0)*(p+0) }')
  pnl=$(awk -v e="$equity" -v s="$start_cash" 'BEGIN{ printf "%.2f", (e+0)-(s+0) }')
  roi=$(awk -v p="$pnl" -v s="$start_cash" 'BEGIN{ if ((s+0)==0) printf "0.00"; else printf "%.2f", ((p+0)/(s+0))*100 }')

  printf "%-12s | %-12s %-14s %-14s %-14s %-10s %s%%\n" \
    "$svc" "price=$price" "cash=$cash" "base=$base" "equity=$equity" "PnL=$pnl" "$roi"
done
