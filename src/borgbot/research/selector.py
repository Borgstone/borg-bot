def select_strategies(results, top_n=3, min_roi=0, max_std=25, max_dd=0.3):
    """
    Select only robust strategies
    """

    filtered = []

    for r in results:
        if r["roi"] < min_roi:
            continue

        if r["roi_std"] > max_std:
            continue

        if r["drawdown"] > max_dd:
            continue

        filtered.append(r)

    # sort by score
    filtered.sort(key=lambda x: x["score"], reverse=True)

    deployable = []

    for r in filtered:
        if r["roi"] > 1.0 and r["roi_std"] < 10:
            deployable.append(r)

    return deployable[:top_n]