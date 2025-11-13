#!/usr/bin/env bash
set -euo pipefail

echo "== Containers =="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | sort
echo

echo "== Health (if defined) =="
for s in $(docker ps --format '{{.Names}}' | grep '^borg-' || true); do
  st="$(docker inspect -f '{{.State.Health.Status}}' "$s" 2>/dev/null || echo 'n/a')"
  echo "/$s -> $st"
done
echo

echo "== Errors/429 in last 2h =="
for s in borg-btc-1m borg-btc-1h borg-eth-1m borg-eth-1h; do
  c="$(docker logs --since=2h "$s" 2>&1 | egrep -i '"level": *"error"|429|rate.?limit|Too Many Requests' | wc -l || true)"
  echo "$s: $c"
done
echo

echo "== DB trades summary =="
for db in /opt/borg/state/*usdt_*.db; do
  name="$(basename "$db")"
  out="$(docker run --rm -v /opt/borg/state:/state alpine:3 sh -lc \
    "apk add --no-cache sqlite >/dev/null 2>&1; \
     sqlite3 -readonly /state/$name \"select count(*), max(ts) from trades;\" 2>/dev/null || true" \
  2>/dev/null || true)"
  cnt="${out%%|*}"; ts_ms="${out##*|}"
  if [[ -n "${ts_ms:-}" && "$ts_ms" != " " ]]; then
    ts_iso="$(date -u -d "@$(( ${ts_ms%%.*} / 1000 ))" +'%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo '?')"
  else
    ts_iso="?"
  fi
  printf "%-16s trades=%-6s last_ts=%s\n" "$name" "${cnt:-0}" "$ts_iso"
done
