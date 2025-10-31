#!/usr/bin/env bash
set -euo pipefail
services=(borg-btc-1m borg-btc-1h borg-eth-1m borg-eth-1h)

for s in "${services[@]}"; do
  health="$(docker inspect -f '{{.State.Health.Status}}' "$s" 2>/dev/null || echo "n/a")"
  started="$(docker inspect -f '{{.State.StartedAt}}' "$s" 2>/dev/null || echo "n/a")"
  last_price="$(docker logs --since=30m "$s" 2>/dev/null \
                | awk -F'"price": ' '/"price":[ ]*[0-9]/{p=$2} END{print p}' \
                | awk -F'[ ,}]' '{print $1}')"
  errs="$(docker logs --since=2h "$s" 2>&1 | egrep -i '"level": "error"|429' | wc -l)"
  trades="$(docker logs --since=2h "$s" | egrep -c '"paper\.buy"|"paper\.sell"' || true)"
  printf "%-12s | health=%-9s started=%-25s last_price=%-12s errors_2h=%-4s trades_2h=%-4s\n" \
    "$s" "$health" "$started" "${last_price:-n/a}" "$errs" "$trades"
done
