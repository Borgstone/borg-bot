def select_strategies(
    results,
    top_n=5,
    min_roi=0.0,
    max_std=50.0,
    max_dd=0.50,
):

    filtered = []

    for r in results:

        if r["roi"] < min_roi:
            continue

        if r["roi_std"] > max_std:
            continue

        if r["drawdown"] > max_dd:
            continue

        filtered.append(r)

    filtered.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return filtered[:top_n]