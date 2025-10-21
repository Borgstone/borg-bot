# borg-bot (MVP paper trader)
Reliable-first paper trader: KuCoin OHLCV -> SMA cross -> paper fills -> SQLite state -> JSON logs.

## Risk
- Daily max loss (default 5%) halts trading for the day.
- Trading window (default 00:00-23:59) pauses outside hours.
- All logs include a `run_id` for correlation.


## Risk
- Daily max loss (default 5%) halts trading for the day.
- Trading window (default 00:00-23:59) pauses outside hours.
- All logs include a `run_id` for correlation.

