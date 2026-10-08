"""Dirtiness score 1-5 from how many litter items were found and how much of the photo they cover.
The bands are starting values: tune them on day two against real Slemani photos
(tools/evaluate.py --suggest-bands, then LEVEL_COUNT_BANDS=...)."""

COUNT_LIMITS = (2, 5, 10, 20)                       # count <= limit -> level 1, 2, 3, 4; above -> 5
COVERAGE_BUMPS = [(0.35, 2), (0.15, 1)]             # coverage above limit adds this much


def dirtiness(count, coverage, limits=COUNT_LIMITS):
    if count <= 0:
        return 0
    score = 5
    for level, limit in enumerate(limits, start=1):
        if count <= limit:
            score = level
            break
    for limit, bump in COVERAGE_BUMPS:
        if coverage > limit:
            score += bump
            break
    return max(1, min(5, score))
