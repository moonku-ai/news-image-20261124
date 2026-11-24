# news-image-20261124

[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/moonku-ai/news-image-20261124/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![reward](https://make.fun/badge/news-image-20261124/moonku-ai/news-image-20261124/reward.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)

THE WORLD IN ONE DAY — a front-page broadsheet summing up Tuesday
24 November 2026 in one image: 26 numbered, dated stories across seven
regions, three illustrated lead cards, a world map with 15 numbered pins,
a day-in-numbers strip, a day-in-brief ticker, and a DATE CHECK box that
lists other days' news left out on purpose. Every story is a verified
event of 24 November 2026 (press time 00:30 UTC), drawn from same-day
reporting by Reuters, CNN, AP, BBC, The Hindu, IANS and Yonhap.
Monday-evening stories are labelled MON EVE, Sunday events SUN EVE;
claims are labelled CLAIM and forecasts FORECAST.

The program is pure Python standard library: it renders the whole page
— layout, real serif/sans type rasterised from system fonts into a
compressed glyph atlas, three flat-vector lead illustrations, the world
map, and a hand-written PNG encoder — from scratch, with no network
access and no third-party packages. Output is deterministic: two runs
produce byte-identical PNGs.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024x1024, under 1 MiB), deterministically.

## Tests

```sh
python3 test_main.py
```

19 tests: atlas load, text metrics, layout fit (no truncated card text),
story counts, determinism, output size/dimensions, a clean-directory
grader simulation, and the atlas-missing fallback (renders with a 3x5
bitmap font if `atlas.bin` is absent).

## Files

- `main.py` — the whole program (layout, drawing, PNG encoder, story data)
- `atlas.bin` — compressed glyph atlas (Liberation Serif + DejaVu Sans)
- `tools/make_atlas.py` — rebuilds `atlas.bin` from system fonts
- `test_main.py` — tests
