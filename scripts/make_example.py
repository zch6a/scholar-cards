"""examples/scholar.json: a made-up researcher (no real person's record), for the README's images, CI and tries
without the network. Seeded: the same file every time.

    uv run python scripts/make_example.py
"""

import random
from pathlib import Path

from scholar_cards.model import Scholar, Work

rng = random.Random(27)
years = list(range(2014, 2027))
cites = [int(40 * 1.38**i + rng.randint(-15, 15)) for i in range(len(years))]
cites[-1] = int(cites[-2] * 0.86)  # the snapshot's own year, not over (it is 2026-11)
works = [3, 4, 6, 5, 8, 7, 9, 11, 8, 10, 12, 9, 7]
scholar = Scholar(
    id="https://openalex.org/A0000000000",
    name="Dr. Ada Example",
    works_count=sum(works),
    cited_by_count=sum(cites),
    h_index=27,
    i10_index=48,
    mean_citedness_2yr=6.4,
    orcid="",
    institution="Example Institute of Technology",
    counts_by_year=[(y, w, c) for y, w, c in zip(years, works, cites, strict=True)],
    top_works=[
        Work("Sparse attention for long documents", 2019, "Advances in Neural Information Processing Systems", 2140),
        Work("A benchmark for robust tabular learning", 2021, "International Conference on Learning Representations", 1315),
        Work("Calibrated uncertainty under distribution shift", 2018, "International Conference on Machine Learning", 978),
        Work("Small models, careful data: a study of curation", 2023, "Transactions on Machine Learning Research", 512),
        Work("Seeds, variance, and what tables should say", 2024, "Journal of Machine Learning Research", 238),
    ],
    retrieved="2026-11-13",
    sources=["(made up: scripts/make_example.py)"],
)
out = Path(__file__).resolve().parent.parent / "examples" / "scholar.json"
out.parent.mkdir(exist_ok=True)
out.write_text(scholar.to_json(), encoding="utf-8")
print(f"wrote {out}")
