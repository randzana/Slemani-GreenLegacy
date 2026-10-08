"""Dirtiness score 1-5 from how many litter items were found and how much of the photo they cover.
The bands are starting values: tune them on day two against real Slemani photos."""

COUNT_BANDS = [(2, 1), (5, 2), (10, 3), (20, 4)]   # count <= limit -> score; above all -> 5
COVERAGE_BUMPS = [(0.35, 2), (0.15, 1)]             # coverage above limit adds this much


def dirtiness(count, coverage):
    if count <= 0:
        return 0
    score = 5
    for limit, value in COUNT_BANDS:
        if count <= limit:
            score = value
            break
    for limit, bump in COVERAGE_BUMPS:
        if coverage > limit:
            score += bump
            break
    return max(1, min(5, score))
