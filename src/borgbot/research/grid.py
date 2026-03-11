import itertools


def parse_range(expr: str):
    """
    "5:20" → [5,6,...,20]
    """
    start, end = expr.split(":")
    return list(range(int(start), int(end) + 1))


def generate_sma_grid(fast_range: str, slow_range: str):
    fast_values = parse_range(fast_range)
    slow_values = parse_range(slow_range)

    combos = []

    for f, s in itertools.product(fast_values, slow_values):
        if f < s:  # prevent invalid combos
            combos.append({"fast": f, "slow": s})

    return combos