# Robust PnL: works even with empty DB/logs, prints a row per running service.

set -u  # be strict on unset vars, but don't -e so we never bail mid-loop

services() {
  docker ps --format '{{.Names}}' \
    | grep -E '^borg-(btc|eth)-(1m|1h)$' || true
}

db_for_service() {
  # borg-btc-1m -> btcusdt_1m.db
  local svc="$1"
  local sym tf
  sym="$(echo "$svc" | cut -d- -f2)"
  tf="$(echo "$svc" | cut -d- -f3)"
  echo "${sym}usdt_${tf}.db"
}

latest_number_from_logs() {
  local svc="$1" field="$2" since="${3:-60m}"
  docker logs --since="$since" "$svc" 2>/dev/null \
    | awk -v f="\""field"\": " '
        $0 ~ f {
          split($0, a, f)
          if (length(a)>1) { g=a[2]; sub(/[ ,}].*/, "", g); val=g }
        }
        END { if (val!="") print val }
      ' || true
}

starting_cash_from_logs() {
  local svc="$1" since="${2:-365d}"
  docker logs --since="$since" "$svc" 2>/dev/null \
    | awk '
        /"event": "init\.cash"/ { if (match($0, /"starting_cash":[ ]*([0-9.]+)/, m)) sc=m[1] }
        END { if (sc!="") print sc }
      ' || true
}

last_cash_base_from_db() {
  local dbfile="$1"
  docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc '
    apk add --no-cache sqlite >/dev/null 2>&1 || true
    [ -f /state/'"$dbfile"' ] || exit 0
    sqlite3 -readonly /state/'"$dbfile"' "SELECT cash_after||\"|\"||base_after FROM trades ORDER BY ts DESC LIMIT 1;" 2>/dev/null
  ' 2>/dev/null || true
}

last_cash_base_from_logs() {
  local svc="$1" since="${2:-365d}"
  docker logs --since="$since" "$svc" 2>/dev/null \
    | awk '
        /"cash_after":/ {
          if (match($0, /"cash_after":[ ]*([0-9.]+)/, c) && match($0, /"base_after":[ ]*([0-9.]+)/, b))
            val=c[1] "|" b[1]
        }
        END { if (val!="") print val }
      ' || true
}

printf "%-12s | %-13s %-14s %-14s %-14s %-11s %s\n" \
  "service" "price" "cash" "base" "equity" "PnL" "ROI%"

for svc in $(services); do
  db="$(db_for_service "$svc")"

  price="$(latest_number_from_logs "$svc" price 60m)";  [ -z "${price:-}" ] && price="$(latest_number_from_logs "$svc" price 365d)"
  [ -z "${price:-}" ] && price="0"

  start_cash="$(starting_cash_from_logs "$svc" 365d)";  [ -z "${start_cash:-}" ] && start_cash="1000"

  row="$(last_cash_base_from_db "$db")"
  [ -z "${row:-}" ] && row="$(last_cash_base_from_logs "$svc" 365d)"

  if [[ -n "${row:-}" && "$row" == *"|"* ]]; then
    IFS='|' read -r cash base <<<"$row"
  else
    cash="$start_cash"; base="0"
  fi

  read -r equity pnl roi < <(
    awk -v c="$cash" -v b="$base" -v p="$price" -v s="$start_cash" 'BEGIN{
      e=c + b*p; pl=e - s; r=(s==0?0:pl/s*100);
      printf("%.2f %.2f %.2f\n", e, pl, r);
    }'
  )

  printf "%-12s | price=%-12s cash=%-12s base=%-12s equity=%-12s PnL=%-12s (%s%%)\n" \
    "$svc" "$price" "$cash" "$base" "$equity" "$pnl" "$roi"
done

